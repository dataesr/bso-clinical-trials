import datetime
import math
import re
import requests

from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils import my_parse_date
from bsoclinicaltrials.server.main.utils_swift import get_objects, set_objects

logger = get_logger(__name__)


def harvest():
    url = 'https://clinicaltrials.gov/api/query/full_studies?expr=france&fmt=json&min_rnk={}&max_rnk={}'
    nb_studies = requests.get(url.format(1, 1)).json()['FullStudiesResponse']['NStudiesFound']
    logger.debug(f'{nb_studies} studies found')
    nb_pages = math.ceil(nb_studies / 100)
    data = []
    for p in range(0, nb_pages):
        r = requests.get(url.format(p * 100 + 1, (p+1) * 100)).json()
        data += r['FullStudiesResponse']['FullStudies']
    today = datetime.date.today()
    set_objects(data, "clinical-trials", f"clinical_trials_raw_{today}.json.gz")
    return data


def parse_all(harvested_data):
    parsed_data = []
    for d in harvested_data:
        parsed = parse_study(d)
        if 'France' in parsed.get('location_country', []):
            parsed_data.append(parsed)
    today = datetime.date.today()
    set_objects(parsed_data, 'clinical-trials', f'clinical_trials_parsed_{today}.json.gz')
    return {
        'status': 'ok',
        'source': 'clinical-trials',
        'nb_studies_harvested': len(harvested_data),
        'nb_studies_parsed': len(parsed_data)
    }


def harvest_parse_clinical_trials(to_harvest=True, to_parse=True, harvest_date=''):
    if to_harvest:
        harvested_data = harvest()
        if to_parse:
            parse_all(harvested_data)
    else:
        if to_parse:
            harvested_data = get_objects('clinical-trials', f'Clinical_trials_raw_{harvest_date}.json.gz')
            parse_all(harvested_data)


