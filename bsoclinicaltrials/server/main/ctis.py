import datetime
import requests

from bsoclinicaltrials.server.main.logger import get_logger
from bsoclinicaltrials.server.main.utils import my_parse_date
from bsoclinicaltrials.server.main.utils_swift import get_objects, set_objects


container = "clinical-trials"
logger = get_logger(__name__)


def harvest():
    # 1. Collect all clinical trials
    cts = []
    page = 0
    per_page = 400
    while True:
        page += 1
        r = requests.post("https://euclinicaltrials.eu/ctis-public-api/search", verify=False, json={
            "pagination": {
                "page": page,
                "size": per_page
            },
            "sort": {
                "property": "ctNumber",
                "direction": "ASC"
            },
            "searchCriteria": {
                "containAll": "",
                "containAny": "",
                "containNot": ""
            }
        })
        data = r.json().get("data", [])
        cts += data
        if len(data) < per_page:
            break
    # 2. For each French clinical trial, find detailed metadata
    cts_fr = []
    for ct in cts:
        # Filter on French clinical trials
        if "france:" in [country.lower() for country in ct.get("trialCountries")]:
            r = requests.get(
                f"https://euclinicaltrials.eu/ctis-public-api/retrieve/{ct.get('ctNumber')}", verify=False)
            cts_fr.append(r.json())
    # 3. Save it in Object Storage
    today = datetime.date.today()
    set_objects(cts_fr, container, f"ctis_raw_{today}.json.gz")
    return cts_fr


def parse_ctis(ct):
    status_mapping = {
        "Authorised, not started": "Active, not recruiting",
        "Ongoing, recruiting": "Recruiting",
        "Ongoing, not yet recruiting": "Not yet recruiting",
        "Ongoing, recruitment ended": "Active, not recruiting",
        "Ended": "Completed",
        "Not authorised": "Not authorised",
        "Halted": "Suspended",
        "Revoked": "Withdrawn"
    }

    res = {
        "CTIS": ct.get("ctNumber"),
    }
    res["title"] = ct.get("authorizedApplication", {}).get("authorizedPartI", {}).get(
        "trialDetails", {}).get("clinicalTrialIdentifiers", {}).get("fullTitle")
    res["study_start_dat"] = ct.get("startDateEU")
    countries = ct.get("authorizedApplication").get("authorizedPartsII")
    res["enrollment_count"] = sum([country.get("recruitmentSubjectCount", 0) for country in countries])
    # Results
    results = ct.get("results", {})
    results = results.get("summaryResults", []) + results.get(
        "laypersonResults", []) + results.get("clinicalStudyReports", [])
    res["has_results"] = len(results) > 0
    res["has_results_or_publications"] = res["has_results"]
    if len(results) > 0:
        dates = [result.get("createdOn") for result in results]
        dates.sort()
        res["results_first_submit_date"] = my_parse_date(dates[0])
    res["acronym"] = ct.get("authorizedApplication", {}).get("authorizedPartI", {}).get(
        "trialDetails", {}).get("clinicalTrialIdentifiers", {}).get("shortTitle")
    # External ids
    other_ids = []
    nct_id = ct.get("authorizedApplication", {}).get("authorizedPartI", {}).get("trialDetails", {}).get(
        "clinicalTrialIdentifiers", {}).get("secondaryIdentifyingNumbers", {}).get("nctNumber", {}).get("number")
    if nct_id:
        other_id = {"id": nct_id, "source": "CTIS", "type": "NCTId"}
        other_ids.append(other_id)
        res["NCTId"] = nct_id
    who_id = ct.get("authorizedApplication", {}).get("authorizedPartI", {}).get("trialDetails", {}).get(
        "clinicalTrialIdentifiers", {}).get("secondaryIdentifyingNumbers", {}).get("whoUniversalTrialNumber", {}).get("number")
    if who_id:
        other_id = {"id": who_id, "source": "CTIS", "type": "WHO_UTN"}
        other_ids.append(other_id)
        res["WHO"] = who_id
    isrctn_id = ct.get("authorizedApplication", {}).get("authorizedPartI", {}).get("trialDetails", {}).get(
        "clinicalTrialIdentifiers", {}).get("secondaryIdentifyingNumbers", {}).get("isrctnNumber", {}).get("number")
    if isrctn_id:
        other_id = {"id": isrctn_id, "source": "CTIS", "type": "ISRCTN_NUMBER"}
        other_ids.append(other_id)
        res["ISRCTN"] = isrctn_id
    additional_ids = ct.get("authorizedApplication", {}).get("authorizedPartI", {}).get("trialDetails", {}).get(
        "clinicalTrialIdentifiers", {}).get("secondaryIdentifyingNumbers", {}).get("additionalRegistries", [])
    for additional_id in additional_ids:
        id = additional_id.get("number")
        if id and id != "N/A":
            other_id = {"id": id, "source": "CTIS",
                        "type": additional_id.get("otherRegistryName")}
            other_ids.append(other_id)
    if len(other_ids) > 0:
        res["other_ids"] = other_ids
    # Lead sponsor
    sponsors = ct.get("authorizedApplication", {}).get(
        "authorizedPartI", {}).get("sponsors", [])
    primary_sponsors = [s for s in sponsors if s.get("primary", False) is True]
    if len(primary_sponsors) > 0:
        res["lead_sponsor"] = primary_sponsors[0].get("publicContacts", [])[
            0].get("organisation", {}).get("name")
    # ?? res['study_type'] = summary_infos.get("Clinical Trial Type")
    res["study_first_submit_date"] = my_parse_date([t for t in ct.get("authorizedApplication", {}).get(
        "applicationInfo", []) if t.get("type") == "INITIAL"][0].get("submissionDate"))
    res["study_completion_date"] = my_parse_date(ct.get("endDateEU"))
    res["status"] = status_mapping.get(ct.get("ctPublicStatus"), "Unknown status")
    res["study_type"] = "Interventional"
    return res


def parse(harvested_data, harvest_date=None):
    if harvest_date is None:
        today = datetime.date.today()
        harvest_date = f"{today}"
    parsed_data = []
    for ct in harvested_data:
        parsed = parse_ctis(ct)
        parsed_data.append(parsed)
    set_objects(parsed_data, container, f"ctis_parsed_{harvest_date}.json.gz")
    return {
        "status": "ok",
        "harvest_date": f"{harvest_date}",
        "source": "ctis",
        "nb_studies_harvested": len(harvested_data),
        "nb_studies_parsed": len(parsed_data)
    }


def harvest_parse_ctis(to_harvest=True, to_parse=True, harvest_date=None):
    if to_harvest:
        harvested_data = harvest()
    else:
        harvested_data = [x[0] for x in get_objects(
            container, f"ctis_raw_{harvest_date}.json.gz")]
    if to_parse:
        return parse(harvested_data, harvest_date)
