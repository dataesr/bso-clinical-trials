import datetime
import re
import requests

from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils import my_parse_date
from bsoclinicaltrials.server.main.utils_swift import get_objects, set_objects

logger = get_logger(__name__)

countries = ["france", "french guiana", "guadeloupe", "martinique", "mayotte", "réunion"]
sponsors = [
    "Aix Marseille Université",
    "Assistance Publique - Hôpitaux de Paris",
    "Assistance Publique Hopitaux De Marseille",
    "Bicetre Hospital",
    "Bichat Hospital",
    "Central Hospital, Nancy, France",
    "Centre Antoine Lacassagne",
    "Centre de Recherche en Nutrition Humaine d'Auvergne",
    "Centre Hospitalier de Verdun",
    "Centre Hospitalier Régional Universitaire Montpellier",
    "Centre hospitalier Saint Jean de Dieu - ARHM",
    "Centre Hospitalier Saint Joseph Saint Luc de Lyon",
    "Centre Hospitalier St Anne",
    "Centre Hospitalier Universitaire de Besancon",
    "Centre Hospitalier Universitaire de la Guadeloupe",
    "Centre Hospitalier Universitaire de la Réunion",
    "Centre Hospitalier Universitaire de Nice",
    "Centre Hospitalier Universitaire de Nīmes",
    "Centre Hospitalier Universitaire de Saint Etienne",
    "Centre Hospitalier Universitaire Dijon",
    "Centre Leon Berard",
    "CHU de Reims",
    "Claude Bernard University",
    "Cochin Hospital",
    "Danone Vitapole, France.",
    "DRC lille, France",
    "Ecole Polytechnique, France",
    "European Georges Pompidou Hospital",
    "Expertise France",
    "Fondation Ophtalmologique Adolphe de Rothschild",
    "French Society for Intensive Care",
    "Groupe Hospitalier de la Rochelle Ré Aunis",
    "Groupe Hospitalier Pitie-Salpetriere",
    "Hôpital Cochin",
    "Hôpital Edouard Herriot",
    "Hopital Lariboisière",
    "Hôpital le Vinatier",
    "Hôpital NOVO",
    "Hôpital Rothschild",
    "Hopitaux de Saint-Maurice",
    "Hospices Civils de Lyon",
    "Hospital Avicenne",
    "Institut Bergonié",
    "Institut de recherche biomédicale des armées (IRBA), Bretigny sur Orge, France",
    "Institut de Recherche Biomedicale des Armees",
    "Institut de Recherche pour le Developpement",
    "Institut du Cancer de Montpellier - Val d'Aurelle",
    "Institut Jean-Godinot",
    "Institut National de Recherche pour l'Agriculture, l'Alimentation et l'Environnement",
    "Institut Paoli-Calmettes",
    "Institut Pasteur",
    "Lille Catholic University",
    "Local Cancer Registry - France",
    "Médecins Sans Frontières, France",
    "Merck Serono S.A.S, France",
    "Ministry of Health, France",
    "Nantes University Hospital",
    "National Cancer Institute, France",
    "Organisms in charge of local cancer screening programs - France",
    "Paris West University Nanterre La Défense",
    "Poissy-Saint Germain Hospital",
    "Poitiers University Hospital",
    "Ramsay Générale de Santé",
    "Rennes University Hospital",
    "Sciences Po Paris",
    "Université de Nantes",
    "Université de Reims Champagne-Ardenne",
    "University Hospital Center of Martinique",
    "University Hospital, Angers",
    "University Hospital, Bordeaux",
    "University Hospital, Brest",
    "University Hospital, Caen",
    "University Hospital, Clermont-Ferrand",
    "University Hospital, Grenoble",
    "University Hospital, Lille",
    "University Hospital, Limoges",
    "University Hospital, Montpellier",
    "University Hospital, Rouen",
    "University Hospital, Strasbourg, France",
    "University Hospital, Toulouse",
    "University Hospital, Tours",
    "University Jean-Jaures, Toulouse, France",
    "University of Paris 13",
    "University of Paris 5 - Rene Descartes",
    "University of Pau and Pays de l'Adour",
    "University of Poitiers",
    "University Paris 7 - Denis Diderot",
]

def harvest():
    queries = countries + sponsors
    queries = ' OR '.join([query.lower() for query in queries])
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
        parsed_countries = [parsed_country.lower() for parsed_country in parsed.get("location_country", [])]
        for country in countries:
            if (not added) and (country.lower() in parsed_countries):
                added = True
                parsed_data.append(parsed)
        parsed_collaborators = [parsed_collaborator.lower() for parsed_collaborator in parsed.get("sponsor_collaborators", [])]
        for sponsor in sponsors:
            if (not added) and (sponsor.lower() in parsed_collaborators):
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


def harvest_parse_clinical_trials(to_harvest=True, to_parse=True, harvest_dates=[]):
    response = {}
    for harvest_date in harvest_dates:
        if to_harvest:
            harvested_data = harvest()
            if to_parse:
                response = parse_all(harvested_data, harvest_date)
        else:
            if to_parse:
                harvested_data = get_objects('clinical-trials', f'clinical_trials_raw_{harvest_date}.json.gz')
                response = parse_all(harvested_data, harvest_date)
    return response


# See data model : https://clinicaltrials.gov/data-api/about-api/study-data-structure
def parse_study(input_study):
    protocol = input_study.get('protocolSection', {})
    # Results
    results = input_study.get('resultsSection')
    elt = {'has_results': (results is not None)}
    # Identification
    identification_module = protocol.get('identificationModule', {})
    elt["id"] = identification_module.get('nctId')
    elt["NCTId"] = identification_module.get('nctId')
    elt["other_ids"] = []
    if identification_module.get("orgStudyIdInfo", {}).get("id"):
        elt["other_ids"].append({"type": "org_study_id",
                                 "id": identification_module.get("orgStudyIdInfo", {}).get("id")})
    for second_id_elt in identification_module.get("secondaryIdInfos", []):
        if second_id_elt.get("id"):
            elt["other_ids"].append(second_id_elt)
            if second_id_elt.get("type") in ["EudraCT Number", "EUDRACT_NUMBER"]:
                elt["eudraCT"] = second_id_elt.get("id")
            elif second_id_elt.get("type") == "REGISTRY" and second_id_elt.get("domain") == "CTIS (EU)":
                elt["CTIS"] = second_id_elt.get("id")
            elif not elt.get("eudraCT") and re.match("^20\d{2}-00\d{4}-\d{2}$", second_id_elt.get("id")):
                elt["eudraCT"] = second_id_elt.get("id")
    elt["title"] = identification_module.get("officialTitle")
    elt["acronym"] = identification_module.get("acronym")
    # Description
    description_module = protocol.get("descriptionModule", {})
    summary = description_module.get("briefSummary")
    if summary:
        elt["summary"] = summary
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
    # Should keep all types of intervention
    elt["intervention_type_raw"] = list(set([intervention.get("type") for intervention in interventions if "type" in intervention]))
    # Only one type of intervention, with priority to DRUG
    elt["intervention_type"] = list(set([intervention.get("type") for intervention in interventions if "type" in intervention]))
    if "DRUG" in elt["intervention_type"]:
        elt["intervention_type"] = "DRUG"
    elif len(elt["intervention_type"]) > 0:
        elt["intervention_type"] = elt["intervention_type"][0]
    else:
        elt["intervention_type"] = None
    return elt
