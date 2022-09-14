import json
import time
import logging

from django.conf import settings
from django.core.management import BaseCommand

from system.api import raw_oauthapi

log = logging.getLogger('worker.mm')


class Command(BaseCommand):
    help = 'Runs the modmail worker'
    
    def add_arguments(self, parser):
        parser.add_argument('--once', '-o', dest='once', action='store_true')
        parser.add_argument('--partial', '-p', action='store_true')

    def handle(self, *args, **options):
        if options['partial']:
            self.partial_run()
            return

        try:
            while 1:
                self.worker()
                if options['once']:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            log.info('Keyboard interrupt received!')
    
    def partial_run(self):
        sub = settings.REDDIT_DEFAULT_SUB
        url = f'api/mod/conversations?limit=10&sort=recent&entity={sub}'

        results = raw_oauthapi(url)
        msgs = []

        for item in results['conversations'].values():
            message = results['messages'].get(item['objIds'][0]['id'])
            if not message or not message['author']['isOp']:
                continue

            msgs.append({
                'subject': item['subject'],
                'message': message['bodyMarkdown'],
                'author': message['author'],
                'others': [i['name'] for i in item['authors'] if i['name'] != message['author']['name']],
                'date': item['lastUpdated']
            })

        self.stdout.write(json.dumps(msgs))

    def worker(self, *args, **options):
        last_id = None
        conversation_count = 0
        while 1:
            url = 'api/mod/conversations?limit=200'
            if last_id is not None:
                url += '&after=' + last_id

            res = raw_oauthapi(url)
            self.stdout.write(str(res))
            if len(res.get('conversationIds', [])) == 0:
                break

            conversation_count += len(res['conversationIds'])
            last_id = res['conversationIds'][-1]
            self.stdout.write(json.dumps(res['conversationIds'][-1]))

        self.stdout.write('********* Total conversation count: ' + str(conversation_count))
