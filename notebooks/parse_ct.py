import datetime
import math
import re
import requests
from dateutil import parser

def my_parse_date(x, dayfirst=False):
    if x:
        return parser.parse(x, dayfirst=dayfirst).isoformat()
    return x



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
    #description
    description_module = protocol.get('DescriptionModule', {})
    summary = description_module.get('BriefSummary')
    if summary:
        elt['summary'] = summary
    # Status
    status_module = protocol.get('StatusModule', {})
    study_start_date = status_module.get('StartDateStruct', {}).get('StartDate')
    study_start_date_type = status_module.get('StartDateStruct', {}).get('StartDateType')
    elt['study_start_date'] = my_parse_date(study_start_date)
    elt['study_start_date_type'] = study_start_date_type
    elt['status'] = status_module.get("OverallStatus")
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
        if r.get('ReferenceType') in ['result', 'derived'] and 'protocol' not in r['ReferenceCitation'].lower():
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
    ipd_sharing_description = ipd_module.get('IPDSharingDescription')
    elt['ipd_sharing'] = ipd_sharing
    elt['ipd_sharing_description'] = ipd_sharing_description
    # Sponsor
    sponsor_module = protocol.get('SponsorCollaboratorsModule', {})
    lead_sponsor = sponsor_module.get('LeadSponsor', {}).get('LeadSponsorName')
    elt['lead_sponsor'] = lead_sponsor
    collaborators = sponsor_module.get('CollaboratorList', [])
    elt['collaborators'] = []
    if collaborators:
        for k in collaborators.get('Collaborator', []):
            if k.get('CollaboratorName') and k not in elt['collaborators']:
                elt['collaborators'].append(k.get('CollaboratorName'))
    elt['sponsor_collaborators'] = [elt['lead_sponsor']] + elt['collaborators']
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
