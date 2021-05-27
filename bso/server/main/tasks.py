from bso.server.main.clinical_trials import harvest_parse_clinical_trials
from bso.server.main.euctr import harvest_parse_euctr

def create_task_harvest(arg) -> dict:
    harvest_source = arg.get('source', '').lower()
    if harvest_source == "clinical-trials":
        return harvest_parse_clinical_trials()
    elif harvest_source == "euctr":
        return harvest_parse_euctr()
    return {}
