import pandas as pd
import datetime
from bso.server.main.logger import get_logger
from bso.server.main.utils_swift import get_objects, set_objects

logger = get_logger(__name__)

def get_each_sources():
    today = datetime.date.today()
    raw_trials = {}
    df_ct = pd.DataFrame(get_objects("clinical-trials", f"clinical_trials_parsed_{today}.json.gz"))
    df_ct['source'] = 'clinical_trials'
    raw_trials['NCTId'] = df_ct.to_dict(orient='records')
    nb_ct_clinical_trials = len(raw_trials['NCTId'])
    logger.debug(f"Nb CT from clinical_trials: {nb_ct_clinical_trials}")
    
    df_euctr = pd.DataFrame(get_objects("clinical-trials", f"euctr_parsed_{today}.json.gz"))
    df_euctr['source'] = 'clinical_trials'
    raw_trials['eudraCT'] = df_euctr.to_dict(orient='records')
    nb_ct_euctr = len(raw_trials['eudraCT'])
    logger.debug(f"Nb CT from euctr: {nb_ct_euctr}")
    return raw_trials

def merge_all():
    raw_trials = get_each_sources()
    ct_transformed = {}
    for k in raw_trials:
        ct_transformed[k] = {}
        for ct in raw_trials[k]:
            ct_transformed[k][ct[k]] = transform_ct(ct)
    matches = {}
    matches = update_matches(matches, raw_trials['NCTId'], 'NCTId', ['eudraCT'])
    matches = update_matches(matches, raw_trials['eudraCT'], 'eudraCT', ['NCTId'])


    known_ids = set([])
    all_ct = []

    for current_id_type in ['NCTId', 'eudraCT']:
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
                        print("missing {} in {}".format(other_id, other_id_type))
                    else:
                        other_version = ct_transformed[other_id_type][other_id]
                        ct_merge = merge_ct(ct_merge, other_version)
            all_ct.append(ct_merge)

            for i in current_ids:
                known_ids.add(i)

    all_ct_final = [untransform_ct(e) for e in all_ct]
    set_objects(all_ct_final, "clinical-trials", "merged_ct.json.gz")
    return all_ct_final

def untransform_ct(ct):
    new_ct = {}
    all_sources = [e['source'] for e in ct['source']]
    all_sources.sort()

    new_ct['all_sources'] = ";".join(all_sources)
    for f in ct:
        if len(ct[f]) == 0:
            continue
        if len(ct[f]) ==  1:
            new_ct[f] = ct[f][0][f]
        else:
            all_values = []
            for v in ct[f]:
                if isinstance(v, dict) and f in v:
                    all_values.append(v[f])
            if len(list(set(all_values))) == 1:
                new_ct[f] = all_values[0]
            else:
                new_ct[f] = ct[f]

            if len(list(set(all_values))) >= 1:
                new_ct[f] = all_values[0]
            else:
                new_ct[f]=""


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
        elif len(ct_org[field]) > 1:
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

