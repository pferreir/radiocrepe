from flask import Blueprint, url_for, request, session, redirect, current_app
from flaskext.oauth import OAuth

from radiocrepe.db import NodeIndex
from radiocrepe.db.users import User

import os
import hashlib


FACEBOOK_APP_ID = '198279803608888'
FACEBOOK_APP_SECRET = 'a0c01fd66de11780f326897d4ac312ac'

oauth = OAuth()

facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=FACEBOOK_APP_ID,
    consumer_secret=FACEBOOK_APP_SECRET,
    request_token_params={'scope': 'email'}
)


web_auth = Blueprint('auth', __name__,
                 template_folder='templates')


@web_auth.route('/login')
def login():
    return facebook.authorize(callback=url_for('auth.facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


@web_auth.route('/login/authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )

    db = NodeIndex(current_app.config)

    session['oauth_token'] = (resp['access_token'], '')
    user = facebook.get('/me?fields=id,name,picture')

    session['user'] = user.data

    if not User.get(db.session, user.data['id']):
        user_id = hashlib.sha1('facebook:' + user.data['id']).hexdigest()
        db.session.add(User(user_id=user_id, identity=user.data['id'],
                            secret_key=os.urandom(10).encode('hex')))

        db.session.commit()

    next_page = request.args.get('next')

    if next_page:
        return redirect(next_page)
    else:
        return redirect(url_for('index'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('oauth_token')
