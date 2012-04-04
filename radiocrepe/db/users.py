from radiocrepe.db.base import HubSideBase

from sqlalchemy import Column, String


class User(HubSideBase):
    __schema__ = 'hub'
    __tablename__ = 'users'
    __public__ = ['user_id', 'picture', 'name']

    user_id = Column(String, primary_key=True)
    identity = Column(String)
    secret_key = Column(String)
    name = Column(String)
    picture = Column(String)

    @classmethod
    def get(cls, session, user_id):
        return session.query(cls).filter_by(user_id=user_id).first()

    def dict(self, private=False):
        d = {}
        for columnName in self.__table__.columns.keys():
            d[columnName] = getattr(self, columnName)

        if private:
            return d
        else:
            return dict((k, v) for (k, v) in d.iteritems() \
                        if k in self.__public__)
