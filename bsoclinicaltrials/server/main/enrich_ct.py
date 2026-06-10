import pandas as pd

from bsoclinicaltrials.server.main.sirano import get_sirano
from bsoclinicaltrials.server.main.strings import normalize
from bsoclinicaltrials.server.main.utils import chunks, get_dois_info


def tag_sponsor(x):
    x_normalized = normalize(x)
    academic_lead_sponsors = [
        "hopit",
        "hosp",
        "universi",
        "chu ",
        "ihu ",
        "cmc ",
        "gustave roussy",
        "pasteur",
        "leon berard",
        " national",
        "calmettes",
        "calmette",
        "curie",
        "direction centrale",
        "société francaise",
        "anrs",
        "inserm",
        "unicancer",
        "polyclinique",
        "institut régional",
        "hotel dieu",
        "imagine institute",
        "cardiometabolisme",
        "cardiométabolisme",
        "foresight",
        "rythme cardiaque",
        # CLCC
        "lutte contre le cancer",
        "oscar lambret",
        "baclesse",
        "aurelle",
        "becquerel",
        "roussy",
        "godinot",
        "de lorraine",
        "strasbourg",
        "institut De cancerologie",
        "marquis",
        "francois leclerc",
        "françois leclerc",
        "jean perrin",
        "bérard",
        "berard",
        "bergonié",
        "bergonie",
        "claudius regaud",
        "oncopole",
        "institut du cancer",
        "lacassagne",
        "catherine",
        # Specific lead_sponsors
        "Institut Mutualiste Montsouris",
        "Ecole des Hautes Etudes en Santé Publique",
        "Etablissement Français du Sang",
        "Institut de Radioprotection et de Surete Nucleaire",
        "Acute Leukemia French Association",
        "ADIR Association",
        "Ages et Vies Association",
        "Alliance Pour La Recherche en Cancerologie",
        "Association Accompagnement pour un Internet en Médecine et Santé au Service des Usagers",
        "Association APPROCHE",
        "Association de Recherche Bibliographique pour les Neurosciences",
        "Association for Innovation and Biomedical Research on Light and Image",
        "Association for Training, Education, and Research in Hematology, Immunology, and Transplantation",
        "Association Francaise d'Urologie",
        "Association Francaise pour la Recherche Thermale",
        "Association pour la Recherche Clinique et Immunologique",
        "Association pour le Développement et l'Organisation de la Recherche en Pneumologie et sur le Sommeil",
        "Association Pro-arte",
        "Association REMEDE",
        "Australian and New Zealand Intensive Care Research Centre",
        "Baim Institute for Clinical Research",
        "Baylor Research Institute",
        "Canadian Cancer Trials Group",
        "Cancer Trials Ireland",
        "Cardiovascular and Pulmonary Rehabilitation Center of Saint Orens",
        "Centre Bouffard Vercelli - USSAP",
        "Centre de Pharmacologie Clinique Applique a la Dermatologie",
        "Centre de Recherches et d'Etude sur la Pathologie Tropicale et le Sida",
        "Centre de Rééducation et Réadaptation Fonctionnelle La Châtaigneraie",
        "Centre d'Etude des Cellules Souches (CECS)",
        "Centre d'Expertise sur l'Altitude EXALT",
        "Centre d'Investigation Clinique et Technologique 805",
        "Centre Européen d'Enseignement Supérieur de l'Ostéopathie de Lyon",
        "Centre Europeen d'Etude du Diabete",
        "Centre Médical Porte Verte",
        "Centre Médico-Chirurgical de Réadaptation des Massues Croix Rouge Française",
        "Centre Mutualiste de Rééducation et de Réadaptation Fonctionnelles de Kerpape",
        "Centre Psychothérapique de Nancy",
        "Centre Recherche Cardio Vasculaire Alpes",
        "Clinical Centre of Serbia",
        "Clinique Ambroise Paré",
        "Clinique Beau Soleil",
        "Clinique Bizet",
        "Clinique de la Mitterie",
        "Clinique de la Sauvegarde",
        "Clinique de lEurope a Amiens",
        "Clinique du Trocadéro",
        "Clinique Générale dAnnecy",
        "Clinique Juge",
        "Clinique Les Trois Soleils",
        "Clinique MEGIVAL",
        "Clinique Mutualiste la Sagesse",
        "Clinique Paris-Bercy",
        "Clinique Saint Jean, France",
        "Dieulefit Santé Centre de Réadaptation",
        "EORTC European Organisation for Research and Treatment of Cancer",
        "Erasmus Medical Center",
        "European Organisation for Research and Treatment of Cancer - EORTC",
        "Federation Francophone de Cancerologie Digestive",
        "Fédération Francophone de Cancérologie Digestive",
        "Fédération Francophone de Cancérologie Digestive (FFCD)",
        "Groupe d'Etude sur le Risque d'Exposition des Soignants aux Agents Infectieux",
        "Institut De La Colonne Vertebrale Et Des Neurosciences",
        "Institut de Recherche pour le Developpement",
        "Institut de Recherche sur la Moelle épinière et l'Encéphale",
        "Institut Franco Europeen de Chiropratique",
        "Institut Jules Bordet",
        "Institute of Tropical Medicine, Belgium",
        "Intergroupe Francophone de Cancerologie Thoracique",
        "Intergroupe Francophone du Myelome",
        "Jaeb Center for Health Research",
        "Jules Bordet Institute",
        "Karolinska Institutet",
        "Kirby Institute",
        "Lymphoma Study Association",
        "Population Health Research Institute",
        "Swiss Cancer Institute",
        "The George Institute",
        "The Netherlands Cancer Institute",
        "Union de Gestion des Etablissements des Caisses d'Assurance Maladie - Nord Est",
        "French Cardiology Society",
        "European Society for Blood and Marrow Transplantation",
        "French Society for Intensive Care",
        "French Society of Digestive Endoscopy",
        "French Defence Health Service",
        "French Innovative Leukemia Organization (FILO)",
        "French Study Group on Chronic Lymphoid Leukemia",
        "The Lymphoma Academic Research Organisation",
        "GCS Ramsay Santé pour l'Enseignement et la Recherche",
        "Ramsay Générale de Santé",
        "Hôpital Marie Lannelongue",
        "French Innovative Leukemia Organisation",
        "Groupe Oncologie Radiotherapie Tete et Cou",
        "Centre d'Etudes et de Recherche pour l'Intensification du Traitement du Diabète",
        "Institut de Myologie",
        "Association Française pour la Recherche Thermale",
        "Groupe d'Étude Thérapeutique des Affections Inflammatoires du Tube Digestif",
        "Association pour la Recherche de Thérapeutiques Innovantes en Cancérologie",
        "European Society for Blood and Marrow Transplantation",
        "Fondation Ellen Poidatz",
        "Adaptations Métaboliques à l'Exercice en conditions Physiologiques et Pathologiques",
        "Fondation Jérôme-Lejeune",
        "Association de Musicothérapie Applications et Recherches Cliniques",
        "Médipole Garonne",
        "Fondation Franc.Cancerologie Digestive",
        "Groupe Francophone des Myélodysplasies",
        "Groupe Francophone des Myélodysplasies",
        "Association Clinique et Thérapeutique Infantile du Val de Marne",
        "European Institute of Oncology",
        "European Mantle Cell Lymphoma Network",
        "European Lung Cancer Working Party",
        "Fédération Française de Pneumologie",
        "Groupement de Coopération Sanitaire Ramsay Générale de Santé pour l’Enseignement et la Recherche",
        "Groupe Francais De Pneumo-Cancerologie",
        "Institut Arnault Tzanck",
        "King's College London",
        "London School of Hygiene and Tropical Medicine",
        "Médecins Sans Frontières",
        "Observatoire Regional de la Sante Provence-Alpes-Côte d'Azur",
        "Association pour la Recherche de Thérapeutiques Innovantes en Cancérologie",
        "Fondation Lenval",
        "Fondation Ildys",
        "Fondation Audavie",
        "Fondation Korian pour le Bien Vieillir",
        "Fondation Mederic Alzheimer"
    ]
    academic_lead_sponsors_normalized = [normalize(x) for x in academic_lead_sponsors]

    industrial_lead_sponsors = [
        "Air Liquide Santé International",
        "Beaver-Visitec International, Inc.",
        "Boehringer Ingelheim International GmbH",
        "Celgene International II S.a.r.l.",
        "Celgene International II SARL",
        "Chugai Pharmaceutical",
        "CIS bio international, member of IBA group",
        "Cosmetique Active International",
        "Debiopharm International S.A.",
        "Debiopharm International SA",
        "Dentsply International",
        "DePuy International",
        "Essilor International",
        "GCP-Service International West GmbH",
        "HUYABIO International, LLC.",
        "Incyte Biosciences International Sàrl",
        "Institut de Recherches Internationales Servier",
        "Janssen Cilag International NV",
        "Janssen Cilag international NV",
        "Janssen-Cilag International N.V.",
        "Janssen-Cilag International NV",
        "Janssen-Cilag International, N.V.Turnhoutseweg 30, 2340 Beerse, Belgium",
        "LABORATOIRE INNOTECH INTERNATIONAL",
        "Lesaffre International",
        "Mayne Pharma International Pty Ltd",
        "Medacta International SA",
        "Medicrea International",
        "MENARINI INTERNATIONAL OPERATIONS LUXEMBOURG SA",
        "Mondelēz International, Inc.",
        "Servier International / Les Laboratoires Servier",
        "Vifor (International) Inc.",
        "Vitaflo International, Ltd",
        "Zogenix International Limited, Inc., a subsidiary of Zogenix, Inc.",
        "Church & Dwight Company, Inc."
    ]
    industrial_lead_sponsors_normalized = [normalize(x) for x in industrial_lead_sponsors]
    
    for word in academic_lead_sponsors_normalized:
        if word in x_normalized and x_normalized not in industrial_lead_sponsors_normalized:
            return "academique"
    return "industriel"


