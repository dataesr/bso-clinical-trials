import datetime
import os
import requests
import time
import pandas as pd

from dateutil import parser
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib import parse

from bsoclinicaltrials.server.main.config import ES_LOGIN_BSO_BACK, ES_PASSWORD_BSO_BACK, ES_URL, MOUNTED_VOLUME
from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils_swift import upload_object, get_objects_by_page

logger = get_logger(__name__)

PUBLIC_API_PASSWORD = os.getenv('PUBLIC_API_PASSWORD')

def my_parse_date(x, dayfirst=False):
    if x:
        return parser.parse(x, dayfirst=dayfirst).isoformat()
    return x


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_dois_info(publications):
    start = datetime.datetime.now()
    nb = len(publications)
    if nb == 0:
        return publications
    logger.debug(f"getting doi info for {nb} publications")
    url_upw = os.getenv("PUBLICATIONS_MONGO_SERVICE")
    r = requests.post(f"{url_upw}/enrich", json={"publications": publications, "last_observation_date_only": True, "PUBLIC_API_PASSWORD": PUBLIC_API_PASSWORD})
    task_id = r.json()['data']['task_id']
    for i in range(0, 10000):
        r_task = requests.get(f"{url_upw}/tasks/{task_id}").json()
        status = r_task['data']['task_status']
        if status == "finished":
            ans = r_task['data']['task_result']
            break
        elif status in ["started", "queued"]:
            time.sleep(1)
            continue
        else:
            logger.debug("problem in getting doi info")
            logger.debug(r_task)
            ans = publications
            break
    end = datetime.datetime.now()
    delta = end - start
    logger.debug(f"time to get doi info : {delta}")
    return ans

    
def requests_retry_session(retries=10, backoff_factor=0.6, status_forcelist=(500, 502, 504), session=None,):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def pandas_to_csv(df):
    data = df.to_dict(orient='records')
    csv_data = []
    for d in data:
        elt = {}
        for f in ['ISRCTN', 'NCTId', 'WHO', 'acronym' ,'all_sources',
                      'delay_first_results_completion', 'delay_start_completion',
                 'delay_submission_start', 'design_allocation', 'enrollment_count',
            'enrollment_type', 'eudraCT', 'first_publication_date',
            'first_results_or_publication_date', 'french_location_only',
            'has_publication_oa', 'has_publications_result', 'has_results',
            'has_results_or_publications', 'intervention_type', 'ipd_sharing', 'ipd_sharing_description',
            'lead_sponsor', 'lead_sponsor_type', 'location_country', 'location_facility',
            'other_ids', 'primary_purpose', 'publication_access', 'publications_result',
            'references', 'results_first_submit_date', 'results_first_submit_qc_date',
            'snapshot_date', 'status', 'status_simplified', 'study_completion_date',
            'study_completion_date_type', 'study_completion_year',
            'study_first_submit_date', 'study_first_submit_qc_date',
            'study_start_date', 'study_start_date_type', 'study_start_year',
            'study_type', 'submission_temporality', 'time_perspective', 'title']:
            if isinstance(d.get(f), str) or isinstance(d.get(f), int) or isinstance(d.get(f), float):
                elt[f] = d[f]
            elif isinstance(d.get(f), list):
                if f == 'other_ids':
                    elt[f] = '|'.join([k['id'] for k in d[f]])
                elif f == 'references':
                    elt[f] = '|'.join([k.get('doi') for k in d[f] if k.get('doi')])
                elif f == 'publication_access':
                    elt[f] = '|'.join(str(d[f]))
                else:
                    elt[f] = '|'.join(d[f])
            elif d.get(f) is None:
                elt[f] = None
            else:
                print(f)
                print(type(d[f]))
                assert(False)
        csv_data.append(elt)
    df_csv = pd.DataFrame(csv_data)
    return df_csv


def dump_to_object_storage(args: dict) -> list:
    file_suffix = args.get('file_suffix', '')
    es_index = args.get('index_name', 'bso-clinical-trials')
    # 1. Dump ES bso-clinical-trials index data into temp file
    es_url_without_http = ES_URL.replace('https://', '').replace('http://', '')
    es_host = f'https://{ES_LOGIN_BSO_BACK}:{parse.quote(ES_PASSWORD_BSO_BACK)}@{es_url_without_http}'
    container = 'bso_dump'
    os.makedirs(MOUNTED_VOLUME, exist_ok=True)
    output_json_file = f'{MOUNTED_VOLUME}{es_index}{file_suffix}.jsonl.gz'
    output_csv_file = f'{MOUNTED_VOLUME}{es_index}{file_suffix}.csv'
    cmd_elasticdump = f'elasticdump --input={es_host}{es_index} --output={output_json_file} ' \
                      f'--type=data --sourceOnly=true --fsCompress=gzip --limit 10000'
    logger.debug(cmd_elasticdump)
    os.system(cmd_elasticdump)
    logger.debug('Elasticdump is done')
    # 2. Convert JSON file into CSV by selecting fields
    df_json=pd.read_json(output_json_file, lines=True)
    df_csv = pandas_to_csv(df_json)
    df_csv.to_csv(output_csv_file, index=False, sep=',')
    cmd_gzip = f'gzip {output_csv_file}'
    logger.debug(cmd_gzip)
    os.system(cmd_gzip)
    logger.debug('global csv file is created')
    # 3. Upload these files into OS
    uploaded_file_json = upload_object(container=container, filename=f'{output_json_file}')
    uploaded_file_csv = upload_object(container=container, filename=f'{output_csv_file}.gz')
    # 4. Clean temporary files
    os.system(f'rm -rf {output_json_file}')
    os.system(f'rm -rf {output_csv_file}.gz')
    return [uploaded_file_json, uploaded_file_csv]
