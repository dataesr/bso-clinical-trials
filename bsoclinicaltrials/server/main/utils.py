import datetime
import os
import requests
import time

from dateutil import parser
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib import parse

from bsoclinicaltrials.server.main.config import ES_LOGIN_BSO_BACK, ES_PASSWORD_BSO_BACK, ES_URL, MOUNTED_VOLUME
from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils_swift import upload_object, get_objects_by_page

logger = get_logger(__name__)


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
    r = requests.post(f"{url_upw}/enrich", json={"publications": publications, "last_observation_date_only": True})
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


def dump_to_object_storage(args: dict) -> list:
    es_index = args.get('index_name', 'bso-clinical-trials')
    # 1. Dump ES bso-clinical-trials index data into temp file
    es_url_without_http = ES_URL.replace('https://', '').replace('http://', '')
    es_host = f'https://{ES_LOGIN_BSO_BACK}:{parse.quote(ES_PASSWORD_BSO_BACK)}@{es_url_without_http}'
    container = 'bso_dump'
    today = datetime.date.today().isoformat().replace('-', '')
    os.makedirs(MOUNTED_VOLUME, exist_ok=True)
    output_json_file = f'{MOUNTED_VOLUME}{es_index}_{today}.jsonl.gz'
    output_csv_file = f'{MOUNTED_VOLUME}{es_index}_{today}.csv'
    cmd_elasticdump = f'elasticdump --input={es_host}{es_index} --output={output_json_file} ' \
                      f'--type=data --sourceOnly=true --fsCompress=gzip --limit 10000'
    logger.debug(cmd_elasticdump)
    os.system(cmd_elasticdump)
    logger.debug('Elasticdump is done')
    # 2. Convert JSON file into CSV by selecting fields
    cmd_header = f"echo 'NCTId' > {output_csv_file}"
    logger.debug(cmd_header)
    os.system(cmd_header)
    cmd_jq = f"zcat {output_json_file} | jq -rc '[.NCTId]|flatten|@csv' >> {output_csv_file}"
    logger.debug(cmd_jq)
    os.system(cmd_jq)
    local_bso_filenames = []
    for page in range(1, 1000000):
        filenames = get_objects_by_page(container='bso-local', page=page, full_objects=False)
        if len(filenames) == 0:
            break
        for filename in filenames:
            logger.debug(f'Dump bso-local {filename}')
            local_bso_filenames += filename.split('.')[0].split('_')
    local_bso_filenames = list(set(local_bso_filenames))
    for local_affiliation in local_bso_filenames:
        logger.debug(f'bso-local files creation for {local_affiliation}')
        cmd_local_json = f'zcat {output_json_file} | fgrep {local_affiliation} > enriched_{local_affiliation}.jsonl'
        cmd_local_csv_header = f'head -n 1 {output_csv_file} > enriched_{local_affiliation}.csv'
        cmd_local_csv = f'cat {output_csv_file} | fgrep {local_affiliation} >> enriched_{local_affiliation}.csv'
        os.system(cmd_local_json)
        os.system(cmd_local_csv_header)
        os.system(cmd_local_csv)
        upload_object(container=container, filename=f'enriched_{local_affiliation}.jsonl')
        upload_object(container=container, filename=f'enriched_{local_affiliation}.csv')
        os.system(f'rm -rf enriched_{local_affiliation}.jsonl')
        os.system(f'rm -rf enriched_{local_affiliation}.csv')
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
