import time
import random
from urllib import unquote

from flask import Blueprint, request, json, jsonify,\
     current_app, Response, session

from radiocrepe.storage import DistributedStorage
from radiocrepe.db import User, Vote, QueueEntry
from radiocrepe.web.util import with_hub_db
from radiocrepe.web.live import broadcast

web_queue = Blueprint('queue', __name__,
                      template_folder='templates')


playing = None


def song(storage, uid):
    return storage.get(uid, None)


@web_queue.route('/playing/')
@with_hub_db
def _playing(db, storage, registry):
    if playing:
        storage = DistributedStorage.bind(current_app.config)
        meta = storage.get(playing.song_id, None)
        meta['time_add'] = playing.timestamp
        meta['added_by'] = User.get(db, playing.user_id).dict()
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@web_queue.route('/enqueue/<uid>/', methods=['POST'])
@with_hub_db
def enqueue(db, storage, registry, uid):
    if uid in storage:
        ts = int(time.time())
        user_id = session['user_id']
        db.session.add(QueueEntry(timestamp=ts, user_id=user_id, song_id=uid))
        db.session.commit()
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
    playing = db.session.query(QueueEntry).filter_by(waiting=True).\
      order_by(QueueEntry.timestamp).first()

    if playing:
        playing.waiting = False
        db.session.commit()

        broadcast('play', {
            'song': song(storage, playing.song_id),
            'user': User.get(db, playing.user_id).dict()
            }, ts=playing.timestamp)
        return ''
    else:
        return Response(jsonify(result='ERR_NO_NEXT').data,
                        mimetype='application/json', status=404)


@web_queue.route('/notify/stop/', methods=['POST'])
@with_hub_db
def _notify_stop(db, storage, registry):
    global playing
    broadcast('stop', song(storage, playing.song_id), ts=playing.timestamp)
    playing = None
    return ''


@web_queue.route('/queue/')
@with_hub_db
def _queue(db, storage, registry):
    res = []
    queue = db.session.query(QueueEntry).filter_by(waiting=True).\
      order_by(QueueEntry.timestamp)

    for entry in queue:
        elem = storage.get(entry.song_id, None)
        elem['uid'] = entry.song_id
        elem['ts_add'] = entry.timestamp
        elem['num_votes'] = db.session.query(Vote).filter_by(
            song_id=entry.song_id, timestamp=entry.timestamp).count()
        elem['self_vote'] = db.session.query(Vote).filter_by(
            song_id=entry.song_id, timestamp=entry.timestamp,
            user_id=entry.user_id).count()
        elem['added_by'] = User.get(db, entry.user_id).dict()
        res.append(elem)
    return json.dumps(res)


@web_queue.route('/play/<term>/', methods=['POST'])
@with_hub_db
def _search(db, storage, registry, term):
    term = unquote(term)

    res = list(storage.search(term, limit=10))

    if len(res) > 1:
        return json.dumps(res)
    elif len(res) == 1:
        ts = int(time.time())
        meta = res[0]
        db.session.add(QueueEntry(timestamp=ts, user_id=session['user_id'],
                                  song_id=meta['uid']))
        db.session.commit()
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