def parse_study(input_study):
    x = input_study.get('Study')
    protocol = x.get('ProtocolSection', {})
    # Results
    results = x.get('ResultsSection')
    elt = {'has_results': (results is not None)}
    # Identification
    identification_module = protocol.get('IdentificationModule', {})
    elt['NCTId'] = identification_module.get('NCTId')
    elt['other_ids'] = []
    if identification_module.get("OrgStudyIdInfo", {}).get("OrgStudyId"):
        elt['other_ids'].append({'type': "org_study_id", 
                                 "id": identification_module.get("OrgStudyIdInfo", {}).get("OrgStudyId")})
    for second_id_elt in identification_module.get("SecondaryIdInfoList", {}).get("SecondaryIdInfo", []):
        if second_id_elt.get("SecondaryId"):
            elt['other_ids'].append({'type': second_id_elt.get('SecondaryIdType'),
                                     'id': second_id_elt.get('SecondaryId')})
            if second_id_elt.get("SecondaryIdType") == "EudraCT Number":
                elt['eudraCT'] = second_id_elt.get("SecondaryId")
    elt['title'] = identification_module.get('OfficialTitle')
    elt['acronym'] = identification_module.get('Acronym')
    # Status
    status_module = protocol.get('StatusModule', {})
    study_start_date = status_module.get('StartDateStruct', {}).get('StartDate')
    study_start_date_type = status_module.get('StartDateStruct', {}).get('StartDateType')
    elt['study_start_date'] = my_parse_date(study_start_date)
    elt['study_start_date_type'] = study_start_date_type
    elt['status'] = status_module.get("OverallStatus")
    elt['study_start_year'] = None
    if elt['study_start_date']:
        elt['study_start_year'] = elt['study_start_date'][0:4]
    study_completion_date = status_module.get('CompletionDateStruct', {}).get('CompletionDate')
    study_completion_date_type = status_module.get('CompletionDateStruct', {}).get('CompletionDateType')
    elt['study_completion_date'] = my_parse_date(study_completion_date)
    elt['study_completion_date_type'] = study_completion_date_type
    study_first_submit_date = status_module.get('StudyFirstSubmitDate')
    study_first_submit_qc_date = status_module.get('StudyFirstSubmitQCDate')
    results_first_submit_date = status_module.get('ResultsFirstSubmitDate')
    results_first_submit_qc_date = status_module.get('ResultsFirstSubmitQCDate')
    elt['study_first_submit_date'] = my_parse_date(study_first_submit_date)
    elt['study_first_submit_qc_date'] = my_parse_date(study_first_submit_qc_date)
    elt['results_first_submit_date'] = my_parse_date(results_first_submit_date)
    elt['results_first_submit_qc_date'] = my_parse_date(results_first_submit_qc_date)
    # Design
    design_module = protocol.get('DesignModule', {})
    study_type = design_module.get('StudyType')
    elt['study_type'] = study_type
    design_info = design_module.get('DesignInfo', {})
    time_perspective = design_info.get('DesignTimePerspectiveList', {}).get('DesignTimePerspective', [])
    elt['time_perspective'] = time_perspective
    elt['design_allocation'] = design_info.get('DesignAllocation')
    elt['primary_purpose'] = design_info.get('DesignPrimaryPurpose')
    enrollment_info = design_module.get("EnrollmentInfo", {})
    enrollment_count = enrollment_info.get("EnrollmentCount")
    enrollment_type = enrollment_info.get("EnrollmentType")
    elt['enrollment_count'] = enrollment_count
    elt['enrollment_type'] = enrollment_type
    # References
    ref_module = protocol.get('ReferencesModule', {})
    ref_list = ref_module.get("ReferenceList", {})
    references = ref_list.get('Reference', [])
    elt['references'] = references
    for r in references:
        if 'doi:' in r.get('ReferenceCitation', '').lower():
            doi = re.sub(".*doi:", '', r.get('ReferenceCitation', '')).strip().lower()
            doi = doi.split(" ")[0]
            if doi[-1] == ".":
                doi = doi[:-1]
            r['doi'] = doi
    # Type can be result, derived or background
    elt['publications_result'] = []
    for r in references:
        if r.get('ReferenceType') == 'result':
            if 'doi' in r:
                elt['publications_result'].append(r['doi'])
            elif 'ReferencePMID' in r:
                elt['publications_result'].append(r['ReferencePMID'])
            elif 'ReferenceCitation' in r:
                elt['publications_result'].append(r['ReferenceCitation'])
            else:
                elt['publications_result'].append('other')
    elt['has_publications_result'] = len(elt['publications_result']) > 0
    elt['has_results_or_publications'] = elt['has_results'] or elt['has_publications_result']
    # IPD individual patient data
    ipd_module = protocol.get('IPDSharingStatementModule', {})
    ipd_sharing = ipd_module.get('IPDSharing')
    elt['ipd_sharing'] = ipd_sharing
    # Sponsor
    sponsor_module = protocol.get('SponsorCollaboratorsModule', {})
    lead_sponsor = sponsor_module.get('LeadSponsor', {}).get('LeadSponsorName')
    elt['lead_sponsor'] = lead_sponsor
    # ContactLocation
    locations_module = protocol.get('ContactsLocationsModule', {})
    locations = locations_module.get('LocationList', {}).get('Location', [])
    location_country = list(set(
        [x.get('LocationCountry') for x in locations if "LocationCountry" in x]))
    location_facility = list(set(
        [x.get('LocationFacility') for x in locations if "LocationFacility" in x]))
    elt['location_country'] = location_country
    elt['location_facility'] = location_facility
    # Intervention
    intervention_module = protocol.get('ArmsInterventionsModule', {})
    interventions = intervention_module.get('InterventionList', {}).get('Intervention', [])
    intervention_type = list(set(
        [w.get('InterventionType') for w in interventions if 'InterventionType' in w]))
    elt['intervention_type'] = intervention_type
    return elt
