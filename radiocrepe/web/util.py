from functools import wraps
import hashlib
import time
import os

from flask import current_app, Response, request
from werkzeug.http import parse_authorization_header
from radiocrepe.storage import DistributedStorage

nonce_registry = {}


def with_hub_db(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        strg = DistributedStorage.bind(current_app.config)
        return f(strg.db, strg, strg.node_registry, *args, **kwargs)
    return _wrapper


class with_digest_auth(object):

    def __init__(self, cred_provider):
        self.cred_provider = cred_provider

    def response(self, user, password, method, digest_uri, nonce,
                 cnonce, nc, qop):
        ha1 = hashlib.md5("%s:%s:%s" % (user, self.cred_provider.realm, password)).hexdigest()
        ha2 = hashlib.md5("%s:%s" % (method, digest_uri)).hexdigest()
        return hashlib.md5("%s:%s:%s:%s:%s:%s" % \
                           (ha1, nonce, nc, cnonce, qop, ha2)).hexdigest()

    def challenge(self, msg='authenticate first', stale=False, code=401):
            is_stale = ', stale=true' if stale else ''
            nonce = hashlib.sha1( os.urandom(10).encode('hex')).hexdigest()
            nonce_registry[request.remote_addr] = (nonce, time.time())
            return Response(msg, code,
                {'WWW-Authenticate': 'Digest realm="{0}", qop="auth", nonce="{1}"{2}'.format(self.cred_provider.realm, nonce, is_stale)})

    def __call__(self, f):
        @wraps(f)
        def _wrapper(*args, **kwargs):
            if 'registry' not in kwargs:
                raise Exception("'with_digest_auth' requires a 'registry'")
            else:
                self.cred_provider.set_session(kwargs['registry'].db.session)
            auth_header = request.headers.get('Authorization')

            if not auth_header or not auth_header.startswith("Digest"):
                return self.challenge()

            auth = parse_authorization_header(auth_header)

            if auth.username not in self.cred_provider:
                return self.challenge('no such user')

            if request.remote_addr in nonce_registry:
                nonce, ts = nonce_registry.get(request.remote_addr, None)
            else:
                return self.challenge('no nonce')

            if (time.time() - ts) > 600:
                return self.challenge('nonce expired', stale=True)

            result = self.response(auth.username, self.cred_provider.get(auth.username).secret_key,
                                    request.method, request.path, auth.nonce,
                                    auth.cnonce, auth.nc, auth.qop)

            if auth.nonce == nonce and auth.realm == self.cred_provider.realm and auth.response == result:
                return f(*args, user=self.cred_provider.get(auth.username), 
                         **kwargs)
            return self.challenge('wrong credentials' , code=403)
        return _wrapper
