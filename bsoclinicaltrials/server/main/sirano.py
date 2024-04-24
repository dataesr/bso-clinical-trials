import pandas as pd
from bsoclinicaltrials.server.main.logger import get_logger

logger = get_logger(__name__)

url = "https://www.data.gouv.fr/fr/datasets/r/c5d8ca9b-39cb-45eb-817a-e5d41154d732"

def get_sirano():
    df = pd.read_csv(url, sep=';', encoding='iso-8859-1')
    sirano_dict = {}
    for ix, row in df.iterrows():
        if isinstance(row.numero_registre_essais, str):
            nct = row.numero_registre_essais
            if nct not in sirano_dict:
                sirano_dict[nct] = {'financement_total': 0.0, 'financements':[]}
            sirano_dict[nct]['financements'].append(row.to_dict())
            if isinstance(row.financement_total, float) or isinstance(row.financement_total, int):
                sirano_dict[nct]['financement_total'] += row.financement_total
    logger.debug(f'{len(sirano_dict)} essais dans SIRANo')
    return sirano_dict
