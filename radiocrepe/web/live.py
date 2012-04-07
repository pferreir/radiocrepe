import time
from Queue import Queue, Empty

from flask import Blueprint, request, json
from gevent import sleep, greenlet

from radiocrepe.web.util import with_hub_db

web_live = Blueprint('live', __name__,
                     template_folder='templates')


messages = {}


def broadcast(mtype, data, ts=None):
    global messages
    for queue in messages.itervalues():
        queue.put((mtype, ts or time.time(), data))


@web_live.route('/updates/')
@with_hub_db
def updates(db, storage, registry):
    """
    Websockets - read-write loop
    Here messages are broadcasted to all clients
    """
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
