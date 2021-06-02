import os

from elasticsearch import Elasticsearch, helpers

from bso.server.main.logger import get_logger

logger = get_logger(__name__)

es = None
try:
    es = Elasticsearch(os.getenv('ES_URL'), http_auth=(os.getenv('ES_LOGIN'), os.getenv('ES_PASSWORD')))
except:
    logger.debug('Cannot connect to es')


def delete_index(index: str):
    logger.debug(f'Deleting {index}')
    response = es.indices.delete(index=index, ignore=[400, 404])
    logger.debug(response)


def reset_index(index):
    try:
        delete_index(index)
    except:
        logger.debug('Index deletion failed')
    response = es.indices.create(
        index=index,
        body={'settings': {}, 'mappings': {}},
        ignore=400  # ignore 400 already exists code
    )
    if 'acknowledged' in response:
        if response['acknowledged']:
            response = str(response['index'])
            logger.debug(f'Index mapping success for index: {response}')


def load_in_es(data, index):
    actions = [
        {
            '_index': index,
            '_id': i,
            '_source': data
        }
        for i, data in enumerate(data)
    ]
    helpers.parallel_bulk(client=es, actions=actions, chunk_size=500, request_timeout=60)
    logger.debug(f'{len(data)} elements imported into {index}')
