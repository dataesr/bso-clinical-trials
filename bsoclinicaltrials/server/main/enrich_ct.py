import pandas as pd

from bsoclinicaltrials.server.main.sirano import get_sirano
from bsoclinicaltrials.server.main.strings import normalize
from bsoclinicaltrials.server.main.utils import chunks, get_dois_info


def tag_sponsor(x):
    x_normalized = normalize(x)
    for f in ["hopit", "hosp", "universi", "chu ", "ihu ", "cmc ", "gustave roussy", "pasteur",
              "leon berard", " national", "calmettes", "curie", "direction centrale", "société francaise",
              "anrs", "inserm", "unicancer"]:
        if f in x_normalized:
            return "academique"
    return "industriel"


def enrich(all_ct):
    res = []
    dois_to_get = []
    sirano_dict = get_sirano()
    sponsors_df = pd.read_csv("/src/bsoclinicaltrials/server/main/bso-lead-sponsors-mapping.csv")
    sponsors_dict = {}
    for _, row in sponsors_df.iterrows():
        sponsors_dict[normalize(row.get("sponsor"))] = { "sponsor_normalized" : row.get("sponsor_normalized"), "ror": row.get("ror") }
    for ct in all_ct:
        enriched = enrich_ct(ct, sirano_dict)
        references = enriched.get('references', [])
        for r in references:
            if r.get('doi') and r.get('type') in ['result', 'derived']:
                dois_to_get.append(r['doi'])
        res.append(enriched)
    dois_info_dict = {}
    for c in chunks(list(set(dois_to_get)), 1000):
        dois_info = get_dois_info(
            [{'doi': doi, 'id': f'doi{doi}', 'all_ids': [f'doi{doi}']} for doi in c])
        for info in dois_info:
            doi = info['doi']
            dois_info_dict[doi] = info
    for p in res:
        has_publication_oa = None
        p['has_results_or_publications_within_1y'] = False
        p['has_results_or_publications_within_3y'] = False
        publication_access = []
        publications_date = []
        for r in p['references']:
            if r.get('doi'):
                doi = r.get('doi')
                if doi in dois_info_dict:
                    for f in ['year', 'published_date', 'oa_details', 'publisher_dissemination', 'observation_dates']:
                        if f in dois_info_dict[doi]:
                            r[f] = dois_info_dict[doi][f]
                if r.get('type') in ['result', 'derived']:
                    if isinstance(r.get('published_date'), str):
                        publications_date.append(r.get('published_date'))
                    if has_publication_oa is None:
                        has_publication_oa = False
                    oa_details = r.get('oa_details', {})
                    if len(oa_details) == 0:
                        continue
                    last_obs_date = max(r.get('observation_dates', []))
                    for obs_date in r.get('oa_details', {}):
                        if obs_date == last_obs_date:
                            oa_detail = oa_details[obs_date]
                            is_oa = oa_detail.get('is_oa', False)
                            publication_access.append(is_oa)
                            has_publication_oa = has_publication_oa or is_oa  # at least one publi is oa
        if publications_date:
            p['first_publication_date'] = min(publications_date)
        if isinstance(p.get('results_first_submit_date'), str) and isinstance(p.get('first_publication_date'), str):
            p['first_results_or_publication_date'] = min(
                p['results_first_submit_date'], p['first_publication_date'])
        elif isinstance(p.get('results_first_submit_date'), str):
            p['first_results_or_publication_date'] = p['results_first_submit_date']
        elif isinstance(p.get('first_publication_date'), str):
            p['first_results_or_publication_date'] = p['first_publication_date']
        if isinstance(p.get('first_results_or_publication_date'), str) and isinstance(p.get('study_completion_date'),
                                                                                      str):
            p['delay_first_results_completion'] = (pd.to_datetime(p['first_results_or_publication_date']) - pd.to_datetime(
                p['study_completion_date'])).days
            p['has_results_or_publications_within_1y'] = (
                p['delay_first_results_completion'] <= 365)
            p['has_results_or_publications_within_3y'] = (
                p['delay_first_results_completion'] <= 365 * 3)
        p['has_publication_oa'] = has_publication_oa
        p['publication_access'] = publication_access
        lead_sponsor = p.get("lead_sponsor")
        if lead_sponsor:
            lead_sponsor_normalized = sponsors_dict.get(normalize(lead_sponsor))
            if lead_sponsor_normalized:
                p["lead_sponsor_normalized"] = lead_sponsor_normalized.get("sponsor_normalized")
                p["ror"] = lead_sponsor_normalized.get("ror")
            else:
                p["lead_sponsor_normalized"] = lead_sponsor
    return res


