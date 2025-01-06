import datetime
import re
import requests

from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils import my_parse_date
from bsoclinicaltrials.server.main.utils_swift import get_objects, set_objects

logger = get_logger(__name__)

countries = ["france", "french guiana", "guadeloupe", "martinique", "mayotte", "réunion"]
sponsors = [
    "anrs",
    "inserm",
    "institut national de la santé et de la recherche médicale",
    "french national agency for research on aids and viral hepatitis",
]

def harvest():
    queries = countries + sponsors
    queries = ' OR '.join([country.lower() for country in queries])
    url = "https://clinicaltrials.gov/api/v2/studies?query.term={}&countTotal={}&pageSize=1000"
    r = requests.get(url.format(queries, "true")).json()
    count = r.get("totalCount")
    nextToken = r.get("nextPageToken")
    logger.debug(f"{count} studies found")
    data = r.get("studies")
    while nextToken:
        r = requests.get(f"{url}&pageToken={nextToken}".format(queries, "false")).json()
        nextToken = r.get("nextPageToken")
        data += r.get("studies")
    today = datetime.date.today()
    set_objects(data, "clinical-trials", f"clinical_trials_raw_{today}.json.gz")
    return data


def parse_all(harvested_data, harvest_date = None):
    parsed_data = []
    for d in harvested_data:
        parsed = parse_study(d)
        added = False
        for country in countries:
            if (not added) and (country in parsed.get("location_country", [])):
                added = True
                parsed_data.append(parsed)
        for sponsor in sponsors:
            if (not added) and (sponsor in parsed.get("collaborators", [])):
                added = True
                parsed_data.append(parsed)
    if harvest_date is None:
        today = datetime.date.today()
        harvest_date = f"{today}"
    set_objects(parsed_data, "clinical-trials", f"clinical_trials_parsed_{harvest_date}.json.gz")
    return {
        "status": "ok",
        "harvest_date": f"{harvest_date}",
        "source": "clinical-trials",
        "nb_studies_harvested": len(harvested_data),
        "nb_studies_parsed": len(parsed_data)
    }


def harvest_parse_clinical_trials(to_harvest=True, to_parse=True, harvest_date=None):
    if to_harvest:
        harvested_data = harvest()
        if to_parse:
            return parse_all(harvested_data, harvest_date)
    else:
        if to_parse:
            harvested_data = get_objects('clinical-trials', f'clinical_trials_raw_{harvest_date}.json.gz')
            return parse_all(harvested_data, harvest_date)


