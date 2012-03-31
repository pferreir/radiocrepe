# stdlib
import logging

# 3rd party
from sqlalchemy.orm import sessionmaker, exc

# radiocrepe
from radiocrepe.db import NodeEntry, HubEntry


Session = sessionmaker()


class NoSuchNodeException(Exception):
    pass


class NodeRegistry(object):

    def __init__(self, storage):
        self._logger = logging.getLogger('radiocrepe.node_reg')
        NodeEntry.metadata.create_all(storage.db.engine)
        self.db = storage.db
        self._storage = storage

    def attach(self, node_id, server, owner):
        """
        Attach remote storage
        """
        self._logger.info('Attaching %s' % node_id)
        if node_id in self:
            self.set_node_active(node_id, True)
        else:
            self.db.add(NodeEntry(node_id=node_id, address=server,
                                  owner=owner))
            self.db.commit()
        self._storage.mark_available(node_id)

    def detach(self, node_id):
        """
        Detach remote storage
        """
        self._logger.info('Detaching %s' % node_id)
        self.set_node_active(node_id, False)
        self._storage.mark_unavailable(node_id)

    def set_node_active(self, node_id, status):
        self.db.query(NodeEntry).filter_by(node_id=node_id).update({
            NodeEntry.active: status
        })
        self.db.commit()

    def __getitem__(self, node_id):
        try:
            return self.db.query(NodeEntry).filter_by(
                node_id=node_id).one()
        except exc.NoResultFound:
            raise NoSuchNodeException()

    def get(self, node_id, default=None):
        """
        Get a node given its id
        """
        try:
            return self[node_id]
        except NoSuchNodeException:
            return default

    def __contains__(self, node_id):
        return self.get(node_id, False) != False

    def get_address(self, node_id):
        return self.db.query(NodeEntry.address).\
          filter_by(node_id=node_id).first()[0]

    def __iter__(self):
        for node in self.db.query(NodeEntry):
            yield node

    def detach_all(self):
        for node in self:
            if node.active:
                self.detach(node.node_id)

    @property
    def stats(self):
        return {
            "total": self.db.query(NodeEntry).count(),
            "active": self.db.query(NodeEntry).filter_by(active=True).count()
            }


class HubRegistry(object):
    def __init__(self, storage):
        self._logger = logging.getLogger('radiocrepe.hub_reg')
        self._storage = storage
        HubEntry.metadata.create_all(storage.db.engine)
