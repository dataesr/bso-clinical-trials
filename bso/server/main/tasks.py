import datetime

from bso.server.main.clinical_trials import harvest_parse_clinical_trials
from bso.server.main.elastic import load_in_es, reset_index, update_alias
from bso.server.main.enrich_ct import enrich
from bso.server.main.euctr import harvest_parse_euctr
from bso.server.main.merge_sources import merge_all


def create_task_harvest(args: dict) -> dict:
    source = args.get('source', '').lower()
    harvest = args.get('harvest', True)
    parse = args.get('parse', True)
    harvest_date = args.get('harvest_date')
    if source == 'clinical-trials':
        return harvest_parse_clinical_trials(harvest, parse, harvest_date)
    elif source == 'euctr':
        return harvest_parse_euctr(harvest, parse, harvest_date)
    return {}


def create_task_transform_load(args: dict) -> dict:
    if args.get('harvest', True):
        harvest_parse_clinical_trials()
        harvest_parse_euctr()
    today = datetime.date.today()
    harvest_date = args.get('harvest_date', today)
    merged_ct = merge_all(harvest_date)
    data = enrich(merged_ct)
    current_month = datetime.date.today().isoformat()[0:7]
    index = args.get('index', f'bso-clinical-trials-{current_month}')
    reset_index(index=index)
    load_in_es(data=data, index=index)
    alias = 'bso-clinical-trials'
    update_alias(alias=alias, old_index='bso-clinical-trials-*', new_index=index)
    return {'nb_data': len(data), 'index': index, 'alias': alias}