# See data model : https://clinicaltrials.gov/data-api/about-api/study-data-structure
def parse_study(input_study):
    protocol = input_study.get('protocolSection', {})
    # Results
    results = input_study.get('resultsSection')
    elt = {'has_results': (results is not None)}
    # Identification
    identification_module = protocol.get('identificationModule', {})
    elt['NCTId'] = identification_module.get('nctId')
    elt['other_ids'] = []
    if identification_module.get("orgStudyIdInfo", {}).get("id"):
        elt['other_ids'].append({'type': "org_study_id", 
                                 "id": identification_module.get("orgStudyIdInfo", {}).get("id")})
    for second_id_elt in identification_module.get("secondaryIdInfos", []):
        if second_id_elt.get("id"):
            elt['other_ids'].append(second_id_elt)
            if second_id_elt.get("type") == "EudraCT Number":
                elt['eudraCT'] = second_id_elt.get("id")
    elt['title'] = identification_module.get('officialTitle')
    elt['acronym'] = identification_module.get('acronym')
    #description
    description_module = protocol.get('descriptionModule', {})
    summary = description_module.get('briefSummary')
    if summary:
        elt['summary'] = summary
    # Status
    status_module = protocol.get('statusModule', {})
    study_start_date = status_module.get('startDateStruct', {}).get('date')
    study_start_date_type = status_module.get('startDateStruct', {}).get('type')
    elt['study_start_date'] = my_parse_date(study_start_date)
    elt['study_start_date_type'] = study_start_date_type
    elt['status'] = status_module.get("overallStatus").capitalize()
    study_completion_date = status_module.get('completionDateStruct', {}).get('date')
    study_completion_date_type = status_module.get('completionDateStruct', {}).get('type')
    elt['study_completion_date'] = my_parse_date(study_completion_date)
    elt['study_completion_date_type'] = study_completion_date_type
    study_first_submit_date = status_module.get('studyFirstSubmitDate')
    study_first_submit_qc_date = status_module.get('studyFirstSubmitQcDate')
    results_first_submit_date = status_module.get('resultsFirstSubmitDate')
    results_first_submit_qc_date = status_module.get('resultsFirstSubmitQcDate')
    elt['study_first_submit_date'] = my_parse_date(study_first_submit_date)
    elt['study_first_submit_qc_date'] = my_parse_date(study_first_submit_qc_date)
    elt['results_first_submit_date'] = my_parse_date(results_first_submit_date)
    elt['results_first_submit_qc_date'] = my_parse_date(results_first_submit_qc_date)
    # Design
    design_module = protocol.get('designModule', {})
    study_type = design_module.get('studyType').capitalize()
    elt['study_type'] = study_type
    design_info = design_module.get('designInfo', {})
    time_perspective = design_info.get('timePerspective')
    elt['time_perspective'] = time_perspective
    elt['design_allocation'] = design_info.get('allocation')
    elt['primary_purpose'] = design_info.get('primaryPurpose')
    enrollment_info = design_module.get("enrollmentInfo", {})
    enrollment_count = enrollment_info.get("count")
    enrollment_type = enrollment_info.get("type")
    elt['enrollment_count'] = enrollment_count
    elt['enrollment_type'] = enrollment_type
    # References
    ref_module = protocol.get("referencesModule", {})
    references = ref_module.get("references", [])
    elt["references"] = []
    for r in references:
        if r.get("type"):
            r["type"] = r.get("type").lower()
        elt["references"].append(r)
    for r in references:
        if "doi:" in r.get("citation", "").lower():
            doi = re.sub(".*doi:", "", r.get("citation", "")).strip().lower()
            doi = doi.split(" ")[0]
            if doi[-1] == ".":
                doi = doi[:-1]
            r["doi"] = doi
    # Type can be result, derived or background (done in enrich)
    #elt['publications_result'] = []
    #for r in references:
    #    if r.get('type').lower() in ['result', 'derived'] and 'protocol' not in r['citation'].lower():
    #        if 'doi' in r:
    #            elt['publications_result'].append(r['doi'])
    #        elif 'pmid' in r:
    #            elt['publications_result'].append(r['pmid'])
    #        elif 'citation' in r:
    #            elt['publications_result'].append(r['citation'])
    #        else:
    #            elt['publications_result'].append('other')
    #elt['has_publications_result'] = len(elt['publications_result']) > 0
    #elt['has_results_or_publications'] = elt['has_results'] or elt['has_publications_result']
    # IPD individual patient data
    ipd_module = protocol.get('ipdSharingStatementModule', {})
    elt['ipd_sharing'] = ipd_module.get('ipdSharing').capitalize() if isinstance(ipd_module.get('ipdSharing'), str) else ipd_module.get('ipdSharing')
    ipd_sharing_description = ipd_module.get('description')
    elt['ipd_sharing_description'] = ipd_sharing_description
    # Sponsors
    sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
    lead_sponsor = sponsor_module.get('leadSponsor', {}).get('name')
    elt['lead_sponsor'] = lead_sponsor
    collaborators = sponsor_module.get('collaborators', [])
    elt['collaborators'] = []
    for k in collaborators:
        if k.get('name') and k.get('name') not in elt['collaborators']:
            elt['collaborators'].append(k.get('name').lower())
    elt['sponsor_collaborators'] = [elt['lead_sponsor']] + elt['collaborators']
    assert(isinstance(elt['sponsor_collaborators'], list))
    # ContactsLocations
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
    elt["location_country"] = list(set([location.get("country").lower() for location in locations if "country" in location]))
    elt["location_facility"] = list(set([location.get("facility") for location in locations if "facility" in location]))
    # Interventions
    interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])
    elt["intervention_type"] = list(set([intervention.get("type") for intervention in interventions if "type" in intervention]))
    return elt
