from radiocrepe.db.base import HubSideBase, NodeSideBase, DB
from radiocrepe.db.schema import Song, RemoteSong, Info, NodeEntry, HubEntry
from radiocrepe.db.users import User


class NodeIndex(DB):
    def __init__(self, config):
        super(NodeIndex, self).__init__(config, 'radiocrepe_index.db')

    @property
    def user_stats(self):
        return {
            "total": self.session.query(User).count(),
            "active": self.session.query(User).count()
            }

    @classmethod
    def get_user(cls, session, user_id):
        return User.get(session, user_id)


class HubDB(DB):
    def __init__(self, config):
        super(HubDB, self).__init__(config, 'radiocrepe_songs.db')
