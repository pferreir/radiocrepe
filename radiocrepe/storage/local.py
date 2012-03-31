import logging
import os

from radiocrepe.storage.base import Storage
from radiocrepe.db import HubDB, Song, Info
from radiocrepe.storage.metadata import MIME_TYPES
import magic


class NodeStorage(Storage):

    _songClass = Song

    def __init__(self, config):
        self.db = HubDB(config)
        self._config = config
        self._logger = logging.getLogger('radiocrepe.storage')

    def initialize(self):
        Song.metadata.create_all(self.db.engine)

    def _file_metadata(self, mtype, fpath):
        return MIME_TYPES[mtype](fpath)

    @property
    def last_sent(self):
        """
        The last time a record was sent to the server
        """
        res = self.db.query(Info.last_sent).scalar()

        if res:
            return res
        else:
            return None

    @last_sent.setter
    def set_last_sent(self, value):
        info = self.db.query(Info).first()
        if info:
            info.last_sent = value
        else:
            self.db.add(Info(last_sent=value))
        self.db.commit()

    def new_records(self):
        last_sent = self.last_sent or 0
        for obj in self.db.query(self._songClass).\
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
