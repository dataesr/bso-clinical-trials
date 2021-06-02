from bso.server.main.clinical_trials import harvest_parse_clinical_trials
from bso.server.main.euctr import harvest_parse_euctr
from bso.server.main.merge_sources import merge_all
from bso.server.main.enrich_ct import enrich
from bso.server.main.elastic import reset_index, load_in_es


def create_task_harvest(args) -> dict:
    source = args.get('source', '').lower()
    harvest = args.get('harvest', True)
    parse = args.get('parse', True)
    harvest_date = args.get('harvest_date')
    if source == "clinical-trials":
        return harvest_parse_clinical_trials(harvest, parse, harvest_date)
    elif source == "euctr":
        return harvest_parse_euctr(harvest, parse, harvest_date)
    return {}


def create_task_transform_load(args) -> dict:
    if args.get('harvest', True):
        harvest_parse_clinical_trials()
        harvest_parse_euctr()
    merged_ct = merge_all()
    data = enrich(merged_ct)
    index = 'bso-clinical-trials'
    reset_index(index=index)
    load_in_es(data=data, index=index)
    return {}
