from __future__ import absolute_import, unicode_literals

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WP1_4.settings')
os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
from django.conf import settings


app = Celery("WP1_4")

app.config_from_object('django.conf:settings', namespace="CELERY")
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.autodiscover_tasks(['monorepo', 'EnergyCapture'])

app.conf.beat_schedule = {
    # 'add-data-every-second': {
    #     'task': 'EnergyCapture.tasks.add_power_clamp_time_task',
    #     'schedule': 100.00,
    # },
    'poll-postgre-data': {
        'task': 'monorepo.tasks.poll_postgre_data',
        'schedule': 6.00,
    },
}


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))