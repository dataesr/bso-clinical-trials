import pandas as pd

from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils_swift import get_objects, set_objects

logger = get_logger(__name__)


def get_each_sources(date_ct, date_euctr, date_ctis):
    raw_trials = {}
    logger.debug(f'getting clinicaltrials data from {date_ct}')
    df_ct = pd.DataFrame(get_objects("clinical-trials", f"clinical_trials_parsed_{date_ct}.json.gz"))
    df_ct['source'] = 'clinical_trials'
    raw_trials['NCTId'] = df_ct.to_dict(orient='records')
    nb_ct_clinical_trials = len(raw_trials['NCTId'])
    logger.debug(f"Nb CT from clinical_trials: {nb_ct_clinical_trials}")
    
    logger.debug(f'getting euctr data from {date_euctr}')
    df_euctr = pd.DataFrame(get_objects("clinical-trials", f"euctr_parsed_{date_euctr}.json.gz"))
    df_euctr['source'] = 'euctr'
    raw_trials['eudraCT'] = df_euctr.to_dict(orient='records')
    nb_ct_euctr = len(raw_trials['eudraCT'])
    logger.debug(f"Nb CT from euctr: {nb_ct_euctr}")

    logger.debug(f'getting ctis data from {date_ctis}')
    df_ctis = pd.DataFrame(get_objects("clinical-trials", f"ctis_parsed_{date_ctis}.json.gz"))
    df_ctis['source'] = 'ctis'
    raw_trials['CTIS'] = df_ctis.to_dict(orient='records')
    nb_ct_ctis = len(raw_trials['ctis'])
    logger.debug(f"Nb CT from ctis: {nb_ct_ctis}")

    return raw_trials


def merge_all(date_ct, date_euctr, date_ctis):
    # each field is transformed (transform_ct function) to become a list of element, each element with a source
    # after merge, the untransform_ct function turns back to a proper schema
    raw_trials = get_each_sources(date_ct, date_euctr, date_ctis)
    ct_transformed = {}
    for k in raw_trials:
        ct_transformed[k] = {}
        for ct in raw_trials[k]:
            ct_transformed[k][ct[k]] = transform_ct(ct)
    matches = {}
    matches = update_matches(matches, raw_trials["NCTId"], "NCTId", ["eudraCT"])
    matches = update_matches(matches, raw_trials["eudraCT"], "eudraCT", ["NCTId"])
    matches = update_matches(matches, raw_trials["CTIS"], "CTIS", ["NCTId"])
    known_ids = set([])
    all_ct = []
    for current_id_type in ["NCTId", "eudraCT", "CTIS"]:
        for ct in raw_trials[current_id_type]:
            if ct[current_id_type] in known_ids:
                continue
            ct_merge = ct_transformed[current_id_type][ct[current_id_type]]
            current_ids = [ct[current_id_type]]
            if ct[current_id_type] in matches:
                for x in matches[ct[current_id_type]]:
                    other_id_type = list(matches[ct[current_id_type]][0].keys())[0]
                    other_id = matches[ct[current_id_type]][0][other_id_type]
                    current_ids.append(other_id)
                    if other_id not in ct_transformed[other_id_type]:
                        pass
                    else:
                        other_version = ct_transformed[other_id_type][other_id]
                        ct_merge = merge_ct(ct_merge, other_version)
            all_ct.append(ct_merge)
            for i in current_ids:
                known_ids.add(i)
    all_ct_final = [untransform_ct(e) for e in all_ct]
    for ct in all_ct_final:
        ct['snapshot_date'] = max(date_ct, date_euctr)
    set_objects(all_ct_final, "clinical-trials", f"merged_ct_{ct['snapshot_date']}.json.gz")
    return all_ct_final


def untransform_ct(ct):
    list_of_dict = ['references', 'other_ids']
    list_of_str = ['location_country', 'location_facility', 'collaborators', 'sponsor_collaborators', 'publications_result']
    new_ct = {}
    all_sources = [e['source'] for e in ct['source']]
    all_sources.sort()
    new_ct['all_sources'] = all_sources
    for f in ct:
        if f == "source":
            continue
        elif len(ct[f]) == 0:
            new_ct[f] = None
        elif f in list_of_dict:
            new_ct[f] = ct[f]
        elif f in list_of_str:
            new_ct[f] = [elt[f] for elt in ct[f]]
        elif len(ct[f]) == 1:
            new_ct[f] = ct[f][0][f]
        else:
            possibilities = [ct[f][i][f] for i in range(0, len(ct[f])) if f in ct[f][i]]
            sources = [ct[f][i]['source'] for i in range(0, len(ct[f]))]
            if isinstance(possibilities[0], bool):
                new_ct[f] = any(possibilities)  # at least one True
            elif 'clinical_trials' in sources:
                new_ct[f] = [ct[f][i][f] for i in range(0, len(ct[f])) if ct[f][i]['source'] == "clinical_trials"][0]
            else:
                logger.debug("THAT SHOULD NOT HAPPEN ??")
                logger.debug(ct[f])
    return new_ct


def update_matches(matches, new_trials, id1_type, other_ids):
    for ct in new_trials:
        id1 = ct[id1_type]
        for id2_type in other_ids:
            if id2_type in ct and ct[id2_type]:
                id2 = ct[id2_type]
                if id1 not in matches:
                    matches[id1] = []
                matches[id1].append({id2_type: id2})
                if id2 not in matches:
                    matches[id2] = []
                matches[id2].append({id1_type: id1})
    return matches


def transform_ct(ct_org):
    ct = {}
    if ct_org is None:
        return {}
    source = ct_org.get('source', 'missing_source')
    for field in ct_org:
        if ct_org[field] is None or (isinstance(ct_org[field], float) and pd.isna(ct_org[field])):
            continue
        if not isinstance(ct_org[field], list):
            ct[field] = [ct_org[field]]
        elif len(ct_org[field]) >= 1:
            ct[field] = ct_org[field]
        else:
            continue
        new_value = []
        for elt in ct[field]:
            if elt is None:
                continue
            if not isinstance(elt, dict):
                if pd.isnull(elt):
                    continue
                elt = {field: elt}
            if 'source' not in elt:
                elt['source'] = source
            new_value.append(elt)
        if len(new_value) > 0:
            ct[field] = new_value
    return ct


def merge_ct(ct1, ct2):
    ct = {}
    fields = list(set(list(ct1.keys()) + list(ct2.keys())))
    for f in fields:
        ct[f] = ct1.get(f, [])
        for e in ct2.get(f, []):
            if e not in ct[f]:
                ct[f].append(e)
    return ct
