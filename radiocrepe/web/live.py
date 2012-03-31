from Queue import Queue, Empty

from flask import Blueprint, request, json, current_app
from gevent import sleep, greenlet

from radiocrepe.storage import DistributedStorage


web_live = Blueprint('live', __name__,
                     template_folder='templates')


messages = {}


def broadcast(mtype, time, uid):
    global messages
    for queue in messages.itervalues():
        queue.put((mtype, time, uid))


def message(msg):
    mtype, ts, uid = msg

    storage = DistributedStorage.bind(current_app.config)
    meta = storage.get(uid, None)

    return json.dumps({'op': mtype, 'time_add': ts, 'data': meta})


@web_live.route('/updates/')
def updates():
    global messages
    guid = id(greenlet.getcurrent())

    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        queue = Queue()
        messages[guid] = queue
        try:
            while True:
                # receive stuff here
                try:
                    while True:
                        msg = message(queue.get_nowait())
                        ws.send(msg)
                except Empty:
                    sleep(1)
        finally:
            del messages[guid]
        return ''
    return 'I can haz websockets?'
