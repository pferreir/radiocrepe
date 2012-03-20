# stdlib
import os
from urllib import urlencode, unquote
from urllib2 import urlopen
import random
import time
from contextlib import closing
import ConfigParser
from threading import Thread

# 3rd party
from flask import Flask, jsonify, request, Response, render_template, json, g

# radiocrepe
from radiocrepe.storage import Storage


app = Flask(__name__)


queue = []
playing = None


@app.route('/song/<uid>')
def song(uid):
    storage = Storage.bind(app.config)
    meta = storage.get(uid, None)
    if meta is None:
        return 'song not found', 404
    else:
        f = storage.file(uid)
        return Response(f, direct_passthrough=True, mimetype=meta['mime'],
                        content_type=meta['mime'],
                        headers={'Content-Disposition': "attachment; filename=" + os.path.basename(meta['fpath'])})


@app.route('/enqueue', methods=['POST'])
def enqueue():
    uid = request.form['uid']
    if uid in storage:
        queue.append((time.time(), uid))
        return jsonify({'id': uid})
    else:
        return Response(jsonify(result='ERR_NO_SUCH_SONG', id=uid).data,
                        mimetype='application/json', status=404)
        return jsonify(), 404


@app.route('/notify/start', methods=['POST'])
def _notify_start():
    global playing
    try:
        playing = queue.pop(0)
        return json.dumps(len(queue))
    except IndexError:
        return Response(jsonify(result='ERR_NO_NEXT').data,
                        mimetype='application/json', status=404)


@app.route('/notify/stop', methods=['POST'])
def _notify_stop():
    global playing
    playing = None
    return ''


@app.route('/queue')
def _queue():
    storage = Storage.bind(app.config)
    res = []
    for ts, uid in queue:
        elem = storage.get(uid, None)
        elem['uid'] = uid
        elem['time'] = ts
        res.append(elem)
    return json.dumps(res)


@app.route('/playing')
def _playing():
    if playing:
        storage = Storage.bind(app.config)
        meta = storage.get(playing[1], None)
        meta['time'] = playing[0]
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@app.route('/artist/<name>')
def artist_info(name):
    if app.config.get('lastfm_key'):
        params = {
            'method': 'artist.getinfo',
            'artist': name,
            'format': 'json',
            'api_key': app.config['lastfm_key']
        }
        url = "http://ws.audioscrobbler.com/2.0/?" + urlencode(params)
        with closing(urlopen(url)) as d:
            return Response(d.read(), mimetype='application/json')
    else:
        return Response(jsonify(result='ERR_NO_LASTFM_KEY').data,
                        mimetype='application/json', status=404)


@app.route('/')
def index():
    return render_template('queue.html', title=app.config['title'])


@app.route('/play/<term>', methods=['POST'])
def _search(term):
    storage = Storage.bind(app.config)

    term = unquote(term)

    res = storage.search(term)

    if res:
        ts = time.time()
        meta = random.choice(res)
        queue.append((ts, meta['uid']))
        meta['time'] = ts
        return jsonify(meta)
    else:
        return Response(jsonify(result='ERR_NO_RESULTS').data,
                        mimetype='application/json', status=404)


def jump_next():
    queue.pop(0)


class StorageThread(Thread):
    def __init__(self, config):
        super(StorageThread, self).__init__()
        self._config = config
        self.daemon = True

    def run(self):
        storage = Storage.bind(self._config)
        storage.initialize()
        storage.update()


def main(args, root_logger, handler):
    config = dict(host='localhost',
                  port=5000,
                  title='Radiocrepe',
                  content_dir='.')

    if args.c:
        config_ini = ConfigParser.ConfigParser()
        config_ini.read(args.c)

        for section in config_ini.sections():
            for k, v in config_ini.items(section):
                if v:
                    config[k] = unicode(v)
        if config_ini.has_option('site', 'debug'):
            config['debug'] = config_ini.getboolean('site', 'debug')

    for k, v in args.__dict__.iteritems():
        if v is not None:
            config[k] = v

    app.config.update(config)

    t = StorageThread(config)
    t.start()

    if not config['debug']:
        app.logger.addHandler(handler)

    app.run(debug=config['debug'],
            host=config['host'], port=int(config['port']))
