import requests
import math
import re
import dateutil.parser
from bso.server.main.logger import get_logger
from bso.server.main.utils_swift import set_objects

logger = get_logger(__name__)


def my_parse_date(x):
    if x:
        return dateutil.parser.parse(x).isoformat()
    return x

def get_doi_info(doi):
    return {}

def harvest():
    url="https://clinicaltrials.gov/api/query/full_studies?expr=france&fmt=json&min_rnk={}&max_rnk={}"
    nb_studies = requests.get(url.format(1,1)).json()['FullStudiesResponse']['NStudiesFound']
    logger.debug(f"{nb_studies} studies found")
    
    nb_pages = math.ceil(nb_studies / 100)

    data = []
    for p in range(0, nb_pages):
        r = requests.get(url.format(p * 100 + 1, (p+1) * 100)).json()
        data += r['FullStudiesResponse']['FullStudies']
    return data

def parse_all(harvested_data):
    parsed_data = []
    for d in harvested_data:
        parsed = parse_study(d)
        if 'France' in parsed.get('location_country', []):
            parsed_data.append(parsed)
    set_objects(parsed_data, "clinical-trials", "clinical_trials.json.gz")
    return {"status": "ok", "source": "clinical-trials", "nb_studies_harvested": len(harvested_data), "nb_studies_parsed": len(parsed_data)}


def harvest_parse_clinical_trials():
    harvested_data = harvest()
    parse_all(harvested_data)

def parse_study(input_study):
    x = input_study.get('Study')
    protocol = x.get('ProtocolSection', {})
    
    ## results
    results = x.get('ResultsSection')
    
    elt = {}
    
    elt['has_results'] = (results is not None)
    
    ## identification
    identification_module = protocol.get('IdentificationModule', {})
    
    elt['NCTId'] = identification_module.get('NCTId')
    elt['other_ids'] = []
    if identification_module.get("OrgStudyIdInfo", {}).get("OrgStudyId"):
        elt['other_ids'].append({'type': "org_study_id", 
                                 "id": identification_module.get("OrgStudyIdInfo", {}).get("OrgStudyId") })
        
    for second_id_elt in identification_module.get("SecondaryIdInfoList", {}).get("SecondaryIdInfo", []):
        if second_id_elt.get("SecondaryId"):
            elt['other_ids'].append({"type": second_id_elt.get("SecondaryIdType"),
                                "id": second_id_elt.get("SecondaryId")})
            if second_id_elt.get("SecondaryIdType") == "EudraCT Number":
                elt['eudraCT'] = second_id_elt.get("SecondaryId")
        
        
    elt['title'] = identification_module.get('OfficialTitle')
    elt['acronym'] = identification_module.get('Acronym')
    
    ## status
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
    
    
    
    ## design
    design_module = protocol.get('DesignModule', {})
    study_type = design_module.get('StudyType')
    elt['study_type'] = study_type
    
    design_info = design_module.get('DesignInfo', {})
    time_perspective = design_info.get('DesignTimePerspectiveList', {}).get('DesignTimePerspective', [])
    elt['time_perspective'] = ";".join(time_perspective)
    
    elt['primary_purpose'] = design_info.get('DesignPrimaryPurpose')
    
    enrollment_info = design_module.get("EnrollmentInfo", {})
    enrollment_count = enrollment_info.get("EnrollmentCount")
    enrollment_type = enrollment_info.get("EnrollmentType")
    elt['enrollment_count'] = enrollment_count
    elt['enrollment_type'] = enrollment_type
    
    ## references
    ref_module = protocol.get('ReferencesModule', {})
    ref_list = ref_module.get("ReferenceList", {})
    references = ref_list.get('Reference', [])
    
    for r in references:
        if 'doi:' in r.get("ReferenceCitation", "").lower():
            doi = re.sub(".*doi:", "", r.get("ReferenceCitation", "")).strip().lower()
            doi = doi.split(" ")[0]
            if doi[-1] == ".":
                doi = doi[:-1]
            r['doi'] = doi
            if r.get('ReferenceType') in ['derived', 'result']:
                r.update(get_doi_info(doi))
            

    for f in ['background', 'derived', 'result']:
        elt['publications_'+f] = ";".join([p['doi'] for p in references if p.get('ReferenceType') == f and 'doi' in p])
        if f in ['derived', 'result']:
            for field in ['is_oa', 'journal_issns', 'journal_name', 'is_icmje']:
                elt['publications_'+f+'_'+field] = ";".join([p[field] for p in references if p.get('ReferenceType') == f and field in p])
        #elt['publications_'+f] = [p for p in references if p.get('ReferenceType') == f]
        
    elt['all_references'] = references    

    
    ## ipd individual patient data
    ipd_module = protocol.get('IPDSharingStatementModule', {})
    ipd_sharing = ipd_module.get('IPDSharing')
    elt['ipd_sharing'] = ipd_sharing
    
    ## sponsor
    sponsor_module = protocol.get('SponsorCollaboratorsModule', {})
    lead_sponsor = sponsor_module.get('LeadSponsor', {}).get('LeadSponsorName')
    elt['lead_sponsor'] = lead_sponsor
    
    ## contactLocation
    locations_module = protocol.get('ContactsLocationsModule', {})
    locations = locations_module.get('LocationList', {}).get('Location', [])
    location_country = ";".join(list(set(
        [x.get('LocationCountry') for x in locations if "LocationCountry" in x])))
    location_facility = ";".join(list(set(
        [x.get('LocationFacility') for x in locations if "LocationFacility" in x])))
    
    elt['location_country'] = location_country
    elt['location_facility'] = location_facility
    
    ## intervention
    intervention_module = protocol.get('ArmsInterventionsModule', {})
    interventions =  intervention_module.get('InterventionList', {}).get('Intervention', [])
    intervention_type = ";".join(list(set(
        [w.get('InterventionType') for w in interventions if 'InterventionType' in w])))
    elt['intervention_type'] = intervention_type
    
    
    return elt
