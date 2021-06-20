import logging

import pymongo
from django.conf import settings
from pymongo import MongoClient

log = logging.getLogger('database')


class Database:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

    def __init__(self):
        self.entries = None
        self.db = None

        db_uri = settings.MODLOG_MONGODB_URI
        if not db_uri:
            raise RuntimeError('Database URI is not set')

        # Initialize database connection
        log.info('Connecting to the database...')
        client = MongoClient(db_uri)
        self.db = client.get_database()
        self.entries = self.db.get_collection('entries')

        log.info('Connected to the database, name: %s', self.db.name)
        # col_count = self.entries.count()
        # log.info('DB entry count: %d', col_count)

        # Create indexes for data retrieval and to avoid dupes.
        self.entries.create_index('id', unique=True)
        self.entries.create_index([('created_utc', pymongo.DESCENDING)])

    def get_entry(self, entry_id):
        """
        Fetch a single entry from the database.
        :param entry_id: The `id` value from the entry.
        :return: The entry if found. `None` if not found or if the database is not ready.
        """
        if not self.db:
            return None

        entry = self.entries.find_one({'id': entry_id}, projection={'_id': 0})
        return entry

    def set_entry_note(self, entry_id, note):
        if not self.get_entry(entry_id):
            return False

        return self.entries.update_one({'id': entry_id}, {'$set': {'notes': note}})

    def set_entry_hidden(self, entry_id, is_hidden, reason):
        if not self.get_entry(entry_id):
            return False

        return self.entries.update_one({'id': entry_id}, {'$set': {'hidden': is_hidden, 'hidden_reason': reason}})

    def insert_entries(self, entries):
        """
        Bulk insert of entries to the database. Filters out entries already on the database.
        :param entries: A `list` of entries fetched from the reddit API.
        :return: The result of the `insert_many` operation. If the database is not ready, or if no missing
        entries were found, then nothing is done and an empty `list` is returned.
        """
        if not self.db:
            return []

        # Fetch a list of IDs of entries that are already in the database.
        id_list = [e['id'] for e in entries]
        already_in = self.entries.find({'id': {'$in': id_list}}).distinct('id')

        # Create a list of entries that are not in the database, from the list above.
        missing_entries = [e for e in entries if e['id'] not in already_in]

        if len(missing_entries) > 0:
            # If there are missing entries, insert them to the database.
            return self.entries.insert_many(missing_entries, ordered=False)
        else:
            return []
