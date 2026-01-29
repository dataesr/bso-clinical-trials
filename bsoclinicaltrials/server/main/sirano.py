import pandas as pd

from bsoclinicaltrials.server.main.logger import get_logger

logger = get_logger(__name__)

# https://sante.gouv.fr/systeme-de-sante/innovation-et-recherche/l-innovation-et-la-recherche-clinique/appels-a-projets/programmes-recherche
url = "https://www.data.gouv.fr/api/1/datasets/r/56589f33-b66b-4b00-ae5c-fe9dcdc9a6e3" # donnees-sirano-projets-c2-2024.csv, MAJ 2024/12/05

def get_sirano():
    df = pd.read_csv(url, sep=';', encoding='iso-8859-1')
    df['financement_total'] = df['financement_total'].str.replace(",", ".").astype(float)
    sirano_dict = {}
    for _, row in df.iterrows():
        if isinstance(row.numero_registre_essais, str):
            nct = row.numero_registre_essais
            if nct not in sirano_dict:
                sirano_dict[nct] = {'financement_total': 0.0, 'financements':[]}
            sirano_dict[nct]['financements'].append(row.to_dict())
            if isinstance(row.financement_total, float) or isinstance(row.financement_total, int):
                sirano_dict[nct]['financement_total'] += row.financement_total
    logger.debug(f'{len(sirano_dict)} essais dans SIRANo')
    return sirano_dict
