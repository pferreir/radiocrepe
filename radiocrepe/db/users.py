from radiocrepe.db.base import DBObject

from sqlalchemy import Column, String


class User(DBObject):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    identity = Column(String, primary_key=False)
    secret_key = Column(String)

    @classmethod
    def get(cls, session, user_id):
        return session.query(cls).filter_by(user_id=user_id).first()
