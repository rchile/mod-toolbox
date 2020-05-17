from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from prawcore import OAuthException

from system.common import random_str, logger
from system.api import reddit_instance


def login(request):
    if request.session.get('auth_code', ''):
        return redirect('home')

    reddit = reddit_instance()
    state = random_str()
    request.session['login_state'] = state
    return redirect(reddit.auth.url(['identity', 'read'], state))


def login_return(request):
    session_state = request.session.get('login_state', '')
    if not session_state:
        messages.add_message(request, messages.ERROR, 'No state previously defined. Please try again.')
        return redirect('index')

    req_state = request.GET.get('state', '')
    if not req_state:
        messages.add_message(request, messages.ERROR, 'Missing "state" parameter.')
        return redirect('index')

    auth_code = request.GET.get('code', '')
    if not auth_code:
        messages.add_message(request, messages.ERROR, 'Missing "code" parameter.')
        return redirect('index')

    if session_state != req_state:
        messages.add_message(request, messages.ERROR, 'Invalid "state" parameter value.')
        return redirect('index')

    reddit = reddit_instance()
    try:
        request.session['auth_code'] = reddit.auth.authorize(auth_code)
        request.session['auth_user'] = reddit.user.me().name
        request.session['auth_sub'] = settings.REDDIT_DEFAULT_SUB

        return redirect('home')
    except OAuthException as e:
        logger.exception(e)
        messages.add_message(request, messages.ERROR, 'Could not login to reddit, please try again.')
        return redirect('index')


def logout(request):
    logout_message = request.session.get('logout_message', '')
    if logout_message:
        messages.add_message(request, messages.INFO, logout_message)
        del request.session['logout_message']

    del request.session['auth_code']
    del request.session['auth_user']
    del request.session['auth_sub']

    return redirect('index')
