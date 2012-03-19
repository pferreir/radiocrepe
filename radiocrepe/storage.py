# stdlib
from collections import defaultdict
import hashlib
import os
from urllib import urlencode
import json
import logging

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
            if isinstance(v, unicode):
                v = v.encode('utf-8')
            keys[k] = v if v else ''

        uid = hashlib.sha1(urlencode(keys)).hexdigest()

        self._logger.debug('Indexing %s (%s)' % (uid, os.path.basename(fpath)))

        c = self._conn.cursor()
        r = c.execute('SELECT * FROM index_uid_meta WHERE key = ?;', (uid,))

        if (r.fetchone()):
            return

        mdata.update({
            'uid': uid,
            'fpath': fpath
        })

        self._index('index_uid_meta', uid, mdata, exact=True)
        self._index('index_artist_uid', mdata['artist'], uid)
        self._index('index_title_uid', mdata['title'], uid)
        self._index('index_album_uid', mdata['album'], uid)

    def _index(self, index, key, data, exact=False):
        c = self._conn.cursor()

        if not exact:
            key = self._make_key(key)

        if isinstance(data, dict):
            value = json.dumps(data)
        else:
            value = data

        c.execute('INSERT INTO %s (key, data) VALUES (?, ?)' % index,
                  (key, value))
        self._conn.commit()

    def get(self, index, key, default=None, like=False):
        c = self._conn.cursor()
        if like:
            key = '%%%s%%' % self._make_key(key)
            r = c.execute("SELECT data FROM %s WHERE key LIKE ?" % index, (key,))
        else:
            r = c.execute('SELECT data FROM %s WHERE key = ?' % index, (key,))

        if like:
            return map(lambda x: x[0], r.fetchall())
        else:
            res = r.fetchone()
            if res:
                return json.loads(res[0])
            else:
                return default

    def __contains__(self, uid):
        c = self._conn.cursor()
        r = c.execute('SELECT data FROM index_uid_meta WHERE key = ?' % (uid,))
        return not not r.fetchone()

    def update(self):
        self._logger.info('Updating DB')
        cdir = self._config['content_dir']
        for dirpath, dirnames, filenames in os.walk(cdir):
            for fname in filenames:
                mime = magic.Magic(mime=True)
                fpath = os.path.join(dirpath, fname)
                mtype = mime.from_file(fpath)
                if mtype in MIME_TYPES:
                    meta = self._file_metadata(mtype, fpath)
                    if meta:
                        meta['mime'] = mtype
                        self._index_file(
                            os.path.relpath(fpath, cdir),
                            meta)
        self._logger.info('DB update finished')

    def file(self, uid):
        meta = self.get('index_uid_meta', uid)
        return open(os.path.join(self._config['content_dir'], meta['fpath']))
