# stdlib
import hashlib
from urllib import urlencode
import time

# 3rd party
from sqlalchemy import or_


class Storage(object):

    @classmethod
    def bind(cls, config):
        return cls(config)

    def _hash(self, mdata):
        keys = {}

        for (k, v) in mdata.iteritems():
            keys[k] = v.encode('utf-8') if v else ''

        return hashlib.sha1(urlencode(keys)).hexdigest().decode('utf-8')

    def _index(self, uid=None, timestamp=None, **mdata):

        if (self.db.query(self._songClass).filter_by(uid=uid).first()):
            return

        obj = self._songClass(timestamp=int(time.time()), uid=uid, **mdata)
        self._logger.debug(u'Indexing %s' % (obj))

        self.db.add(obj)
        self.db.commit()

    def search(self, term, limit=None):
        key = "%%%s%%" % term
        for r in self.db.query(
                self._songClass).filter(
                    or_(self._songClass.artist.like(key),
                        self._songClass.title.like(key)),
                        self._songClass.available == True).limit(limit):
            yield r.dict()

    def get(self, uid, default=None, private=False):
        first = self.db.query(self._songClass).filter_by(uid=uid).first()
        return first.dict(private=private) if first else default

    def __contains__(self, uid):
        return self.get(uid) != None

    def file(self, uid):
        """
        Overload: retrieve file by UID
        """
