import os
from urllib import urlencode, unquote
from urllib2 import urlopen
import random
import copy
import time


from contextlib import closing

import ConfigParser

from radiocrepe.storage import Storage

from flask import Flask, jsonify, request, Response, render_template, json, g
app = Flask(__name__)


queue = []
playing = None


@app.route('/song/<uid>')
def song(uid):
    storage = Storage.get(app.config)
    meta = storage.get('index_uid_meta', uid, None)
    if meta is None:
        return 'song not found', 404
    else:
        f = open(meta['fpath'], 'rb')
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
        elem = storage.get('index_uid_meta', uid, None)
        elem['uid'] = uid
        elem['time'] = ts
        res.append(elem)
    return json.dumps(res)


@app.route('/playing')
def _playing():
    if playing:
        storage = Storage.bind(app.config)
        meta = storage.get('index_uid_meta', playing[1], None)
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

    res = set(storage.get('index_artist_uid', term, like=True))
    res |= set(storage.get('index_title_uid', term, like=True))

    if res:
        ts = time.time()
        uid = random.choice(list(res))
        queue.append((ts, uid))
        meta = storage.get('index_uid_meta', uid, None)
        meta['time'] = ts
        return jsonify(meta)
    else:
        return Response(jsonify(result='ERR_NO_RESULTS').data,
                        mimetype='application/json', status=404)


def jump_next():
    queue.pop(0)


def main(args):
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
                    config[k] = v

    for k, v in args.__dict__.iteritems():
        if v is not None:
            config[k] = v

    app.config.update(config)

    storage = Storage.bind(config)
    storage.initialize()
    storage.update()

    app.run(debug=True, host=config['host'], port=int(config['port']))
