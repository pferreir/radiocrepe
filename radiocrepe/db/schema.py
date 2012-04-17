from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

from radiocrepe.db.base import NodeSideBase, HubSideBase


class SongMixin(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    uid = Column(String, primary_key=True)
    timestamp = Column(Integer)
    mime = Column(String)
    artist = Column(String)
    title = Column(String)
    album = Column(String)

    __mapper_args__ = {'always_refresh': True}

    def dict(row):
        d = {}
        for columnName in row.__table__.columns.keys():
            d[columnName] = getattr(row, columnName)

        return d


class Vote(HubSideBase):
    __tablename__ = 'votes'

    user_id = Column(String, ForeignKey("users.user_id"), primary_key=True)
    song_id = Column(String, ForeignKey("song_index.uid"), primary_key=True)
    timestamp = Column(Integer, primary_key=True)


class QueueEntry(HubSideBase):
    __tablename__ = 'queue'

    user_id = Column(String, ForeignKey("users.user_id"), primary_key=True)
    song_id = Column(String, ForeignKey("song_index.uid"), primary_key=True)
    timestamp = Column(Integer, primary_key=True)
    waiting = Column(Boolean, default=True)


class Song(SongMixin, NodeSideBase):
    __tablename__ = 'songs'

    fpath = Column(String)

    def __unicode__(self):
        return u"<Song:{0} @ {1}>".format(self.uid, self.fpath)


class RemoteSong(SongMixin, HubSideBase):
    __tablename__ = 'song_index'

    node_id = Column(String, primary_key=True)
    available = Column(Boolean, default=True)

    def __unicode__(self):
        return u"<RemoteSong:{0} @ {1}>".format(self.uid, self.node_id)


class Info(NodeSideBase):
    __tablename__ = 'info'

    last_sent = Column(Integer, primary_key=True)


class NodeEntry(HubSideBase):
    __tablename__ = 'nodes'

    node_id = Column(String, primary_key=True)
    address = Column(String)
    active = Column(Boolean, default=True)
    owner_id = Column(String, ForeignKey("users.user_id"))
    owner = relationship('User',
                         backref=backref('users', lazy='dynamic'))


class HubEntry(NodeSideBase):
    __tablename__ = 'hubs'

    hub_id = Column(String, primary_key=True)
    address = Column(String)
    last_sent = Column(Integer)
