from bs4 import BeautifulSoup
import datetime
import time
import re

from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils import my_parse_date, requests_retry_session
from bsoclinicaltrials.server.main.utils_swift import get_objects, set_objects

logger = get_logger(__name__)


def parse_all(harvested_data):
    parsed_data = []
    for d in harvested_data:
        parsed = parse_euctr(d)
        parsed_data.append(parsed)
    today = datetime.date.today()
    set_objects(parsed_data, 'clinical-trials', f'euctr_parsed_{today}.json.gz')
    return {
        'status': 'ok',
        'source': 'euctr',
        'nb_studies_harvested': len(harvested_data),
        'nb_studies_parsed': len(parsed_data)
    }


def harvest_parse_euctr(to_harvest=True, to_parse=True, harvest_date=""):
    if to_harvest:
        harvested_data = harvest()
        if to_parse:
            parse_all(harvested_data)
    else:
        if to_parse:
            harvested_data = get_objects("clinical-trials", f"euctr_raw_{harvest_date}.json.gz")
            parse_all(harvested_data)


def harvest():
    url = 'https://www.clinicaltrialsregister.eu/ctr-search/search?query=&country=fr&page='
    r = requests_retry_session().get(url + '1', verify=False)
    soup = BeautifulSoup(r.text, 'lxml')
    nb_pages = int(re.sub(".*Displaying page 1 of ", "",
                          soup.find(class_="outcome").get_text().replace("\n", " ")).split(".")[0])
    logger.debug(f'{nb_pages} from EUCTR to download')
    links_to_download = []
    for p in range(1, nb_pages + 1):
        try:
            r = requests_retry_session().get(url+str(p), verify=False)
        except:
            logger.debug(f'Ignoring page {url}{p} that cannot be downloaded')
            time.sleep(2)
            continue
        soup = BeautifulSoup(r.text, "lxml")
        current_links = []
        for link in soup.find_all('a'):
            href = link.attrs['href']
            if '/ctr-search/trial/' in href and '/FR' in href:
                current_links.append('https://www.clinicaltrialsregister.eu' + href)
        links_to_download += current_links
        time.sleep(2)
    htmls = []
    for ix, url in enumerate(links_to_download):
        try:
            r = requests_retry_session().get(url, verify=False)
        except:
            logger.debug(f'Ignoring page {url} that cannot be downloaded')
            time.sleep(2)
            continue
        htmls.append(r.text)
        time.sleep(1)
    today = datetime.date.today()
    set_objects(htmls, 'clinical-trials', f'euctr_raw_{today}.json.gz')
    return htmls


def parse_results(eudract):
    res = {}
    url = "https://www.clinicaltrialsregister.eu/ctr-search/trial/{}/results".format(eudract)
    try:
        r = requests_retry_session().get(url, verify=False)
    except:
        logger.debug(f"ignoring page {url} that cannot be downloaded")
        time.sleep(2)
        return res
    html = r.text

    soup = BeautifulSoup(html)
    trs = soup.find_all('tr')
    infos = {}
    for tr in trs:
        label_col = tr.find(class_="labelColumn")
        value_col = tr.find(class_="valueColumn")
        if label_col and value_col:
            infos[label_col.get_text(" ").strip()] = value_col.get_text(" ").strip()
    res['results_first_submit_date'] = my_parse_date(infos.get('First version publication date'), dayfirst=True)
    res['study_start_date'] = my_parse_date(infos.get('Actual start date of recruitment'), dayfirst=True)
    if len(infos.get('US NCT number', '')) > 3:
        res['NCTId'] = infos.get('US NCT number')
    if len(infos.get('ISRCTN number', '')) > 3:
        res['ISRCTN'] = infos.get('ISRCTN number')
    if len(infos.get('WHO universal trial number (UTN)', '')) > 3:
        res['WHO'] = infos.get('WHO universal trial number (UTN)')
    try:
        res['enrollment_count'] = int(infos.get('Worldwide total number of subjects'))
    except:
        pass
    return res


def parse_euctr(html):
    soup = BeautifulSoup(html)
    summary_infos = {}
    try:
        tr_summary = soup.find(class_="section summary").find_all('tr')
        for tr in tr_summary:
            tds = tr.find_all('td')
            if len(tds) == 2:
                summary_key = tds[0].get_text(" ").replace(':', '').strip()
                summary_value = tds[1].get_text(" ").strip()
                summary_infos[summary_key] = summary_value
    except:
        pass
    tr_info = soup.find_all('tr', class_="tricell")
    infos = {}
    for tr in tr_info:
        try:
            info_key_nb = tr.find('td', class_="first").get_text(" ").strip()
            info_key_str = tr.find('td', class_="second").get_text(" ").strip()
            info_key = "{};{}".format(info_key_nb, info_key_str)
            info_value = tr.find('td', class_="third").get_text(" ").strip()
            infos[info_key] = info_value
        except:
            continue
    res = {
        'AudraCT': infos.get('A.2;EudraCT number'),
        'has_results': summary_infos.get('Trial results') == 'View results'
    }
    res['has_results_or_publications'] = res['has_results']
    if res['has_results']:
        results_res = parse_results(res['eudraCT'])
        res.update(results_res)
    res['title'] = infos.get("A.3;Full title of the trial")
    res['acronym'] = infos.get("A.3.2;Name or abbreviated title of the trial where available")
    other_ids = []
    if "A.4.1;Sponsor's protocol code number" in infos:
        other_id = {'type': 'org_study_id', 'id': infos.get("A.4.1;Sponsor's protocol code number")}
        other_ids.append(other_id)
    if len(other_ids) > 0:
        res['other_ids'] = other_ids
    res['lead_sponsor'] = infos.get("B.1.1;Name of Sponsor")
    res['study_type'] = summary_infos.get("Clinical Trial Type")
    res['study_first_submit_date'] = \
        my_parse_date(summary_infos.get('Date on which this record was first entered in the EudraCT database'),
                      dayfirst=True)
    res['study_completion_date'] = my_parse_date(infos.get("P.;Date of the global end of the trial"), dayfirst=True)
    res['status'] = summary_infos.get("Trial Status")
    res['study_type'] = "Interventional"
    return res
