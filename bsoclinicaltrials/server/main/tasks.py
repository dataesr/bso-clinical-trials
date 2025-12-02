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
    harvest_dates = args.get('harvest_dates')
    if source == 'clinical-trials':
        return harvest_parse_clinical_trials(harvest, parse, harvest_dates)
    elif source == 'euctr':
        return harvest_parse_euctr(harvest, parse, harvest_dates)
    elif source == 'ctis':
        return harvest_parse_ctis(harvest, parse, harvest_dates)
    return {}


def create_task_transform_load(args: dict) -> dict:
    today = datetime.date.today()
    harvest_dates_ct = args.get('harvest_dates_ct', f'{today}')
    harvest_dates_euctr = args.get('harvest_dates_euctr', f'{today}')
    harvest_dates_ctis = args.get('harvest_dates_ctis', f'{today}')
    to_harvest = args.get('harvest', True)
    to_parse = args.get('parse', True)
    if to_harvest or to_parse:
        harvest_parse_clinical_trials(to_harvest=to_harvest, to_parse=to_parse, harvest_dates=harvest_dates_ct)
        harvest_parse_euctr(to_harvest=to_harvest, to_parse=to_parse, harvest_dates=harvest_dates_euctr)
        harvest_parse_ctis(to_harvest=to_harvest, to_parse=to_parse, harvest_dates=harvest_dates_ctis)
    merged_ct = merge_all(harvest_dates_ct, harvest_dates_euctr, harvest_dates_ctis)
    data = enrich(merged_ct, harvest_dates_ct, harvest_dates_euctr, harvest_dates_ctis)
    current_date = today.strftime('%Y%m%d')
    index = args.get('index', f'bso-clinical-trials-{current_date}')
    reset_index(index=index)
    load_in_es(data=data, index=index)
    # Alias update should be done manually !
    return {'nb_data': len(data), 'index': index}
