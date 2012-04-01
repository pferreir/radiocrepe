import time
from Queue import Queue, Empty

from flask import Blueprint, request, json
from gevent import sleep, greenlet

from radiocrepe.web.util import with_storage
from radiocrepe.storage import DistributedStorage

web_live = Blueprint('live', __name__,
                     template_folder='templates')


messages = {}


def broadcast(mtype, data, ts=None):
    global messages
    for queue in messages.itervalues():
        queue.put((mtype, ts or time.time(), data))


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
                        mtype, ts, data = queue.get_nowait()
                        msg = json.dumps({
                            'mtype': mtype,
                            'ts': ts,
                            'data': data
                            })
                        ws.send(msg)
                except Empty:
                    sleep(1)
        finally:
            del messages[guid]
        return ''
    return 'I can haz websockets?'
