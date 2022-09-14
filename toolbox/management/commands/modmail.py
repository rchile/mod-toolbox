import json
import time
import logging

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

        daemon = not options['once']

        try:
            while 1:
                self.worker()
                if not daemon:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            log.info('Keyboard interrupt received!')
    
    def partial_run(self):
        url = 'api/mod/conversations?limit=10&entity=chile'

        res = raw_oauthapi(url)
        self.stdout.write(json.dumps(res))

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
