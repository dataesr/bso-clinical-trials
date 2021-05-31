import pandas as pd
from bso.server.main.utils import get_dois_info, chunks

def enrich(all_ct):
    res = []
    dois_to_get = []
    for ct in all_ct:
        enriched = enrich_ct(ct)
        for r in enriched['references']:
            if 'doi:' in r.get("ReferenceCitation", "").lower():
                doi = re.sub(".*doi:", "", r.get("ReferenceCitation", "")).strip().lower()
                doi = doi.split(" ")[0]
                if doi[-1] == ".":
                    doi = doi[:-1]
                r['doi'] = doi
                if r.get('ReferenceType') in ['result', 'derived']:
                    dois_to_get.append(doi)
        res.append(enriched)
    
    dois_info_dict = {}
    for c in chunks(list(set(dois_to_get)), 1000): 
        dois_info = get_dois_info([{'doi': doi} for doi in c])
        for info in dois_info:
            doi = info['doi']
            dois_info_dict[doi] = info
    
    for p in res:
        has_publication_oa = None
        publication_access = []
        publications_date = []
        for r in p['references']:
            if r.get('doi'):
                doi = r.get('doi')
                if doi in dois_info_dict:
                    r.update(dois_info_dict[doi])
                if r.get('ReferenceType') in ['result']:
                    publications_date.append(r.get('published_date'))
                    if has_publication_oa is None:
                        has_publication_oa = False
                    oa_details = r.get('oa_details', [])
                    last_obs_date = max([oa_detail.get('observation_date') for oa_detail in oa_details])
                    for oa_detail in r.get('oa_details', []):
                        obs_date = oa_detail.get('observation_date')
                        if obs_date == last_obs_date:
                            is_oa = oa_detail.get('is_oa', False)
                            publication_access.append(is_oa)
                            has_publication_oa = has_publication_oa or is_oa # at least one publi is oa

        if publications_date:
            p['first_publication_date'] = min(publications_date)

        if p['results_first_submit_date'] and p['first_publication_date']:
            p['first_results_or_publication_date'] = min(p['results_first_submit_date'], p['first_publication_date'])
        elif p['results_first_submit_date'] :
              p['first_results_or_publication_date'] = p['results_first_submit_date'] 
        elif p['first_publication_date']:
             p['first_results_or_publication_date'] = p['first_publication_date']

        if p['first_results_or_publication_date'] and p['study_completion_date']:
            p['delay_first_results_completion'] = (pd.to_datetime(p['study_completion_date']) - pd.to_datetime(p['first_results_or_publication_date'])).days

        p['has_publication_oa'] = has_publication_oa
        p['publication_access'] = publication_access

    return res

def enrich_ct(ct):
    delay_submission_start = (pd.to_datetime(ct['study_start_date']) - pd.to_datetime(ct['study_first_submit_date'])).days
    ct['delay_submission_start'] = delay_submission_start
    if ct['study_start_date'] > ct['study_first_submit_date']:
        ct['submission_temporality'] = 'before_start'
    elif ct['study_completion_date'] >= ct['study_first_submit_date']
        ct['submission_temporality'] = 'during_study'
    else:
        ct['submission_temporality'] = 'after_completion'
    
    delay_start_completion = (pd.to_datetime(ct['study_completion_date']) - pd.to_datetime(ct['study_start_date'])).days
    ct['delay_start_completion'] = delay_start_completion

    if ct['enrollment_count'] < 50:
        ct['enrollment_count_type'] = '49 or less'
    elif ct['enrollment_count'] < 100
        ct['enrollment_count_type'] = '50 - 99'
    elif ct['enrollment_count'] < 500
        ct['enrollment_count_type'] = '100 - 499'
    elif ct['enrollment_count'] < 1000
        ct['enrollment_count_type'] = '500 - 999'
    elif ct['enrollment_count'] < 5000
        ct['enrollment_count_type'] = '1000 - 4999'
    elif ct['enrollment_count'] >= 5000
        ct['enrollment_count_type'] = '5000 or more'
    
    return ct
