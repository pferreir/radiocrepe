import time
import random
from urllib import unquote

from flask import Blueprint, request, json, jsonify,\
     current_app, Response, session

from radiocrepe.storage import DistributedStorage
from radiocrepe.db import User
from radiocrepe.web.util import with_hub_db
from radiocrepe.web.live import broadcast

web_queue = Blueprint('queue', __name__,
                      template_folder='templates')


playing = None
queue = []


def song(storage, uid):
    return storage.get(uid, None)


@web_queue.route('/playing/')
@with_hub_db
def _playing(db, storage, registry):
    if playing:
        storage = DistributedStorage.bind(current_app.config)
        meta = storage.get(playing[1], None)
        meta['time_add'] = playing[0]
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@web_queue.route('/enqueue/', methods=['POST'])
@with_hub_db
def enqueue(db, storage, registry):
    uid = request.form.get('uid')
    if uid in storage:
        ts = time.time()
        queue.append((ts, uid))
        broadcast('add', {
            'song': song(storage, uid),
            'user': User.get(storage.db, session['user_id']).dict()
        }, ts=ts)
        return jsonify({'id': uid})
    else:
        return Response(jsonify(result='ERR_NO_SUCH_SONG', id=uid).data,
                        mimetype='application/json', status=404)
        return jsonify(), 404


@web_queue.route('/notify/start/', methods=['POST'])
@with_hub_db
def _notify_start(db, storage, registry):
    global playing
    try:
        playing = queue.pop(0)
        broadcast('play', {
            'song': song(storage, playing[1])
            }, ts=playing[0])
        return json.dumps(len(queue))
    except IndexError:
        return Response(jsonify(result='ERR_NO_NEXT').data,
                        mimetype='application/json', status=404)


@web_queue.route('/notify/stop/', methods=['POST'])
@with_hub_db
def _notify_stop(db, storage, registry):
    global playing
    broadcast('stop', song(storage, playing[1]), ts=playing[0])
    playing = None
    return ''


@web_queue.route('/queue/')
@with_hub_db
def _queue(db, storage, registry):
    res = []
    for ts, uid in queue:
        elem = storage.get(uid, None)
        elem['uid'] = uid
        elem['time_add'] = ts
        res.append(elem)
    return json.dumps(res)


@web_queue.route('/play/<term>/', methods=['POST'])
@with_hub_db
def _search(db, storage, registry, term):
    term = unquote(term)

    res = storage.search(term)

    if res:
        ts = time.time()
        meta = random.choice(res)
        queue.append((ts, meta['uid']))
        broadcast('add', {
            'song': song(storage, meta['uid']),
            'user': User.get(storage.db, session['user_id']).dict()
        }, ts=ts)
        meta['time'] = ts
        return jsonify(meta)
    else:
        return Response(jsonify(result='ERR_NO_RESULTS').data,
                        mimetype='application/json', status=404)
