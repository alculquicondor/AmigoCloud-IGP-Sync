from datetime import timedelta
from hashlib import md5
import json

from amigocloud import AmigoCloud
from celery import Celery

from utils import get_earthquakes_data, to_amigo_format
from settings import TOKEN, PROJECT_URL, DATASET_ID, BROKER_URL

app = Celery()

app.conf.CELERYBEAT_SCHEDULE = {
    'sync-every-5-min': {
        'task': 'tasks.amigocloud_sync_earthquakes',
        'schedule': timedelta(minutes=5)
    },
}
app.conf.BROKER_URL = BROKER_URL
app.conf.CELERY_TIMEZONE = 'UTC'


@app.task(name='tasks.amigocloud_sync_earthquakes')
def amigocloud_sync_earthquakes(page=1):
    change_data = []
    for earthquake in get_earthquakes_data(page):
        amigo_data = to_amigo_format(earthquake)
        amigo_id = md5(str(amigo_data).encode()).hexdigest()
        change_data.append({
            'amigo_id': amigo_id,
            'new': amigo_data
        })
    change = {
        'type': 'DML',
        'entity': 'dataset_%s' % DATASET_ID,
        'action': 'INSERT',
        'data': change_data
    }

    amigocloud = AmigoCloud(TOKEN, PROJECT_URL)
    amigocloud.post('datasets/%s/submit_change' % DATASET_ID,
                    {'change': json.dumps(change)})
