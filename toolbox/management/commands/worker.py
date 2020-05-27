import time

import pymongo
from django.core.management import BaseCommand
from praw.models import ModAction

from system.api import api
from system.database import Database


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

    def handle(self, *args, **options):
        self.stdout.write('Connecting to the database...')
        self.db = Database.get_instance()
        self.stdout.write('Connected.')
        self.stdout.write('Starting the worker loop...')

        try:
            while True:
                self.worker()
                time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write('Keyboard interrupt received!')

        self.stdout.write('Goodbye!')

    def worker(self):
        last = self.db.entries.find_one(sort=[("created_utc", pymongo.DESCENDING)])

        last_api = get_entries(limit=1)
        last_api = None if not last_api else last_api[0]

        if not last_api:
            self.stdout.write('No entries available, or the API is unavailable.')
            return

        last_id = None if not last else last['id']
        if last_id == last_api['id']:
            self.stdout.write('Database is up-to-date.')
            return

        self.stdout.write('Needs update, last entry on DB is different than the last one from the API')
        self.stdout.write('Latest API entry: {} {}'.format(last_api['id'], last_api['created_utc']))

        if last:
            self.stdout.write('Latest entry in database: {} {}'.format(last['id'], last['created_utc']))
            total_entries = self.partial_sync(last_id)
        else:
            self.stdout.write('Entries collection is empty, running full sync.')
            total_entries = self.full_sync()

        self.stdout.write('Sync finished. Entries added: {}'.format(total_entries))

    def partial_sync(self, last_id):
        api_entries = [0]
        total_entries = 0
        while len(api_entries) > 0:
            self.stdout.write('Fetching entries after ID {}'.format(last_id))
            api_entries = get_entries(limit=100, before=last_id)
            if not len(api_entries):
                self.stdout.write('No more entries found.')
                break

            total_entries += len(api_entries)
            last_id = api_entries[0]['id']
            self.stdout.write('Current batch ID: {}, inserting {} entries (suming up {}).'.format(
                last_id, len(api_entries), total_entries))
            self.db.insert_entries(api_entries)
        return total_entries

    def full_sync(self):
        last_id = None
        api_entries = [0]
        total_entries = 0
        while len(api_entries) > 0:
            self.stdout.write('Fetching entries after ID {}'.format(last_id))
            api_entries = get_entries(limit=5000, after=last_id)
            if not len(api_entries):
                self.stdout.write('No more entries found.')
                break

            last_id = api_entries[-1]['id']
            total_entries += len(api_entries)
            self.stdout.write('Current batch ID: {}, inserting {} entries (suming up {}).'.format(
                last_id, len(api_entries), total_entries))
            self.db.insert_entries(api_entries)

        return total_entries
