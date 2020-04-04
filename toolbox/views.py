import re
import math
from urllib.parse import urlencode

import pymongo
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from system import constants
from system.common import require_auth
from system.database import Database

pat_reddit_user = re.compile(r'^[a-zA-Z0-9_\-]{5,30}$')
pat_reddit_modaction = re.compile(r'^[a-z]{5,30}$')


def index(request):
    return render(request, 'index_.html', context={
        'messages': messages.get_messages(request)
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
def home(request):
    return TemplateResponse(request, 'home.html')


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

    if username:
        db = Database.get_instance()
        list_entries = db.entries.find({'target_author': username})
        list_count = list_entries.count()

        if list_count == 0:
            messages.add_message(request, messages.ERROR, 'No entries found for that user')
            return redirect(reverse('user_form'))

        for entry in list_entries:
            if entry['action'] not in list_sum:
                list_sum[entry['action']] = 0
            list_sum[entry['action']] += 1

    return TemplateResponse(request, 'user.html', {
        'username': username,
        'entries_count': list_count,
        'list_sum': list_sum
    })
