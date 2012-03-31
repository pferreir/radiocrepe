import time
import random
from urllib import unquote

from flask import Blueprint, request, json, jsonify,\
     current_app, Response

from radiocrepe.storage import DistributedStorage
from radiocrepe.web.util import with_storage
from radiocrepe.web.live import broadcast

web_queue = Blueprint('queue', __name__,
                      template_folder='templates')


playing = None
queue = []


@web_queue.route('/playing/')
@with_storage(DistributedStorage)
def _playing(storage):
    if playing:
        storage = DistributedStorage.bind(current_app.config)
        meta = storage.get(playing[1], None)
        meta['time_add'] = playing[0]
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@web_queue.route('/enqueue/', methods=['POST'])
@with_storage(DistributedStorage)
def enqueue(storage):
    uid = request.form.get('uid')
    if uid in storage:
        ts = time.time()
        queue.append((ts, uid))
        broadcast('add', ts, uid)
        return jsonify({'id': uid})
    else:
        return Response(jsonify(result='ERR_NO_SUCH_SONG', id=uid).data,
                        mimetype='application/json', status=404)
        return jsonify(), 404


@web_queue.route('/notify/start/', methods=['POST'])
def _notify_start():
    global playing
    try:
        playing = queue.pop(0)
        broadcast('play', playing[0], playing[1])
        return json.dumps(len(queue))
    except IndexError:
        return Response(jsonify(result='ERR_NO_NEXT').data,
                        mimetype='application/json', status=404)


@web_queue.route('/notify/stop/', methods=['POST'])
def _notify_stop():
    global playing
    broadcast('stop', playing[0], playing[1])
    playing = None
    return ''


@web_queue.route('/queue/')
@with_storage(DistributedStorage)
def _queue(storage):
    res = []
    for ts, uid in queue:
        elem = storage.get(uid, None)
        elem['uid'] = uid
        elem['time_add'] = ts
        res.append(elem)
    return json.dumps(res)


@web_queue.route('/play/<term>/', methods=['POST'])
@with_storage(DistributedStorage)
def _search(term, storage):
    term = unquote(term)

    res = storage.search(term)

    if res:
        ts = time.time()
        meta = random.choice(res)
        queue.append((ts, meta['uid']))
        broadcast('add', ts, meta['uid'])
        meta['time'] = ts
        return jsonify(meta)
    else:
        return Response(jsonify(result='ERR_NO_RESULTS').data,
                        mimetype='application/json', status=404)
