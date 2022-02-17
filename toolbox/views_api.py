from django.http import JsonResponse
from pymongo import DESCENDING

from system.common import filter_entry, pat_modlog_entry_id, message_response
from system.database import Database


def modlog(request):
    after_id = request.GET.get('after', '')
    if after_id and not pat_modlog_entry_id.match(after_id):
        return message_response('Invalid "after" mod action ID', status=400)

    db = Database.get_instance()
    after_entry = db.get_entry(after_id) if after_id else None

    q_filter = {'created_utc': {'$lt': after_entry['created_utc']}} if after_entry else None
    results = db.entries.find(q_filter, projection={'_id': 0}).limit(50).sort('created_utc', DESCENDING)

    results = [filter_entry(e) for e in results]
    return JsonResponse(results, safe=False)
