from radiocrepe.db.base import HubSideBase

from sqlalchemy import Column, String


class User(HubSideBase):
    __schema__ = 'hub'
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    identity = Column(String)
    secret_key = Column(String)

    @classmethod
    def get(cls, session, user_id):
        return session.query(cls).filter_by(user_id=user_id).first()

    def dict(row):
        d = {}
        for columnName in row.__table__.columns.keys():
            d[columnName] = getattr(row, columnName)

        return d
