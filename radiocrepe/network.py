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
        NodeEntry.metadata.create_all(storage._engine)
        self._session = storage._session
        self._storage = storage

    def attach(self, node_id, server):
        """
        Attach remote storage
        """
        self._session.add(NodeEntry(node_id=node_id, address=server))
        self._storage.mark_available(node_id)

    def detach(self, node_id):
        """
        Detach remote storage
        """
        self._session.query(NodeEntry).filter_by(node_id=node_id).delete()

    def __getitem__(self, node_id):
        try:
            return self._session.query(NodeEntry).filter_by(
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
        return self._session.query(NodeEntry.address).\
          filter_by(node_id=node_id).first()[0]


class HubRegistry(object):
    def __init__(self, storage):
        self._logger = logging.getLogger('radiocrepe.hub_reg')
        self._storage = storage
        HubEntry.metadata.create_all(storage._engine)