def enrich(all_ct):
    res = []
    dois_to_get = []
    sirano_dict = get_sirano()
    chu_df = pd.read_csv("/src/bsoclinicaltrials/server/main/chu.csv")
    chu = list(chu_df["ror"])
    clcc_df = pd.read_csv("/src/bsoclinicaltrials/server/main/clcc.csv")
    clcc = list(clcc_df["ror"])
    sponsors_df = pd.read_csv(
        "/src/bsoclinicaltrials/server/main/bso-lead-sponsors-mapping.csv"
    )
    sponsors_dict = {}
    for _, row in sponsors_df.iterrows():
        sponsors_dict[normalize(row.get("sponsor"))] = {
            "sponsor_normalized": row.get("sponsor_normalized"),
            "ror": row.get("ror"),
        }
    for ct in all_ct:
        enriched = enrich_ct(ct, sirano_dict)
        for date in enriched.get("results_details", {}):
            for reference in enriched["results_details"][date].get("references", []):
                if reference.get("doi") and reference.get("type") in [
                    "result",
                    "derived",
                ]:
                    dois_to_get.append(reference["doi"])
        res.append(enriched)
    dois_info_dict = {}
    for c in chunks(list(set(dois_to_get)), 1000):
        dois_info = get_dois_info(
            [{"doi": doi, "id": f"doi{doi}", "all_ids": [f"doi{doi}"]} for doi in c]
        )
        for info in dois_info:
            doi = info["doi"]
            dois_info_dict[doi] = info
    for p in res:
        p["observation_dates"] = list(p.get("results_details", {}).keys())
        for date in p.get("results_details", {}):
            has_publication_oa = None
            p["results_details"][date]["has_results_or_publications_within_1y"] = False
            p["results_details"][date]["has_results_or_publications_within_3y"] = False
            publication_access = []
            publications_date = []
            for reference in p["results_details"][date].get("references", []):
                doi = reference.get("doi")
                if doi:
                    if doi in dois_info_dict:
                        for field in [
                            "observation_dates",
                            "published_date",
                            "publisher_dissemination",
                            "year",
                        ]:
                            if field in dois_info_dict[doi]:
                                reference[field] = dois_info_dict[doi][field]
                    if reference.get("type") in ["derived", "result"]:
                        if isinstance(reference.get("published_date"), str):
                            publications_date.append(reference.get("published_date"))
                        if has_publication_oa is None:
                            has_publication_oa = False
                        oa_details = dois_info_dict.get(doi, {}).get("oa_details", {})
                        if len(oa_details) == 0:
                            continue
                        last_obs_date = max(reference.get("observation_dates", []))
                        for obs_date in oa_details:
                            if obs_date == last_obs_date:
                                oa_detail = oa_details[obs_date]
                                reference["oa_details_latest"] = oa_detail
                                is_oa = oa_detail.get("is_oa", False)
                                publication_access.append(is_oa)
                                has_publication_oa = (
                                    has_publication_oa or is_oa
                                )  # at least one publi is oa
            if publications_date:
                p["results_details"][date]["first_publication_date"] = min(
                    publications_date
                )
            if isinstance(
                p["results_details"][date].get("results_first_submit_date"), str
            ) and isinstance(
                p["results_details"][date].get("first_publication_date"), str
            ):
                p["results_details"][date]["first_results_or_publication_date"] = min(
                    p["results_details"][date]["results_first_submit_date"],
                    p["results_details"][date]["first_publication_date"],
                )
            elif isinstance(
                p["results_details"][date].get("results_first_submit_date"), str
            ):
                p["results_details"][date]["first_results_or_publication_date"] = p[
                    "results_details"
                ][date]["results_first_submit_date"]
            elif isinstance(
                p["results_details"][date].get("first_publication_date"), str
            ):
                p["results_details"][date]["first_results_or_publication_date"] = p[
                    "results_details"
                ][date]["first_publication_date"]
            if isinstance(p.get("study_completion_date"), str):
                if isinstance(
                    p["results_details"][date].get("results_first_submit_date"), str
                ):
                    p["results_details"][date]["delay_first_results"] = (
                        pd.to_datetime(
                            p["results_details"][date]["results_first_submit_date"]
                        )
                        - pd.to_datetime(p["study_completion_date"])
                    ).days
                    p["results_details"][date]["has_results_within_1y"] = (
                        p["results_details"][date]["delay_first_results"] <= 365
                    )
                    p["results_details"][date]["has_results_within_3y"] = (
                        p["results_details"][date]["delay_first_results"] <= 365 * 3
                    )
                if isinstance(
                    p["results_details"][date].get("first_publication_date"), str
                ):
                    p["results_details"][date]["delay_first_publication"] = (
                        pd.to_datetime(
                            p["results_details"][date]["first_publication_date"]
                        )
                        - pd.to_datetime(p["study_completion_date"])
                    ).days
                    # TODO Restore it later
                    # p["results_details"][date]["has_publication_within_1y"] = p["results_details"][date]["has_publications_result"] and (p["results_details"][date]["delay_first_publication"] <= 365)
                    p["results_details"][date]["has_publication_within_1y"] = (
                        p["results_details"][date]["delay_first_publication"] <= 365
                    )
                    # TODO Restore it later
                    # p["results_details"][date]["has_publication_within_3y"] = p["results_details"][date]["has_publications_result"] and (
                    #     p["results_details"][date]["delay_first_publication"] <= 365 * 3
                    # )
                    p["results_details"][date]["has_publication_within_3y"] = (
                        p["results_details"][date]["delay_first_publication"] <= 365 * 3
                    )
                if isinstance(
                    p["results_details"][date].get("first_results_or_publication_date"),
                    str,
                ):
                    p["results_details"][date]["delay_first_results_completion"] = (
                        pd.to_datetime(
                            p["results_details"][date][
                                "first_results_or_publication_date"
                            ]
                        )
                        - pd.to_datetime(p["study_completion_date"])
                    ).days
                    # TODO Restore it later
                    # p["results_details"][date][
                    #     "has_results_or_publications_within_1y"
                    # ] = p["results_details"][date]["has_results_or_publications"] and (
                    #     p["results_details"][date]["delay_first_results_completion"]
                    #     <= 365
                    # )
                    p["results_details"][date][
                        "has_results_or_publications_within_1y"
                    ] = (
                        p["results_details"][date]["delay_first_results_completion"]
                        <= 365
                    )
                    # TODO Restore it later
                    # p["results_details"][date][
                    #     "has_results_or_publications_within_3y"
                    # ] = p["results_details"][date]["has_results_or_publications"] and (
                    #     p["results_details"][date]["delay_first_results_completion"]
                    #     <= 365 * 3
                    # )
                    p["results_details"][date][
                        "has_results_or_publications_within_3y"
                    ] = (
                        p["results_details"][date]["delay_first_results_completion"]
                        <= 365 * 3
                    )
            p["results_details"][date]["has_publication_oa"] = has_publication_oa
            p["results_details"][date]["publication_access"] = publication_access
        lead_sponsor = p.get("lead_sponsor")
        if lead_sponsor and isinstance(lead_sponsor, str):
            lead_sponsor_normalized = sponsors_dict.get(normalize(lead_sponsor))
            if lead_sponsor_normalized:
                p["lead_sponsor_normalized"] = lead_sponsor_normalized.get(
                    "sponsor_normalized"
                )
                ror = lead_sponsor_normalized.get("ror")
                p["ror"] = ror
                p["bso_local_affiliations"] = [str(ror).replace("https://ror.org/", "")]
                if ror in chu:
                    p["bso_local_affiliations"].append("CHU")
                if ror in clcc:
                    p["bso_local_affiliations"].append("CLCC")
            else:
                p["lead_sponsor_normalized"] = lead_sponsor
            p["lead_sponsor_type"] = tag_sponsor(p["lead_sponsor_normalized"])
    return res


