import time
import datetime
import requests
import os
from dateutil import parser
from requests.adapters import HTTPAdapter

from requests.packages.urllib3.util.retry import Retry
from bsoclinicaltrials.server.main.logger import get_logger

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
    r = requests.post(f"{url_upw}/enrich", json={"publications":publications})
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
