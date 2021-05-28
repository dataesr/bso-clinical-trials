from bso.server.main.clinical_trials import harvest_parse_clinical_trials
from bso.server.main.euctr import harvest_parse_euctr
from bso.server.main.merge_sources import merge_all
from bso.server.main.elastic import reset_index, load_in_es

def create_task_harvest(arg) -> dict:
    source = arg.get('source', '').lower()
    harvest = arg.get('harvest', True)
    parse = arg.get('parse', True)
    harvest_date = arg.get('harvest_date')
    if source == "clinical-trials":
        return harvest_parse_clinical_trials(harvest, parse, harvest_date)
    elif source == "euctr":
        return harvest_parse_euctr(harvest, parse, harvest_date)
    return {}

def create_task_transform_load(arg) -> dict:
    if arg.get('harvest', True):
        harvest_parse_clinical_trials()
        harvest_parse_euctr()
    data_to_import = merge_all()
    reset_index("bso-clinical-trials")
    load_in_es(data_to_import, "bso-clinical-trials")
    return {}