def enrich_ct(ct, sirano_dict):
    ct["study_start_year"] = None
    if isinstance(ct.get("study_start_date"), str):
        ct["study_start_year"] = int(ct["study_start_date"][0:4])
    ct["study_completion_year"] = None
    if isinstance(ct.get("study_completion_date"), str):
        ct["study_completion_year"] = int(ct["study_completion_date"][0:4])
    if isinstance(ct.get("study_start_date"), str) and isinstance(
        ct.get("study_first_submit_date"), str
    ):
        delay_submission_start = (
            pd.to_datetime(ct["study_first_submit_date"])
            - pd.to_datetime(ct["study_start_date"])
        ).days
        ct["delay_submission_start"] = delay_submission_start
    if (
        isinstance(ct.get("study_start_date"), str)
        and isinstance(ct.get("study_first_submit_date"), str)
        and ct["study_start_date"] > ct["study_first_submit_date"]
    ):
        ct["submission_temporality"] = "before_start"
    elif (
        isinstance(ct.get("study_first_submit_date"), str)
        and isinstance(ct.get("study_completion_date"), str)
        and ct["study_completion_date"] >= ct["study_first_submit_date"]
    ):
        ct["submission_temporality"] = "during_study"
    elif (
        isinstance(ct.get("study_first_submit_date"), str)
        and isinstance(ct.get("study_completion_date"), str)
        and ct["study_completion_date"] < ct["study_first_submit_date"]
    ):
        ct["submission_temporality"] = "after_completion"
    else:
        ct["submission_temporality"] = None
    if isinstance(ct.get("study_completion_date"), str) and isinstance(
        ct.get("study_start_date"), str
    ):
        delay_start_completion = (
            pd.to_datetime(ct["study_completion_date"])
            - pd.to_datetime(ct["study_start_date"])
        ).days
        ct["delay_start_completion"] = delay_start_completion
    french_location_only = None
    location_country = ct.get("location_country", [])
    if isinstance(location_country, list):
        location_country_lower = list(set([loc.lower() for loc in location_country]))
        if "france" in location_country_lower:
            location_country_lower.remove("france")
        if len(location_country_lower) > 0:
            french_location_only = False
        else:
            french_location_only = True
    ct["french_location_only"] = french_location_only
    for date in ct.get("results_details", {}):
        ct["results_details"][date]["publications_result"] = []
        for reference in ct["results_details"][date].get("references", []):
            # Exclude publications whose type is not "result" or "derived", by example "background"
            # Exclude publications that have the word "protocol" in their title
            if (
                reference.get("type", "").lower() in ["result", "derived"]
                # TODO Restore it later
                # and "protocol" not in reference["citation"].lower()
            ):
                if "doi" in reference:
                    ct["results_details"][date]["publications_result"].append(
                        reference["doi"]
                    )
                elif "pmid" in reference:
                    ct["results_details"][date]["publications_result"].append(
                        reference["pmid"]
                    )
                elif "citation" in reference:
                    ct["results_details"][date]["publications_result"].append(
                        reference["citation"]
                    )
                else:
                    ct["results_details"][date]["publications_result"].append("other")
        ct["results_details"][date]["has_publications_result"] = (
            len(ct["results_details"][date]["publications_result"]) > 0
        )
        ct["results_details"][date]["has_results_or_publications"] = (
            ct["results_details"][date].get("has_results", False)
            or ct["results_details"][date]["has_publications_result"]
        )
    current_status = ct.get("status")
    status_simplified = "Unknown"
    if current_status in ["Completed"]:
        status_simplified = "Completed"
    elif current_status in [
        "Ongoing",
        "Recruiting",
        "Active, not recruiting",
        "Not yet recruiting",
    ]:
        status_simplified = "Ongoing"
    ct["status_simplified"] = status_simplified
    ct["bso_country"] = ["fr"]
    if isinstance(ct.get("NCTId"), str) and ct["NCTId"] in sirano_dict:
        ct.update(sirano_dict[ct["NCTId"]])
    return ct
