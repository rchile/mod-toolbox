import praw
from django.conf import settings


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


reddit = reddit_instance(settings.REDDIT_APP_REFRESH)
api = reddit.subreddit(settings.REDDIT_DEFAULT_SUB)
