from flask import Blueprint, request, json, current_app

from radiocrepe.storage import DistributedStorage
from radiocrepe.web.live import broadcast


web_hub = Blueprint('hub', __name__,
                    template_folder='templates')


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
    node_id = request.form.get('node_id')
    owner_id = request.form.get('owner_id')
    registry = DistributedStorage.bind(current_app.config).node_registry
    registry.attach(node_id, request.form.get('address'), owner_id)
    broadcast('attach', {
        'node_id': node_id,
        'owner': registry.db.get_user(owner_id)
        })
    return ''


