import json
import logging

import requests
from system import settings
from system.constants import IMPORTANT_ACTIONS

webhook = settings.DISCORD_MODLOG_WEBHOOK
log = logging.getLogger('discord_ws')


def send(entry):
    if not webhook:
        return
    
    if entry['action'] not in IMPORTANT_ACTIONS:
        return
    
    try:
        entry_copy = {k: v for k, v in entry.items() if k != '_id'}
        embed = {
            'title': 'Detalles de la acción',
            'fields': [
                {'name': 'Mod', 'value': entry['mod'], 'inline': True},
                {'name': 'Evento', 'value': entry['action'], 'inline': True},
            ],
            'footer': {'text': f'Fecha: {entry["created_utc"]}'}
        }

        if entry['target_author']:
            embed['fields'].append({'name': 'Usuario', 'value': entry['target_author'], 'inline': True})
        if entry['target_permalink']:
            embed['description']: f'**Link**: https://{entry["target_permalink"]}'
            
        if entry['target_body']:
            body_field = {
                'name': 'Contenido del post',
                'value': entry['target_body'][:1000]
            }
            if len(entry['target_body']) > 1000:
                body_field['value'] += '…'
            embed['fields'].append(body_field)

        payload = {
            'content': '**Nueva acción de moderación**',
            'embeds': [embed]
        }

        #log.error('Entry: %s', json.dumps(entry_copy))
        log.error('Enviando mensaje webhook: %s', json.dumps(payload))
        resp = requests.post(webhook, json=payload)

        if resp.status_code != 200:
            log.error('Error enviando mensaje, estado %i: %s', resp.status_code, resp.text)
    except Exception as e:
        log.exception(e)
