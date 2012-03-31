# stdlib
from urllib import urlencode
from urllib2 import urlopen
from contextlib import closing

# 3rd party
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
from flask import Flask, jsonify, Response, render_template, \
     redirect, session

# radiocrepe
from radiocrepe.storage import DistributedStorage
from radiocrepe.util import load_config

from radiocrepe.web.auth import web_auth
from radiocrepe.web.queue import web_queue
from radiocrepe.web.hub import web_hub
from radiocrepe.web.live import web_live


SECRET_KEY = 'development key'


app = Flask(__name__)
app.register_blueprint(web_auth)
app.register_blueprint(web_queue)
app.register_blueprint(web_hub)
app.register_blueprint(web_live)
app.secret_key = SECRET_KEY


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
    storage = DistributedStorage.bind(app.config)
    return render_template('queue.html', title=app.config['title'],
                           user=session.get('user'), storage_data=storage.stats,
                           users_data=storage.db.user_stats)


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
