import logging
import random
import re
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from prawcore import OAuthException, InsufficientScope
from pymongo import MongoClient

from system.api import reddit_instance

logger = logging.getLogger('rchilemt')

pat_modlog_entry_id = re.compile(r'^ModAction_[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$')


def random_str(length=15):
    x = 'abcdefghihklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
    return ''.join([x[random.randint(0, len(x)-1)] for _ in range(length)])


def message_response(message=None, data=None, status=200):
    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise RuntimeError('data parameter is not a dict or None')

    return JsonResponse({'message': message, **data}, status=status)


def filter_entry(entry):
    """
    Filters data out from a hidden entry
    :param entry: The entry to remove it's public data
    :return: The filtered entry
    """

    if entry.get('hidden', None):
        clear_attrs = 'target_author,target_permalink,target_body,target_title,' \
                      'target_fullname,description,details'.split(',')
        entry = {**dict(entry), **zip(clear_attrs, [None] * len(clear_attrs))}

    return entry


def get_database():
    client = MongoClient(settings.MODLOG_MONGODB_URI)
    return client.get_database()


def require_auth(f):
    def wrapper(request, *args, **kwargs):
        auth_code = request.session.get('auth_code', '')
        if not auth_code:
            messages.add_message(request, messages.ERROR, 'Not logged or session expired.')
            return redirect('index')

        # Instantiate reddit session interface
        reddit = reddit_instance(auth_code)

        # Check session only if last check was done 5 minutes ago or more
        last_check = request.session.get('last_session_check', 0)
        now_timestamp = datetime.now().timestamp()
        if (now_timestamp - last_check) > 300:
            try:
                reddit.auth.scopes()
            except (OAuthException, InsufficientScope):
                del request.session['auth_code']
                messages.add_message(request, messages.ERROR, 'Your session expired.')
                return redirect('login')

            user = reddit.user.me()
            request.session['username'] = user.name
            subreddit = request.session.get('auth_sub', settings.REDDIT_DEFAULT_SUB)
            if subreddit not in user.moderated():
                request.session['logout_message'] = 'You are not a moderator of this subreddit!'
                return redirect('logout')

            # Update last session check timestamp
            request.session['last_session_check'] = datetime.now().timestamp()

        user = request.session.get('username', None)
        if not user:
            user = reddit.user.me()
            request.session['username'] = user.name

        view_response = f(request, *args, **kwargs)

        if isinstance(view_response, TemplateResponse):
            if not view_response.context_data:
                view_response.context_data = {}
            view_response.context_data['user'] = user
            return view_response.render()
        else:
            return view_response

    return wrapper


def sort_numeric_dict(the_dict, reverse=True):
    return {k: v for k, v in sorted(the_dict.items(), key=lambda item: item[1], reverse=reverse)}
