import json

from django.core.management import BaseCommand

from system.api import raw_oauthapi


class Command(BaseCommand):
    help = 'Runs the modmail worker'

    def handle(self, *args, **options):
        last_id = None
        conversation_count = 0
        while 1:
            url = 'api/mod/conversations?limit=200'
            if last_id is not None:
                url += '&after=' + last_id

            x = raw_oauthapi(url)
            if len(x['conversationIds']) == 0:
                break

            conversation_count += len(x['conversationIds'])
            last_id = x['conversationIds'][-1]
            self.stdout.write(json.dumps(x['conversationIds'][-1]))

        self.stdout.write('********* Total conversation count: ' + str(conversation_count))
