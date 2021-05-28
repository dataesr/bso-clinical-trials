from bso.server.main.clinical_trials import harvest_parse_clinical_trials
from bso.server.main.euctr import harvest_parse_euctr
from bso.server.main.merge_sources import merge_all
from bso.server.main.elastic import reset_index, load_in_es

def create_task_harvest(arg) -> dict:
    harvest_source = arg.get('source', '').lower()
    if harvest_source == "clinical-trials":
        return harvest_parse_clinical_trials()
    elif harvest_source == "euctr":
        return harvest_parse_euctr()
    return {}

def create_task_transform_load(arg) -> dict:
    data_to_import = merge_all()
    reset_index("bso-clinical-trials")
    load_in_es(data_to_import, "bso-clinical-trials")
    return {}
