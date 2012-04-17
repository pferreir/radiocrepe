# stdlib
from urllib import urlencode
from urllib2 import urlopen
from contextlib import closing

# 3rd party
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
from flask import Flask, jsonify, Response, render_template, \
     redirect, session
from flaskext.assets import Environment, Bundle

# radiocrepe
from radiocrepe.util import load_config
from radiocrepe.storage import DistributedStorage
from radiocrepe.web.util import with_hub_db

# blueprints
from radiocrepe.web.auth import web_auth, configure_auth
from radiocrepe.web.queue import web_queue
from radiocrepe.web.hub import web_hub
from radiocrepe.web.live import web_live
from radiocrepe.web.user import web_user


app = Flask(__name__)
app.register_blueprint(web_auth)
app.register_blueprint(web_queue)
app.register_blueprint(web_hub)
app.register_blueprint(web_live)
app.register_blueprint(web_user)


assets = Environment(app)

lib_bundle = Bundle('js/jquery.js', 'js/jquery.qtip.js', 'js/underscore.js',
                    'js/backbone.js', 'js/handlebars.js',
                    filters='jsmin', output='js/gen/libs.packed.js')

rc_bundle = Bundle('js/queue.js', 'js/user_profile.js', 'js/notifications.js',
                   filters='jsmin', output='js/gen/radiocrepe.packed.js')

assets.register('js_libs', lib_bundle)
assets.register('js_app', rc_bundle)


@app.route('/song/<uid>/')
@with_hub_db
def song(db, storage, registry, uid):
    """
    retrieve the song from one of the storage nodes
    """
    meta = storage.get(uid, None, private=True)
    if meta is None:
        return 'song not found', 404
    else:
        address = storage.node_registry.get_address(meta['node_id'])
        return redirect('http://{0}/song/{1}/'.format(address, meta['uid']))


@app.route('/artist/<name>/')
def artist_info(name):
    """
    Return a JSON structure with the information about an artists.
    The information is fetched directly from last.fm.
    """
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
@with_hub_db
def index(db, storage, registry):
    """
    Home page
    """
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
        assets.debug = True

    if not config.get('secret_key'):
        raise Exception('Please set a secret key!')

    app.secret_key = str(config['secret_key'])
    configure_auth(app)

    http_server = WSGIServer((config['host'], int(config['port'])),
                              app, handler_class=WebSocketHandler)
    http_server.serve_forever()
