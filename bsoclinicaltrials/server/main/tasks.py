import datetime

from bsoclinicaltrials.server.main.clinical_trials import harvest_parse_clinical_trials
from bsoclinicaltrials.server.main.ctis import harvest_parse_ctis
from bsoclinicaltrials.server.main.elastic import load_in_es, reset_index
from bsoclinicaltrials.server.main.enrich_ct import enrich
from bsoclinicaltrials.server.main.euctr import harvest_parse_euctr
from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.merge_sources import merge_all

logger = get_logger(__name__)

def create_task_harvest(args: dict) -> dict:
    source = args.get('source', '').lower()
    harvest = args.get('harvest', True)
    parse = args.get('parse', True)
    harvest_date = args.get('harvest_date')
    if source == 'clinical-trials':
        return harvest_parse_clinical_trials(harvest, parse, harvest_date)
    elif source == 'euctr':
        return harvest_parse_euctr(harvest, parse, harvest_date)
    elif source == 'ctis':
        return harvest_parse_ctis(harvest, parse, harvest_date)
    return {}


def create_task_transform_load(args: dict) -> dict:
    today = datetime.date.today()
    harvest_date_ct = args.get('harvest_date_ct', f'{today}')
    harvest_date_euctr = args.get('harvest_date_euctr', f'{today}')
    harvest_date_ctis = args.get('harvest_date_ctis', f'{today}')
    to_harvest = args.get('harvest', True)
    to_parse = args.get('parse', True)
    if to_harvest or to_parse:
        harvest_parse_clinical_trials(to_harvest=to_harvest, to_parse=to_parse, harvest_date=harvest_date_ct)
        harvest_parse_euctr(to_harvest=to_harvest, to_parse=to_parse, harvest_date=harvest_date_euctr)
        harvest_parse_ctis(to_harvest=to_harvest, to_parse=to_parse, harvest_date=harvest_date_ctis)
    merged_ct = merge_all(harvest_date_ct, harvest_date_euctr, harvest_date_ctis)
    data = enrich(merged_ct)
    current_date = today.isoformat()
    index = args.get('index', f'bso-clinical-trials-{current_date}')
    reset_index(index=index)
    load_in_es(data=data, index=index)
    # alias update should be done manually !
    return {'nb_data': len(data), 'index': index}
