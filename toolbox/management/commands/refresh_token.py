import random
import socket

import praw

from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Spin off a web server to retrieve a refresh token from reddit'
    
    def add_arguments(self, parser):
        parser.add_argument('--port', '-p', type=int, default=8881)
        parser.add_argument('--host', '-H', default='127.0.0.1')
        parser.add_argument('--all-scopes', '-a', action='store_true')
        parser.add_argument('--scopes', '-s', default='modlog,modmail')

    def send_message(self, client, message):
        """Send message to client and close the connection."""
        self.stdout.write(message)
        client.send(f'HTTP/1.1 200 OK\r\n\r\n{message}'.encode("utf-8"))
        client.close()

    def serve(self, host, port):
        """Wait for and then return a connected socket..

        Opens a TCP connection and waits for a single client.
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        self.stdout.write(f'Listening on {host}:{port}')
        server.listen(1)
        client = server.accept()[0]
        server.close()
        return client
    
    def handle(self, *args, **options):
        """Provide the program's entry point when directly executed."""

        redirect_uri = ''
        host, port = options['host'], options['port']
        if port == 80:
            redirect_uri = f'http://{host}'
        else:
            redirect_uri = f'http://{host}:{port}'

        self.stdout.writelines([
            "* Go here while logged into the account you want to create a "
            "token for: https://www.reddit.com/prefs/apps/",
            "* Click the create an app button. Put something in the name "
            "field and select the script radio button.",
            f"* Put {redirect_uri} in the redirect uri field and "
            "click create app."
        ])

        try:
            client_id = settings.REDDIT_REFRESH_APP_ID or input(
                "-> Enter the client ID, it's the line just under "
                "Personal use script at the top: "
            )
            client_secret = settings.REDDIT_REFRESH_APP_SECRET or input(
                "-> Enter the client secret, it's the line next " "to secret: "
            )
            comma_scopes = 'all' if options['all_scopes'] else options['scopes']
        except KeyboardInterrupt:
            self.stdout.write('\nCancelled.')
            return

        if comma_scopes.lower() == 'all':
            scopes = ['*']
        else:
            scopes = comma_scopes.strip().split(',')

        reddit = praw.Reddit(
            client_id=client_id.strip(),
            client_secret=client_secret.strip(),
            redirect_uri=redirect_uri,
            user_agent='rchilemt/1.0 +refresh_token',
        )
        state = str(random.randint(0, 65000))
        url = reddit.auth.url(scopes, state, 'permanent')
        self.stdout.write('Now open this url in your browser: ' + url)
        self.stdout.flush()

        client = self.serve(host, port)
        data = client.recv(1024).decode('utf-8')
        param_tokens = data.split(' ', 2)[1].split('?', 1)[1].split('&')
        params = {k: v for (k, v) in [token.split('=') for token in param_tokens]}

        if state != params['state']:
            self.send_message(client, f'State mismatch. Expected: {state} Received: {params["state"]}')
            return
        elif 'error' in params:
            self.send_message(client, params['error'])
            return

        refresh_token = reddit.auth.authorize(params['code'])
        self.send_message(client, f'Refresh token: {refresh_token}')
        return
