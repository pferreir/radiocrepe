# stdlib
import os
from urllib import urlencode, unquote
from urllib2 import urlopen
import random
import time
from contextlib import closing
from Queue import Queue, Empty

# 3rd party
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
from gevent import sleep
from flask import Flask, jsonify, request, Response, render_template, json, g, redirect

# radiocrepe
from radiocrepe.storage import DistributedStorage
from radiocrepe.util import load_config

app = Flask(__name__)


queue = []
playing = None
messages = {}


def broadcast(mtype, time, uid):
    global messages
    for queue in messages.itervalues():
        queue.put((mtype, time, uid))


def message(msg):
    mtype, ts, uid = msg

    storage = DistributedStorage.bind(app.config)
    meta = storage.get(uid, None)

    return json.dumps({'op': mtype, 'time_add': ts, 'data': meta})


@app.route('/song/<uid>/')
def song(uid):
    """
    retrieve the song from one of the storage nodes
    """
    storage = DistributedStorage.bind(app.config)
    meta = storage.get(uid, None)
    if meta is None:
        return 'song not found', 404
    else:
        address = storage.node_registry.get_address(meta['node_id'])
        return redirect('http://{0}/song/{1}/'.format(address, meta['uid']))


@app.route('/node/upload/', methods=['POST'])
def node_recv():
    """
    Receive metadata from the nodes
    """
    storage = DistributedStorage.bind(app.config)
    registry = storage.node_registry
    node = request.form.get('node_id')
    data = request.form.get('songs')
    server = request.form.get('server')

    if not registry.get(node):
        registry.attach(node, server)
    storage.update_node(node, json.loads(data))
    return ''


@app.route('/node/detach/', methods=['POST'])
def node_detach():
    """
    Detach from a node
    """
    registry = DistributedStorage.bind(app.config).node_registry
    registry.detach(request.form.get('node_id'))


@app.route('/enqueue/', methods=['POST'])
def enqueue():
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


@app.route('/notify/start/', methods=['POST'])
def _notify_start():
    global playing
    try:
        playing = queue.pop(0)
        broadcast('play', playing[0], playing[1])
        return json.dumps(len(queue))
    except IndexError:
        return Response(jsonify(result='ERR_NO_NEXT').data,
                        mimetype='application/json', status=404)


@app.route('/notify/stop/', methods=['POST'])
def _notify_stop():
    global playing
    broadcast('stop', playing[0], playing[1])
    playing = None
    return ''


@app.route('/queue/')
def _queue():
    storage = DistributedStorage.bind(app.config)
    res = []
    for ts, uid in queue:
        elem = storage.get(uid, None)
        elem['uid'] = uid
        elem['time_add'] = ts
        res.append(elem)
    return json.dumps(res)


@app.route('/updates/')
def updates():
    global messages

    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        queue = Queue()
        messages[id(request)] = queue
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
            del messages[id(request)]
        return ''
    return 'I can haz websockets?'


@app.route('/playing/')
def _playing():
    if playing:
        storage = DistributedStorage.bind(app.config)
        meta = storage.get(playing[1], None)
        meta['time_add'] = playing[0]
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@app.route('/artist/<name>/')
def artist_info(name):
    if app.config.get('lastfm_key'):
        params = {
            'method': 'artist.getinfo',
            'artist': name.encode('utf-8'),
            'format': 'json',
            'api_key': app.config['lastfm_key']
        }
        url = u"http://ws.audioscrobbler.com/2.0/?" + urlencode(params)
        with closing(urlopen(url)) as d:
            return Response(d.read(), mimetype='application/json')
    else:
        return Response(jsonify(result='ERR_NO_LASTFM_KEY').data,
                        mimetype='application/json', status=404)


@app.route('/')
def index():
    return render_template('queue.html', title=app.config['title'])


@app.route('/play/<term>/', methods=['POST'])
def _search(term):
    storage = DistributedStorage.bind(app.config)
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


def jump_next():
    queue.pop(0)


def main(args, root_logger, handler):
    global messages
    config = load_config(args)

    storage = DistributedStorage.bind(config)
    storage.initialize()

    app.config.update(config)

    if not config['debug']:
        app.logger.addHandler(handler)
    else:
        app.debug = True

    http_server = WSGIServer((config['host'], int(config['port'])),
                              app, handler_class=WebSocketHandler)
    http_server.serve_forever()
    #app.run(debug=config['debug'],
    #        host=config['host'], port=int(config['port']))
