import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


HubSideBase = declarative_base()
NodeSideBase = declarative_base()

Session = sessionmaker()


class DB(object):
    session = None

    def __init__(self, config, fname):
        self.engine = create_engine('sqlite:///%s' % os.path.join(
        config['content_dir'], fname))
        Session.configure(bind=self.engine)
        self.session = Session()

    def __getattr__(self, attr):
        return getattr(self.session, attr)
