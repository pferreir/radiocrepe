import time
import random
from urllib import unquote

from flask import Blueprint, request, json, jsonify,\
     current_app, Response, session

from radiocrepe.storage import DistributedStorage
from radiocrepe.db import User, Vote
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
        meta['added_by'] = User.get(db, playing[2]).dict()
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@web_queue.route('/enqueue/', methods=['POST'])
@with_hub_db
def enqueue(db, storage, registry):
    uid = request.form.get('uid')
    if uid in storage:
        ts = int(time.time())
        user_id = session['user_id']
        queue.append((ts, uid, user_id))
        broadcast('add', {
            'song': song(storage, uid),
            'user': User.get(db, user_id).dict(),
            'self_vote': False,
            'num_votes': 0
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
        ts, uid, user_id = playing
        broadcast('play', {
            'song': song(storage, uid),
            'user': User.get(db, user_id).dict()
            }, ts=ts)
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
    for ts, uid, user_id in queue:
        elem = storage.get(uid, None)
        elem['uid'] = uid
        elem['ts_add'] = ts
        elem['num_votes'] = db.session.query(Vote).filter_by(song_id=uid,
                                                             timestamp=ts).count()
        elem['self_vote'] = db.session.query(Vote).filter_by(song_id=uid,
                                                             timestamp=ts,
                                                             user_id=user_id).count()
        elem['added_by'] = User.get(db, user_id).dict()
        res.append(elem)
    return json.dumps(res)


@web_queue.route('/play/<term>/', methods=['POST'])
@with_hub_db
def _search(db, storage, registry, term):
    term = unquote(term)

    res = storage.search(term)

    if res:
        ts = int(time.time())
        meta = random.choice(res)
        queue.append((ts, meta['uid'], session['user_id']))
        broadcast('add', {
            'song': song(storage, meta['uid']),
            'user': User.get(storage.db, session['user_id']).dict(),
            'self_vote': False,
            'num_votes': 0
            }, ts=ts)
        meta['time'] = ts
        return jsonify(meta)
    else:
        return Response(jsonify(result='ERR_NO_RESULTS').data,
                        mimetype='application/json', status=404)


@web_queue.route('/queue/<uid>_<ts_add>/vote_up/', methods=['POST'])
@with_hub_db
def _vote_up(db, storage, registry, uid, ts_add):
    user_id = session['user_id']
    db.session.add(Vote(user_id=user_id, timestamp=int(ts_add), song_id=uid))
    db.session.commit()
    broadcast('vote_up', {
        'uid': uid,
        'ts_add': int(ts_add),
        'user_id': user_id
        })

    return ''


@web_queue.route('/queue/<uid>_<ts_add>/vote_undo/', methods=['POST'])
@with_hub_db
def _vote_undo(db, storage, registry, uid, ts_add):
    user_id = session['user_id']

    vote = db.session.query(Vote).filter_by(song_id=uid,
                                            timestamp=int(ts_add),
                                            user_id=user_id).first()
    if vote:
        db.session.delete(vote)
    db.session.commit()

    broadcast('vote_undo', {
        'uid': uid,
        'ts_add': int(ts_add),
        })

    return ''
