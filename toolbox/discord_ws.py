import json
import logging
from datetime import datetime

import requests
from system import settings
from system.constants import MODACTION_WH, USELESS_DETAILS

webhook = settings.DISCORD_MODLOG_WEBHOOK
bots = ['AutoModerator', 'FloodgatesBot']
log = logging.getLogger('worker.dsws')


def make_embed(entry):
    ts = datetime.fromtimestamp(entry['created_utc']).isoformat().replace('T', ' ')
    mod = ('🤖 ' if entry['mod'] in bots else '') + entry['mod']

    embed = {
        'fields': [{'name': 'Mod', 'value': mod, 'inline': True}],
        'footer': {'text': f'Fecha: {ts}'}
    }

    if entry.get('target_author', ''):
        embed['fields'].append({'name': 'Usuario', 'value': entry['target_author'], 'inline': True})

    if entry.get('target_permalink', ''):
        embed['description'] = f'**Link**: https://www.reddit.com{entry["target_permalink"]}'

    if entry.get('details', ''):
        details = entry['details']
        for k, v in USELESS_DETAILS.items():
            if k == details:
                details = v
        if details:
            embed['fields'].append({'name': 'Detalles', 'value': entry['details'], 'inline': True})

    if entry.get('target_title', ''):
        embed['fields'].append({
            'name': 'Título del post',
            'value': entry['target_title']
        })

    if entry.get('target_body', ''):
        content_type = 'post' if entry.get('target_title', '') else 'comentario' 
        body_field = {
            'name': f'Contenido del {content_type}',
            'value': entry['target_body'][:1000]
        }
        if len(entry['target_body']) > 1000:
            body_field['value'] += '…'
        embed['fields'].append(body_field)

    return embed


def send(entries):
    if not webhook:
        return
    
    for entry in entries[:5]:
        if entry['action'] not in MODACTION_WH:
            return
        
        try:
            action_description = MODACTION_WH[entry['action']]
            payload = {
                'content': f'📝 **{action_description}** por **{entry["mod"]}**',
                'embeds': [make_embed(entry)]
            }

            log.debug('Entry: %s', entry)
            log.debug('Enviando mensaje webhook: %s', json.dumps(payload))
            resp = requests.post(webhook, json=payload)

            if resp.status_code >= 400:
                log.error('Error enviando mensaje, estado %i: %s', resp.status_code, resp.text)
        except Exception as e:
            log.exception(e)
