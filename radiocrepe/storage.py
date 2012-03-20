# stdlib
from collections import defaultdict
import hashlib
import os
from urllib import urlencode
import json
import logging
import time

# 3rd party
import magic
import sqlite3
import pkg_resources

# radiocrepe
from radiocrepe.metadata import MIME_TYPES


index_uid_meta = {}
index_artist_uid = defaultdict(list)
index_title_uid = defaultdict(list)
index_album_uid = defaultdict(list)


class Storage(object):

    @classmethod
    def bind(cls, config):
        return cls(config)

    def __init__(self, config):
        self._conn = sqlite3.connect(os.path.join(
            config['content_dir'], 'songs.db'))
        self._conn.row_factory = sqlite3.Row
        self._config = config
        self._logger = logging.getLogger('radiocrepe.storage')

    def initialize(self):
        c = self._conn.cursor()
        r = c.execute('SELECT COUNT(*) FROM SQLITE_MASTER;')

        if r.fetchone()[0] <= 0:
            self._logger.warning('Database empty - creating from scratch')
            deftables = pkg_resources.resource_string('radiocrepe', 'tables.sql')
            for st in deftables.split('\n\n'):
                c.execute(st)

    def _file_metadata(self, mtype, fpath):
        return MIME_TYPES[mtype](fpath)

    def _make_key(self, term):
        if term is None:
            return None
        else:
            return filter(term.__class__.isalnum, term.lower().replace(' ', ''))

    def _index_file(self, fpath, mdata):
        keys = {}

        for (k, v) in mdata.iteritems():
            keys[k] = v.encode('utf-8') if v else ''

        uid = hashlib.sha1(urlencode(keys)).hexdigest().decode('utf-8')

        self._logger.debug(u'Indexing %s (%s)' % (uid, os.path.basename(fpath)))

        c = self._conn.cursor()
        r = c.execute('SELECT * FROM song_index WHERE uid = ?;', (uid,))

        if (r.fetchone()):
            return

        mdata.update({
            'uid': uid,
            'fpath': fpath
        })

        self._index(uid, mdata, int(time.time()))

    def _index(self, uid, data, ts):
        c = self._conn.cursor()
        c.execute('INSERT INTO song_index (uid, timestamp, fpath, mime, artist, title, album) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (uid, ts, data['fpath'], data['mime'], data['artist'], data['title'], data['album']))
        self._conn.commit()

    def search(self, term):
        c = self._conn.cursor()
        key = "%%%s%%" % term
        r = c.execute("SELECT * FROM song_index WHERE artist LIKE ? OR title LIKE ?", (key, key))
        return map(lambda r: dict(r), r.fetchall())

    def get(self, uid, default=None):
        c = self._conn.cursor()
        r = c.execute('SELECT * FROM song_index WHERE uid = ?', (uid,))

        res = r.fetchone()
        if res:
            return dict(res)
        else:
            return default

    def __contains__(self, uid):
        c = self._conn.cursor()
        r = c.execute('SELECT data FROM song_index WHERE uid = ?' % (uid,))
        return not not r.fetchone()

    def update(self):
	allowed_mtypes = self._config.get('allowed_mime_types').split(',') or MIME_TYPES.keys()
        self._logger.info('Updating DB')
        cdir = self._config['content_dir']
        for dirpath, dirnames, filenames in os.walk(cdir):
            for fname in filenames:
                mime = magic.Magic(mime=True)
                fpath = os.path.join(dirpath, fname)

                mtype = mime.from_file(fpath.encode('utf-8'))
                if mtype in allowed_mtypes:
                    meta = self._file_metadata(mtype, fpath)
                    if meta:
                        meta['mime'] = mtype
                        self._index_file(
                            os.path.relpath(fpath, cdir),
                            meta)
        self._logger.info('DB update finished')

    def file(self, uid):
        meta = self.get(uid)
        return open(os.path.join(self._config['content_dir'], meta['fpath']))
