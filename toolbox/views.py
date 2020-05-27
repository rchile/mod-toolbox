import re
import math
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlencode

import pymongo
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from system import constants
from system.api import api, reddit, rawapi
from system.common import require_auth, sort_numeric_dict
from system.database import Database

pat_reddit_user = re.compile(r'^[a-zA-Z0-9_\-]{5,30}$')
pat_reddit_modaction = re.compile(r'^[a-z]{5,30}$')


def index(request):
    return render(request, 'login.html', context={
        'messages': messages.get_messages(request)
    })


@require_auth
def home(request):
    current_seg = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

    db = Database.get_instance()
    total_count = db.entries.find().count()
    last_hour = db.entries.find({'created_utc': {'$gte': current_seg - 3600}}).count()
    last_24h = db.entries.find({'created_utc': {'$gte': current_seg - (3600*24)}})

    mod_count = {}
    action_count = {}
    target_count = {}
    comments_count = 0
    posts_count = 0
    automod_count = 0

    for entry in last_24h:
        mod = entry['mod']
        action = entry['action']
        target = entry['target_author']

        if action not in action_count:
            action_count[action] = 0
        action_count[action] += 1

        if target and target != '[deleted]':
            if target not in target_count:
                target_count[target] = 0
            target_count[target] += 1

        if mod == 'AutoModerator':
            automod_count += 1
        else:
            if mod not in mod_count:
                mod_count[mod] = 0
            mod_count[mod] += 1

            if entry['action'] in ['removecomment', 'spamcomment']:
                comments_count += 1
            if entry['action'] in ['removelink', 'spamlink']:
                posts_count += 1

    approval_count = action_count.get('approvelink', 0) + action_count.get('approvecomment', 0)
    mod_count = sort_numeric_dict(mod_count)
    action_count = sort_numeric_dict(action_count)
    target_count = OrderedDict(list(sort_numeric_dict(target_count).items())[:10])

    return TemplateResponse(request, 'home.html', {
        'total': total_count,
        'last_hour': last_hour,
        'last_24h': last_24h.count(),
        'mod_count': mod_count,
        'action_count': action_count,
        'target_count': target_count,
        'posts_count': posts_count,
        'approval_count': approval_count,
        'ban_count': action_count.get('banuser', 0),
        'comment_count': comments_count,
        'automod_count': automod_count
    })


@require_auth
def entries(request, page=1):
    if page < 1:
        return redirect('entries')

    db = Database.get_instance()

    q_filters = {}  # query filters
    url_filters = {}  # query filters

    # Validate user filter
    filter_user = request.GET.get('user', '').strip()
    if filter_user and pat_reddit_user.match(filter_user):
        q_filters['target_author'] = filter_user
        url_filters['user'] = filter_user
    else:
        filter_user = ''

    # Validate action filter
    filter_action = request.GET.get('action', '').strip()
    if filter_action and pat_reddit_user.match(filter_action):
        q_filters['action'] = filter_action
        url_filters['action'] = filter_action
    else:
        filter_action = ''

    n_limit = 30
    list_entries = db.entries.find(q_filters, limit=n_limit, sort=[("created_utc", pymongo.DESCENDING)])
    n_entries = list_entries.count()

    max_page = math.ceil(n_entries / n_limit) or 1

    if max_page > max_page:
        return redirect(reverse('entries_paged', kwargs={'page': max_page}))

    list_entries.skip((n_limit * page) - n_limit)
    next_page = page + 1 if page < max_page else None
    prev_page = page - 1 if page > 1 else None

    url_filters = urlencode(url_filters)
    if url_filters:
        url_filters = '?' + url_filters

    return TemplateResponse(request, 'entries.html', context={
        'entries': list_entries,
        'entries_total': n_entries,
        'filter_user': filter_user,
        'filter_action': filter_action,
        'mod_actions': constants.MOD_ACTIONS,
        'prev_page': prev_page,
        'next_page': next_page,
        'url_filters': url_filters
    })


@require_auth
def user(request, username=None):
    req_username = request.GET.get('username', '') or request.POST.get('username', '')
    if req_username and pat_reddit_user.match(req_username):
        return redirect(reverse('user_detail', kwargs={'username': req_username}))

    if username is None:
        username = ''

    if username and not pat_reddit_user.match(username):
        return HttpResponseBadRequest('Invalid user name')

    list_count = 0
    list_sum = {}
    entries = []
    userdata = None

    if username:
        userdata = rawapi(f'user/{username}/about')

        db = Database.get_instance()
        list_entries = db.entries.find({'target_author': username})
        list_count = list_entries.count()

        if list_count == 0:
            messages.add_message(request, messages.ERROR, 'No entries found for that user')
            return redirect(reverse('user_form'))

        for entry in list_entries:
            if len(entries) < 20:
                entries.append(entry)
            if entry['action'] not in list_sum:
                list_sum[entry['action']] = 0
            list_sum[entry['action']] += 1

    return TemplateResponse(request, 'user.html', {
        'username': username,
        'userdata': userdata,
        'entries_count': list_count,
        'list_sum': list_sum,
        'entries': entries
    })
