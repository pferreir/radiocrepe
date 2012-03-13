import os
import magic
import hashlib
from collections import defaultdict
from urllib import urlencode, unquote
from urllib2 import urlopen
import random
import copy
import time

from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

from contextlib import closing

from flask import Flask, jsonify, request, Response, render_template, json, g
app = Flask(__name__)


index_uid_meta = {}
index_artist_uid = defaultdict(list)
index_title_uid = defaultdict(list)
index_album_uid = defaultdict(list)

queue = []
playing = None


def make_key(term):
    if term is None:
        return None
    else:
        return filter(term.__class__.isalnum, term.lower().replace(' ', ''))


def flac_read(fpath):
    audio = FLAC(fpath)
    audio.pprint()
    return {
        'artist': audio.get('artist', [None])[0],
        'album': audio.get('album', [None])[0],
        'title': audio.get('title', [None])[0]
        }


def id3_read(fpath):
    try:
        audio = EasyID3(fpath)
    except ID3NoHeaderError:
        return None
    return {
        'artist': audio['artist'][0],
        'album': audio.get('album', [None])[0],
        'title': audio['title'][0]
        }


MIME_TYPES = {
    'audio/mpeg': id3_read,
    'audio/x-flac': flac_read
    }


def index_file(fpath, mtype):
    mdata = MIME_TYPES[mtype](fpath)

    if not mdata:
        return

    d = {}

    for (k, v) in mdata.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        d[k] = v if v else ''

    uid = hashlib.sha1(urlencode(d)).hexdigest()
    print(uid)
    mdata.update({
        'fpath': fpath,
        'uid': uid,
        'mime': mtype
    })
    index_uid_meta[uid] = mdata

    k = make_key(mdata['artist'])
    if k:
        index_artist_uid[k].append(uid)

    k = make_key(mdata['title'])
    if k:
        index_title_uid[k].append(uid)

    k = make_key(mdata['album'])
    if k:
        index_album_uid[k].append(uid)


@app.route('/song/<uid>')
def song(uid):
    meta = index_uid_meta.get(uid, None)
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
    if uid in index_uid_meta:
        queue.append((time.time(), uid))
        return jsonify({'id': uid})
    else:
        return Response(jsonify(result='ERR_NO_SUCH_SONG', id=uid).data,
                        mimetype='application/json', status=404)
        return jsonify(), 404


@app.route('/next', methods=['POST'])
def _next():
    global playing
    if len(queue):
        playing = queue.pop(0)
        print playing
        return jsonify(index_uid_meta[playing[1]])
    else:
        playing = None
        return Response(jsonify(result='ERR_NO_NEXT').data,
                        mimetype='application/json', status=404)


@app.route('/queue')
def _queue():
    res = []
    for ts, uid in queue:
        elem = copy.copy(index_uid_meta[uid])
        elem['uid'] = uid
        elem['time'] = ts
        res.append(elem)
    return json.dumps(res)


@app.route('/playing')
def _playing():
    if playing:
        meta = index_uid_meta.get(playing[1], None)
        meta['time'] = playing[0]
    else:
        meta = None
    return Response(json.dumps(meta),
                    mimetype='application/json')


@app.route('/artist/<name>')
def artist_info(name):
    if app.config['lastfm_key']:
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
    term = make_key(unquote(term))
    res = set()
    for title, uid in index_title_uid.iteritems():
        if term.encode('utf-8') in title:
            res |= set(uid)
    for artist, uid in index_artist_uid.iteritems():
        if term.encode('utf-8') in artist:
            res |= set(uid)

    if res:
        ts = time.time()
        uid = random.choice(list(res))
        queue.append((ts, uid))
        meta = copy.copy(index_uid_meta[uid])
        meta['time'] = ts
        return jsonify(meta)
    else:
        return Response(jsonify(result='ERR_NO_RESULTS').data,
                        mimetype='application/json', status=404)


def jump_next():
    queue.pop(0)


def main(music_dir, host='localhost', port=5000, lastfm_key=None, title='Radiocrepe'):
    for dirpath, dirnames, filenames in os.walk(music_dir):
        for fname in filenames:
                mime = magic.Magic(mime=True)
                fpath = os.path.join(dirpath, fname)
                mtype = mime.from_file(fpath)
                if mtype in MIME_TYPES:
                    index_file(fpath, mtype)

    app.config['lastfm_key'] = lastfm_key
    app.config['title'] = title
    app.run(debug=True, host=host, port=port)
