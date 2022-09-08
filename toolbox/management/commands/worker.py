import logging
import time
import os

import pymongo
from django.core.management import BaseCommand
from praw.models import ModAction

from system.api import api
from system.database import Database

log = logging.getLogger('worker')


def serialize(item: ModAction):
    d = vars(item)
    del d['_reddit']
    d['mod'] = d.pop('_mod')
    return d


def get_entries(*, limit=100, **kwargs):
    # The result is converted to list for easier JSON serialization.
    result = list(map(serialize, api.mod.log(
        limit=limit, params=kwargs
    )))

    return result


class Command(BaseCommand):
    help = 'Runs the worker'

    def __init__(self):
        super().__init__()
        self.db = None
    
    def add_arguments(self, parser):
        parser.add_argument('--once', '-o', dest='once', action='store_true', default=False)

    def handle(self, *args, **options):
        self.db = Database.get_instance()
        daemon = not options['once'] and os.getenv('MTB_WORKER_DAEMON', '1') == '1'

        try:
            while 1:
                self.worker()
                if not daemon:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            log.info('Keyboard interrupt received!')

        log.info('Goodbye!')

    def worker(self):
        last = self.db.entries.find_one(sort=[("created_utc", pymongo.DESCENDING)])

        last_api = get_entries(limit=1)
        last_api = None if not last_api else last_api[0]

        if not last_api:
            log.info('No entries available, or the API is unavailable.')
            return

        last_id = None if not last else last['id']
        if last_id == last_api['id']:
            log.info('Database is up-to-date.')
            return

        log.info('Needs update, last entry on DB is different than the last one from the API')
        log.info('Latest API entry: {} {}'.format(last_api['id'], last_api['created_utc']))

        if last:
            log.info('Latest entry in database: {} {}'.format(last['id'], last['created_utc']))
            total_entries = self.partial_sync(last_id)
        else:
            log.info('Entries collection is empty, running full sync.')
            total_entries = self.full_sync()

        log.info('Sync finished. Entries added: {}'.format(total_entries))

    def partial_sync(self, last_id):
        api_entries = [0]
        total_entries = 0
        while len(api_entries) > 0:
            log.info('Fetching entries after ID {}'.format(last_id))
            api_entries = get_entries(limit=100, before=last_id)
            if not len(api_entries):
                log.info('No more entries found.')
                break

            total_entries += len(api_entries)
            last_id = api_entries[0]['id']
            log.info('Current batch ID: {}, inserting {} entries (suming up {}).'.format(
                last_id, len(api_entries), total_entries))
            self.db.insert_entries(api_entries)
        return total_entries

    def full_sync(self):
        last_id = None
        api_entries = [0]
        total_entries = 0
        while len(api_entries) > 0:
            log.info('Fetching entries after ID {}'.format(last_id))
            api_entries = get_entries(limit=5000, after=last_id)
            if not len(api_entries):
                log.info('No more entries found.')
                break

            last_id = api_entries[-1]['id']
            total_entries += len(api_entries)
            log.info('Current batch ID: {}, inserting {} entries (suming up {}).'.format(
                last_id, len(api_entries), total_entries))
            self.db.insert_entries(api_entries)

        return total_entries
