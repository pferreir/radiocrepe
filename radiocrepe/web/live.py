import time
from Queue import Queue, Empty

from flask import Blueprint, request, json
from gevent import sleep, greenlet

from radiocrepe.web.util import with_storage
from radiocrepe.storage import DistributedStorage

web_live = Blueprint('live', __name__,
                     template_folder='templates')


messages = {}


def broadcast(mtype, uid, ts=None):
    global messages
    for queue in messages.itervalues():
        queue.put((mtype, ts or time.time(), uid))


def message(storage, msg):
    mtype, ts, uid = msg
    meta = storage.get(uid, None)

    return json.dumps({'op': mtype, 'time_add': ts, 'data': meta})


@web_live.route('/updates/')
@with_storage(DistributedStorage)
def updates(storage):
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
                        msg = message(storage, queue.get_nowait())
                        ws.send(msg)
                except Empty:
                    sleep(1)
        finally:
            del messages[guid]
        return ''
    return 'I can haz websockets?'
