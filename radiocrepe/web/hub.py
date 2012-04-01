import time
import os

from flask import Blueprint, request, json, current_app

from radiocrepe.storage import DistributedStorage
from radiocrepe.web.live import broadcast
from radiocrepe.web.util import with_digest_auth, with_node_registry, with_storage
from radiocrepe.db import User

web_hub = Blueprint('hub', __name__,
                    template_folder='templates')


class CredentialProvider:
    realm = 'radiocrepe node auth'

    def __init__(self):
        pass

    def get(self, user_id):
        user = self.session.query(User).get(user_id)
        return user

    def __contains__(self, user):
        return self.get(user) != None

    def set_session(self, session):
        self.session = session


credential_provider = CredentialProvider()


@web_hub.route('/node/upload/', methods=['POST'])
@with_node_registry
@with_storage(DistributedStorage)
@with_digest_auth(credential_provider)
def node_recv(storage, registry, user):
    """
    Receive metadata from the nodes
    """
    node = request.form.get('node_id')
    data = request.form.get('songs')
    server = request.form.get('server')

    if not registry.get(node):
        return 'node is not attached to this storage', 400
    storage.update_node(node, json.loads(data))
    return ''


@web_hub.route('/node/detach/', methods=['POST'])
@with_node_registry
@with_digest_auth(credential_provider)
def node_detach(registry, user):
    """
    Detach from a node
    """
    node_id = request.form.get('node_id')

    registry.detach(node_id)
    broadcast('detach', {
        'node_id': node_id,
        'owner': user.dict()
        })

    return ''


@web_hub.route('/node/attach/', methods=['POST'])
@with_node_registry
@with_digest_auth(credential_provider)
def node_attach(registry, user):
    """
    Attach to a node
    """
    node_id = request.form.get('node_id')

    registry.attach(node_id, request.form.get('address'), user.user_id)
    broadcast('attach', {
        'node_id': node_id,
        'owner': user.dict()
        })
    return ''


@web_hub.route('/node/test/', methods=['POST'])
@with_node_registry
@with_digest_auth(credential_provider)
def node_test(registry, user):
    return str(request.form)
