from flask import Blueprint, jsonify, session, current_app

from radiocrepe.db import NodeIndex
from radiocrepe.db.users import User

web_user = Blueprint('user', __name__,
                     template_folder='templates')


@web_user.route('/user/keys/')
def user_keys():
    user_id = session.get('user_id')

    if not user_id:
        return 'Not logged in', 403

    db = NodeIndex(current_app.config)
    user_db = User.get(db.session, user_id)

    return jsonify({
        'user_id': user_id,
        'secret_key': user_db.secret_key
    })
