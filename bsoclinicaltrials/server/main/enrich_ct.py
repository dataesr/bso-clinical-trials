import pandas as pd

from bsoclinicaltrials.server.main.sirano import get_sirano
from bsoclinicaltrials.server.main.strings import normalize
from bsoclinicaltrials.server.main.utils import chunks, get_dois_info


def tag_sponsor(x):
    x_normalized = normalize(x)
    for f in ["hopit", "hosp", "universi", "chu ", "ihu ", "cmc ", "gustave roussy", "pasteur",
              "leon berard", " national", "calmettes", "calmette", "curie", "direction centrale", "société francaise",
              "anrs", "inserm", "unicancer", "polyclinique", "institut régional", "hotel dieu",
              "imagine institute", "cardiometabolisme", "cardiométabolisme", "foresight", "rythme cardiaque",
            # CLCC
              "lutte contre le cancer", "oscar lambret", "baclesse", "aurelle",
              "becquerel", "roussy", "godinot", "de lorraine", "strasbourg", "institut De cancerologie",
              "marquis", "francois leclerc", "françois leclerc", "jean perrin", "bérard", "berard",
              "bergonié", "bergonie", "claudius regaud", "oncopole", "institut du cancer", "lacassagne", "catherine"]:
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
        for date in enriched.get("results_details", {}):
            for reference in enriched["results_details"][date].get("references", []):
                if reference.get('doi') and reference.get('type') in ['result', 'derived']:
                    dois_to_get.append(reference['doi'])
        res.append(enriched)
    dois_info_dict = {}
    for c in chunks(list(set(dois_to_get)), 500):
        dois_info = get_dois_info(
            [{'doi': doi, 'id': f'doi{doi}', 'all_ids': [f'doi{doi}']} for doi in c])
        for info in dois_info:
            doi = info['doi']
            dois_info_dict[doi] = info
    for p in res:
        p["observation_dates"] = list(p.get("results_details", {}).keys())
        for date in p.get("results_details", {}):
            has_publication_oa = None
            p["results_details"][date]["has_results_or_publications_within_1y"] = False
            p["results_details"][date]["has_results_or_publications_within_3y"] = False
            publication_access = []
            publications_date = []
            for reference in p["results_details"][date].get("references", []):
                doi = reference.get("doi")
                if doi:
                    if doi in dois_info_dict:
                        for field in ["observation_dates", "published_date", "publisher_dissemination", "year"]:
                            if field in dois_info_dict[doi]:
                                reference[field] = dois_info_dict[doi][field]
                    if reference.get("type") in ["derived", "result"]:
                        if isinstance(reference.get("published_date"), str):
                            publications_date.append(reference.get("published_date"))
                        if has_publication_oa is None:
                            has_publication_oa = False
                        oa_details = dois_info_dict.get(doi, {}).get("oa_details", {})
                        if len(oa_details) == 0:
                            continue
                        last_obs_date = max(reference.get("observation_dates", []))
                        for obs_date in oa_details:
                            if obs_date == last_obs_date:
                                oa_detail = oa_details[obs_date]
                                reference["oa_details_latest"] = oa_detail
                                is_oa = oa_detail.get("is_oa", False)
                                publication_access.append(is_oa)
                                has_publication_oa = has_publication_oa or is_oa  # at least one publi is oa
            if publications_date:
                p["results_details"][date]["first_publication_date"] = min(publications_date)
            if isinstance(p["results_details"][date].get("results_first_submit_date"), str) and isinstance(p["results_details"][date].get("first_publication_date"), str):
                p["results_details"][date]["first_results_or_publication_date"] = min(
                    p["results_details"][date]["results_first_submit_date"], p["results_details"][date]["first_publication_date"])
            elif isinstance(p["results_details"][date].get("results_first_submit_date"), str):
                p["results_details"][date]["first_results_or_publication_date"] = p["results_details"][date]["results_first_submit_date"]
            elif isinstance(p["results_details"][date].get("first_publication_date"), str):
                p["results_details"][date]["first_results_or_publication_date"] = p["results_details"][date]["first_publication_date"]
            if isinstance(p["results_details"][date].get("first_results_or_publication_date"), str) and isinstance(p.get("study_completion_date"), str):
                p["results_details"][date]["delay_first_results_completion"] = (pd.to_datetime(p["results_details"][date]["first_results_or_publication_date"]) - pd.to_datetime(
                    p["study_completion_date"])).days
                p["results_details"][date]["has_results_or_publications_within_1y"] = (
                    p["results_details"][date]["delay_first_results_completion"] <= 365)
                p["results_details"][date]['has_results_or_publications_within_3y'] = (
                    p["results_details"][date]["delay_first_results_completion"] <= 365 * 3)
            p["results_details"][date]['has_publication_oa'] = has_publication_oa
            p["results_details"][date]['publication_access'] = publication_access
        lead_sponsor = p.get("lead_sponsor")
        if lead_sponsor and isinstance(lead_sponsor, str):
            lead_sponsor_normalized = sponsors_dict.get(normalize(lead_sponsor))
            if lead_sponsor_normalized:
                p["lead_sponsor_normalized"] = lead_sponsor_normalized.get("sponsor_normalized")
                p["ror"] = lead_sponsor_normalized.get("ror")
            else:
                p["lead_sponsor_normalized"] = lead_sponsor
            p["lead_sponsor_type"] = tag_sponsor(p["lead_sponsor_normalized"])
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
    ct["french_location_only"] = french_location_only
    for date in ct.get("results_details", {}):
        ct["results_details"][date]["publications_result"] = []
        for reference in ct["results_details"][date].get("references", []):
            # Exclude publications whose type is not "result" or "derived", by example "background"
            # Exclude publications that have the word "protocol" in their title
            if reference.get("type", "").lower() in ["result", "derived"] and "protocol" not in reference["citation"].lower():
                if "doi" in reference:
                    ct["results_details"][date]["publications_result"].append(reference["doi"])
                elif 'pmid' in reference:
                    ct["results_details"][date]["publications_result"].append(reference["pmid"])
                elif 'citation' in reference:
                    ct["results_details"][date]["publications_result"].append(reference["citation"])
                else:
                    ct["results_details"][date]["publications_result"].append("other")
        ct["results_details"][date]["has_publications_result"] = len(ct["results_details"][date]["publications_result"]) > 0
        ct["results_details"][date]["has_results_or_publications"] = ct["results_details"][date].get("has_results", False) or ct["results_details"][date]["has_publications_result"]
    current_status = ct.get("status")
    status_simplified = "Unknown"
    if current_status in ["Completed"]:
        status_simplified = "Completed"
    elif current_status in ["Ongoing", "Recruiting", "Active, not recruiting", "Not yet recruiting"]:
        status_simplified = "Ongoing"
    ct["status_simplified"] = status_simplified
    ct["bso_country"] = ["fr"]
    if isinstance(ct.get("NCTId"), str) and ct["NCTId"] in sirano_dict:
        ct.update(sirano_dict[ct["NCTId"]])
    return ct
