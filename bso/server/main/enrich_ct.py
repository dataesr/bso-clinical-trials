import pandas as pd
import re

from bso.server.main.utils import chunks, get_dois_info
from bso.server.main.strings import normalize


def tag_sponsor(x):
    x_normalized = normalize(x)
    for f in ['hopit', 'hosp', 'universi', 'chu ', 'ihu ', 'cmc ', 'gustave roussy', 'pasteur',
              'leon berard', ' national', 'calmettes', 'curie', 'direction centrale', 'société francaise']:
        if f in x_normalized:
            return 'academique'
    return 'industriel'


def enrich(all_ct):
    res = []
    dois_to_get = []
    for ct in all_ct:
        enriched = enrich_ct(ct)
        references = enriched.get('references', [])
        for r in references:
            if 'doi:' in r.get('ReferenceCitation', '').lower():
                doi = re.sub(".*doi:", '', r.get('ReferenceCitation', '')).strip().lower()
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
            p['first_results_or_publication_date'] = min(p['results_first_submit_date'], p['first_publication_date'])
        elif isinstance(p.get('results_first_submit_date'), str):
            p['first_results_or_publication_date'] = p['results_first_submit_date']
        elif isinstance(p.get('first_publication_date'), str):
            p['first_results_or_publication_date'] = p['first_publication_date']
        if isinstance(p.get('first_results_or_publication_date'), str) and isinstance(p.get('study_completion_date'),
                                                                                      str):
            p['delay_first_results_completion'] = (pd.to_datetime(p['study_completion_date']) - pd.to_datetime(
                p['first_results_or_publication_date'])).days
        p['has_publication_oa'] = has_publication_oa
        p['publication_access'] = publication_access
    return res


def enrich_ct(ct):
    if isinstance(ct.get('study_start_date'), str) and isinstance(ct.get('study_first_submit_date'), str):
        delay_submission_start = (
                pd.to_datetime(ct['study_start_date']) - pd.to_datetime(ct['study_first_submit_date'])).days
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
    return ct
