import time
import os
import hmac

from flask import Blueprint, request, json, current_app

from radiocrepe.storage import DistributedStorage
from radiocrepe.web.live import broadcast
from radiocrepe.db import User

web_hub = Blueprint('hub', __name__,
                    template_folder='templates')

nonce_registry = {}


@web_hub.route('/node/upload/', methods=['POST'])
def node_recv():
    """
    Receive metadata from the nodes
    """
    storage = DistributedStorage.bind(current_app.config)
    registry = storage.node_registry
    node = request.form.get('node_id')
    data = request.form.get('songs')
    server = request.form.get('server')

    if not registry.get(node):
        registry.attach(node, server)
    storage.update_node(node, json.loads(data))
    return ''


@web_hub.route('/node/detach/', methods=['POST'])
def node_detach():
    """
    Detach from a node
    """
    registry = DistributedStorage.bind(current_app.config).node_registry
    registry.detach(request.form.get('node_id'))
    return ''


@web_hub.route('/node/attach/', methods=['POST'])
def node_attach():
    """
    Detach from a node
    """
    registry = DistributedStorage.bind(current_app.config).node_registry
    node_id = request.form.get('node_id')
    owner_id = request.form.get('owner_id')
    signature = request.form.get('signature')

    if not owner_id:
        return 'no owner specified', 400

    owner = registry.db.query(User).get(owner_id)
    node = registry.get(node_id)

    if not owner:
        return 'owner does not exist', 400

    # TODO: ADD TIMEOUT!

    if node and node.owner != owner:
        return 'someone else owns that node', 403

    nonce = nonce_registry.get(node_id, None)
    if not nonce or signature != hmac.new(str(owner.secret_key),
                                          nonce[1]).hexdigest():
        return 'access denied', 403

    registry.attach(node_id, request.form.get('address'), owner_id)
    broadcast('attach', {
        'node_id': node_id,
        'owner': registry.db.get_user(owner_id)
        })
    return ''


@web_hub.route('/node/auth/', methods=['POST'])
def node_authenticate():
    """
    The client should send a POST request containing a description
    of the node it claims to be
    """
    node_id = request.form.get('node_id')
    if not node_id:
        return 'no node_id was sent', 400
    nonce = os.urandom(10).encode('hex')
    nonce_registry[node_id] = (time.time(), nonce)
    return nonce
