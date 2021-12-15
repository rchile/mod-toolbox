import json
import re
import math
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlencode

import arrow
import pymongo
from django.contrib import messages
from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from system import constants
from system.api import rawapi, raw_oauthapi
from system.common import require_auth, sort_numeric_dict, pat_reddit_id
from system.constants import IMPORTANT_ACTIONS, MOD_ACTIONS
from system.database import Database

pat_reddit_user = re.compile(r'^[a-zA-Z0-9_\-]{5,30}|Anti-Evil Operations$')
pat_reddit_modaction = re.compile(r'^[a-z]{5,30}$')


@require_auth
def home(request):
    current_seg = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

    db = Database.get_instance()
    total_count = db.entries.count_documents({})
    last_hour = db.entries.count_documents({'created_utc': {'$gte': current_seg - 3600}})
    last_24h = list(db.entries.find({'created_utc': {'$gte': current_seg - (3600*24)}}))
    last_bans = list(db.entries.find({'action': 'banuser'}).limit(30).sort('created_utc', pymongo.DESCENDING))
    last_removed = list(db.entries.find(
        {'action': {'$in': ['removecomment', 'spamcomment', 'removelink', 'spamlink']}})
        .limit(15).sort('created_utc', pymongo.DESCENDING))

    mod_count = {}
    action_count = {}
    target_count = {}
    comments_count = 0
    posts_count = 0
    automod_count = 0
    ban_perm_count = 0

    for entry in last_24h:
        mod = entry['mod']
        action = entry['action']
        target = entry['target_author']

        if action not in action_count:
            action_count[action] = 0
        action_count[action] += 1

        if action in IMPORTANT_ACTIONS and target and target != '[deleted]':
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
            if entry['action'] == 'banuser' and entry['details'] == 'permanent':
                ban_perm_count += 1

    approval_post_count = action_count.get('approvelink', 0)
    approval_comments_count = action_count.get('approvecomment', 0)
    approval_count = approval_post_count + approval_comments_count
    mod_count = sort_numeric_dict(mod_count)
    action_count = sort_numeric_dict(action_count)
    target_count = OrderedDict(list(sort_numeric_dict(target_count).items())[:10])

    return TemplateResponse(request, 'home.html', {
        'total': total_count,
        'last_hour': last_hour,
        'last_24h_count': len(last_24h),
        'mod_count': mod_count,
        'action_count': action_count,
        'target_count': target_count,
        'posts_count': posts_count,
        'approval_count': approval_count,
        'ban_count': action_count.get('banuser', 0),
        'ban_perm_count': ban_perm_count,
        'comment_count': comments_count,
        'automod_count': automod_count,
        'last_bans': last_bans,
        'last_bans_count': len(last_bans),
        'last_removed': last_removed,
        'approval_comments_count': approval_comments_count,
        'approval_post_count': approval_post_count
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

    # Validate mod filter
    filter_mod = request.GET.get('mod', '').strip()
    if filter_mod and pat_reddit_user.match(filter_mod):
        q_filters['mod'] = filter_mod
        url_filters['mod'] = filter_mod
    else:
        filter_mod = ''

    # Validate action filter
    filter_action = request.GET.get('action', '').strip()
    if filter_action and pat_reddit_modaction.match(filter_action):
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
        'filter_mod': filter_mod,
        'mod_actions': constants.MOD_ACTIONS,
        'prev_page': prev_page,
        'next_page': next_page,
        'url_filters': url_filters
    })


@require_auth
def entry_details(request, entry_id):
    db = Database.get_instance()
    the_entry = db.get_entry(entry_id)
    if the_entry is None:
        raise Http404('Entry not found')

    return TemplateResponse(request, 'entry_details.html', {'entry': the_entry})


@require_auth
def user_search(request):
    req_username = request.GET.get('username', '') or request.POST.get('username', '')
    if req_username and pat_reddit_user.match(req_username):
        return redirect(reverse('user_detail', kwargs={'username': req_username}))

    return TemplateResponse(request, 'user.html')


@require_auth
def user_details(request, username):
    if not pat_reddit_user.match(username):
        return HttpResponseBadRequest('Invalid user name')

    action_filter = request.GET.get('action', '')
    if action_filter and action_filter not in MOD_ACTIONS:
        action_filter = None

    userdata = rawapi(f'user/{username}/about')['data']

    db = Database.get_instance()
    list_entries = db.entries.find({'target_author': username}).sort('created_utc', pymongo.ASCENDING)
    list_count = list_entries.count()

    if list_count == 0:
        messages.add_message(request, messages.ERROR, 'No entries found for that user')
        return redirect(reverse('user_form'))

    permaban = False
    list_sum = {}
    entries_list = []
    removed_comments = []
    removed_posts = []
    for entry in list_entries:
        if not action_filter or entry['action'] == action_filter:
            entries_list.append(entry)
        if entry['action'] not in list_sum:
            list_sum[entry['action']] = 0
        list_sum[entry['action']] += 1

        # Check if user is permanently banned
        if entry['action'] == 'banuser' and entry['details'] == 'permanent':
            permaban = True
        if entry['action'] == 'unbanuser' and entry['details'] == 'was permanent':
            permaban = True

        # Removed comments and posts list
        permalink = entry.get('target_permalink', None)
        if entry['action'] in ['removecomment', 'spamcomment'] and permalink not in removed_comments:
            removed_comments.append(permalink)
        if entry['action'] == 'approvecomment' and permalink in removed_comments:
            removed_comments.remove(permalink)
        if entry['action'] in ['removelink', 'spamlink'] and permalink not in removed_posts:
            removed_posts.append(permalink)
        if entry['action'] == 'approvelink' and permalink in removed_posts:
            removed_posts.remove(permalink)

    entries_display = entries_list[-50:][::-1]
    return TemplateResponse(request, 'user.html', {
        'username': username,
        'userdata': userdata,
        'entries': entries_display,
        'entries_count': list_count,
        'entries_list_count': len(entries_display),
        'mod_actions': constants.MOD_ACTIONS,
        'action_filter': action_filter,
        'list_sum': list_sum,
        'ban_count': list_sum.get('banuser', 0),
        'permaban': permaban,
        'removed_comments': len(removed_comments),
        'removed_posts': len(removed_posts)
    })


@require_auth
def modmail(request, convo_id=None):
    token = request.session['auth_code']
    if convo_id:
        if not pat_reddit_id.match(convo_id):
            return HttpResponseBadRequest('Invalid conversation ID')

        data = raw_oauthapi('api/mod/conversations/' + convo_id, token)
        data['conversation']['participant'] = data['user']
        conversations = [data['conversation']]
    else:
        data = raw_oauthapi('api/mod/conversations?sort=recent', token)
        conversations = data['conversations'].values()

    for convo in conversations:
        convo['messages'] = [data['messages'][x['id']] for x in convo['objIds'] if x['id'] in data['messages']]
        convo['dt'] = arrow.get(convo['lastUpdated']).timestamp()

    return TemplateResponse(request, 'modmail.html', {
        'conversations': sorted(conversations, key=lambda x: x['dt'], reverse=True),
        'convo_id': convo_id,
        'data': json.dumps(data)
    })
