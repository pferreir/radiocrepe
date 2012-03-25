# stdlib
import hashlib
import os
from urllib import urlencode
import logging
import time

# 3rd party
import magic
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, or_

# radiocrepe
from radiocrepe.metadata import MIME_TYPES
from radiocrepe.db import Song, RemoteSong, Info
from radiocrepe.network import NodeRegistry, HubRegistry

Session = sessionmaker()


class Storage(object):

    @classmethod
    def bind(cls, config):
        return cls(config)

    def __init__(self, config):
        self._engine = create_engine('sqlite:///%s' % os.path.join(
            config['content_dir'], 'songs.db'))
        Session.configure(bind=self._engine)
        self._session = Session()
        self._config = config
        self._logger = logging.getLogger('radiocrepe.storage')

    def initialize(self):
        Song.metadata.create_all(self._engine)

    def _file_metadata(self, mtype, fpath):
        return MIME_TYPES[mtype](fpath)

    def _make_key(self, term):
        if term is None:
            return None
        else:
            return filter(term.__class__.isalnum, term.lower().replace(' ', ''))

    def _hash(self, mdata):
        keys = {}

        for (k, v) in mdata.iteritems():
            keys[k] = v.encode('utf-8') if v else ''

        return hashlib.sha1(urlencode(keys)).hexdigest().decode('utf-8')

    def _index(self, uid=None, timestamp=None, **mdata):

        if (self._session.query(self._songClass).filter_by(uid=uid).first()):
            return

        obj = self._songClass(timestamp=int(time.time()), uid=uid, **mdata)
        self._logger.debug(u'Indexing %s' % (obj))

        self._session.add(obj)
        self._session.commit()

    def search(self, term):
        key = "%%%s%%" % term
        return list(r.dict() for r in self._session.query(
            self._songClass).filter(or_(self._songClass.artist.like(key),
                                        self._songClass.title.like(key)),
                                    self._songClass.available == True))

    def get(self, uid, default=None):
        first = self._session.query(self._songClass).filter_by(uid=uid).first()
        return first.dict() if first else default

    def __contains__(self, uid):
        return self.get(uid) != None

    def file(self, uid):
        """
        Overload: retrieve file by UID
        """


class NodeStorage(Storage):

    _songClass = Song

    @property
    def last_sent(self):
        """
        The last time a record was sent to the server
        """
        res = self._session.query(Info.last_sent).scalar()

        if res:
            return res
        else:
            return None

    @last_sent.setter
    def last_sent(self, value):
        info = self._session.query(Info).first()
        if info:
            info.last_sent = value
        else:
            self._session.add(Info(last_sent=value))
        self._session.commit()

    def new_records(self):
        last_sent = self.last_sent or 0
        for obj in self._session.query(self._songClass).\
                filter(self._songClass.timestamp > last_sent):
            song = obj.dict()
            # no need for remote host to know this
            del song['fpath']
            yield song

    def file(self, uid):
        meta = self.get(uid)
        return open(os.path.join(self._config['content_dir'], meta['fpath']))

    def update(self):
        mtypes = self._config.get('allowed_mime_types', '')
        if mtypes:
            allowed_mtypes = mtypes.split(',')
        else:
            allowed_mtypes = MIME_TYPES.keys()

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
                        meta.update({
                            'mime': mtype,
                            'fpath': os.path.relpath(fpath, cdir),
                            'uid': self._hash(meta)
                            })
                        self._index(**meta)
        self._logger.info('DB update finished')


class DistributedStorage(Storage):

    _songClass = RemoteSong

    def __init__(self, config):
        self._engine = create_engine('sqlite:///' + os.path.join(
            config['content_dir'], 'radiocrepe_index.db'))
        Session.configure(bind=self._engine)
        self._session = Session()
        self._config = config
        self._logger = logging.getLogger('radiocrepe.dist_storage')
        self.node_registry = NodeRegistry(self)

    def initialize(self):
        RemoteSong.metadata.create_all(self._engine)
        self.node_registry.detach_all()

    def mark_available(self, node_id):
        """
        Mark all songs stored in this node as available
        """
        self._session.query(self._songClass).filter_by(node_id=node_id).update({
            self._songClass.available: True
        })
        self._session.commit()

    def mark_unavailable(self, node_id):
        """
        Mark all songs in this node as unavailable
        """
        self._session.query(self._songClass).filter_by(node_id=node_id).update({
            self._songClass.available: False
        })
        self._session.commit()

    def file(self, uid):
        r = self._node_registry.get(uid)
        if r:
            return urlopen('http://%s/song/%s' % (r.server, r.uid))
        else:
            return None

    def update_node(self, node_id, data):
        for song in data:
            self._index(node_id=node_id, **song)
