from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Boolean


Base = declarative_base()


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

    __mapper_args__= {'always_refresh': True}

    def dict(row):
        d = {}
        for columnName in row.__table__.columns.keys():
            d[columnName] = getattr(row, columnName)

        return d


class Song(SongMixin, Base):
    __tablename__ = 'songs'

    fpath = Column(String)

    def __unicode__(self):
        return u"<Song:{0} @ {1}>".format(self.uid, self.fpath)


class RemoteSong(SongMixin, Base):
    __tablename__ = 'song_index'
    node_id = Column(String, primary_key=True)
    available = Column(Boolean, default=True)

    def __unicode__(self):
        return u"<RemoteSong:{0} @ {1}>".format(self.uid, self.node_id)


class Info(Base):
    __tablename__ = 'info'
    last_sent = Column(Integer, primary_key=True)


class NodeEntry(Base):
    __tablename__ = 'nodes'
    node_id = Column(String, primary_key=True)
    address = Column(String)


class HubEntry(Base):
    __tablename__ = 'hubs'
    hub_id = Column(String, primary_key=True)
    address = Column(String)
    last_sent = Column(Integer)