def enrich_ct(ct, sirano_dict):
    ct['study_start_year'] = None
    if isinstance(ct.get('study_start_date'), str):
        ct['study_start_year'] = int(ct['study_start_date'][0:4])
    ct['study_completion_year'] = None
    if isinstance(ct.get('study_completion_date'), str):
        ct['study_completion_year'] = int(ct['study_completion_date'][0:4])
    if isinstance(ct.get('study_start_date'), str) and isinstance(ct.get('study_first_submit_date'), str):
        delay_submission_start = (
                pd.to_datetime(ct['study_first_submit_date']) - pd.to_datetime(ct['study_start_date'])).days
        ct['delay_submission_start'] = delay_submission_start
    if isinstance(ct.get('study_start_date'), str) and isinstance(ct.get('study_first_submit_date'), str) \
            and ct['study_start_date'] > ct['study_first_submit_date']:
        ct['submission_temporality'] = 'before_start'
    elif isinstance(ct.get('study_first_submit_date'), str) and isinstance(ct.get('study_completion_date'), str) \
            and ct['study_completion_date'] >= ct['study_first_submit_date']:
        ct['submission_temporality'] = 'during_study'
    elif isinstance(ct.get('study_first_submit_date'), str) and isinstance(ct.get('study_completion_date'), str) \
            and ct['study_completion_date'] < ct['study_first_submit_date']:
        ct['submission_temporality'] = 'after_completion'
    else:
        ct['submission_temporality'] = None
    if isinstance(ct.get('study_completion_date'), str) and isinstance(ct.get('study_start_date'), str):
        delay_start_completion = (
                pd.to_datetime(ct['study_completion_date']) - pd.to_datetime(ct['study_start_date'])).days
        ct['delay_start_completion'] = delay_start_completion
    if isinstance(ct.get('lead_sponsor'), str):
        ct['lead_sponsor_type'] = tag_sponsor(ct['lead_sponsor'])
    french_location_only = None
    location_country = ct.get('location_country', [])
    if isinstance(location_country, list):
        location_country_lower = list(set([loc.lower() for loc in location_country]))
        if 'france' in location_country_lower:
            location_country_lower.remove('france')
        if len(location_country_lower) > 0:
            french_location_only = False
        else:
            french_location_only = True
    ct['french_location_only'] = french_location_only
    if ct.get('references') is None:
        ct['references'] = []
    references = ct['references']
    ct['publications_result'] = []
    for r in references:
        if r.get('type').lower() in ['result', 'derived']:
            if 'doi' in r:
                ct['publications_result'].append(r['doi'])
            elif 'pmid' in r:
                ct['publications_result'].append(r['pmid'])
            elif 'citation' in r:
                ct['publications_result'].append(r['citation'])
            else:
                ct['publications_result'].append('other')
    ct['has_publications_result'] = len(ct['publications_result']) > 0
    ct['has_results_or_publications'] = ct['has_results'] or ct['has_publications_result']
    current_status = ct.get('status')
    status_simplified = 'Unknown'
    if current_status in ['Completed']:
        status_simplified = 'Completed'
    elif current_status in ['Ongoing', 'Recruiting', 'Active, not recruiting', 'Not yet recruiting']:
        status_simplified = 'Ongoing'
    ct['status_simplified'] = status_simplified
    ct['bso_country'] = ['fr']
    if isinstance(ct.get('NCTId'), str) and ct['NCTId'] in sirano_dict:
        ct.update(sirano_dict[ct['NCTId']])
    return ct
