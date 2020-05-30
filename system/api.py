import logging
from json import JSONDecodeError

import praw
import requests
from django.conf import settings
from prawcore.const import ACCESS_TOKEN_PATH

logger = logging.getLogger('rchilemt')


def reddit_instance(refresh=None):
    params = {
        'client_id': settings.REDDIT_APP_ID,
        'client_secret': settings.REDDIT_APP_SECRET,
        'user_agent': settings.REDDIT_APP_UA,
        'check_for_updates': False
    }

    if refresh:
        params['refresh_token'] = refresh
        return praw.Reddit(**params)
    else:
        params['redirect_uri'] = settings.REDDIT_APP_REDIRECT
        return praw.Reddit(**params)


def rawapi(url, append_json=True, auth=False, oauth=False):
    url = 'https://{}reddit.com/{}'.format(('oauth.' if oauth else ''), url.lstrip('/'))
    if append_json and not url.endswith('.json'):
        url += '.json'

    headers = {'User-Agent': settings.REDDIT_APP_UA, 'Accept': 'application/json'}
    httpauth = None
    if auth:
        headers['Authorization'] = 'Bearer ' + (settings.REDDIT_APP_REFRESH if isinstance(auth, bool) else auth)
        if not oauth:
            httpauth = (settings.REDDIT_APP_ID, settings.REDDIT_APP_SECRET)

    headers_log = headers.copy()
    if 'Authorization' in headers_log:
        headers_log['Authorization'] = 'Bearer ***'

    logger.debug('Requesting url %s headers %s', url, headers_log)
    data = requests.get(url, headers=headers, auth=httpauth)
    try:
        data = data.json()
    except JSONDecodeError:
        logger.error('Invalid JSON retrieved')
        logger.error(data)
        raise RuntimeError('Invalid JSON retrieved')

    return data


def raw_oauthapi(url, token=None):
    headers = {'User-Agent': settings.REDDIT_APP_UA}
    auth = (settings.REDDIT_APP_ID, settings.REDDIT_APP_SECRET)
    auth_data = {'grant_type': 'refresh_token', 'refresh_token': token or settings.REDDIT_APP_REFRESH}

    logger.debug('Manually fetching access_token with refresh token...')
    response = requests.post('https://www.reddit.com' + ACCESS_TOKEN_PATH, headers=headers, data=auth_data, auth=auth)

    auth_response = response.json()
    if response.status_code != 200:
        logger.debug('Could not authenticate to OAuth API: %s', auth_response)
        raise RuntimeError('Could not authenticate to OAuth API')

    logger.debug('Token retrieved!')
    return rawapi(url, append_json=False, auth=auth_response['access_token'], oauth=True)


reddit = reddit_instance(settings.REDDIT_APP_REFRESH)
api = reddit.subreddit(settings.REDDIT_DEFAULT_SUB)
