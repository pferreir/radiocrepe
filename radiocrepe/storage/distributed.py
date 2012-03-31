import logging
from urllib2 import urlopen

from radiocrepe.db import NodeIndex, RemoteSong
from radiocrepe.storage.base import Storage
from radiocrepe.network import NodeRegistry


class DistributedStorage(Storage):

    _songClass = RemoteSong

    def __init__(self, config):
        self.db = NodeIndex(config)
        self._config = config
        self._logger = logging.getLogger('radiocrepe.dist_storage')
        self.node_registry = NodeRegistry(self)

    def initialize(self):
        RemoteSong.metadata.create_all(self.db.engine)
        self.node_registry.detach_all()

    def mark_available(self, node_id):
        """
        Mark all songs stored in this node as available
        """
        self.db.query(self._songClass).filter_by(node_id=node_id).update({
            self._songClass.available: True
        })
        self.db.commit()

    def mark_unavailable(self, node_id):
        """
        Mark all songs in this node as unavailable
        """
        self.db.query(self._songClass).filter_by(node_id=node_id).update({
            self._songClass.available: False
        })
        self.db.commit()

    def file(self, uid):
        r = self._node_registry.get(uid)
        if r:
            return urlopen('http://%s/song/%s' % (r.server, r.uid))
        else:
            return None

    def update_node(self, node_id, data):
        for song in data:
            self._index(node_id=node_id, **song)

    @property
    def stats(self):
        return {
            "nodes": self.node_registry.stats
            }
