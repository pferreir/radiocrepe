from flask import Blueprint, url_for, request, session, redirect, current_app
from flaskext.oauth import OAuth

from radiocrepe.db import NodeIndex
from radiocrepe.db.users import User

import os
import hashlib


oauth = OAuth()
web_auth = Blueprint('auth', __name__,
                 template_folder='templates')


def get_facebook_oauth_token():
    return session.get('oauth_token')


def configure_auth(app):
    config = app.config

    app.auth = {}

    if 'facebook_key' not in config or 'facebook_secret' not in config:
        raise Exception('Please set your facebook keys!')

    facebook = oauth.remote_app(
        'facebook',
        base_url='https://graph.facebook.com/',
        request_token_url=None,
        access_token_url='/oauth/access_token',
        authorize_url='https://www.facebook.com/dialog/oauth',
        consumer_key=config['facebook_key'],
        consumer_secret=config['facebook_secret'],
        request_token_params={'scope': 'email'})

    app.auth['facebook'] = facebook
    facebook.tokengetter(get_facebook_oauth_token)


@web_auth.route('/login')
def login():
    return current_app.auth['facebook'].authorize(
        callback=url_for('auth.facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


@web_auth.route('/login/authorized')
def facebook_authorized():

    facebook = current_app.auth['facebook']

    # ripped off from Flask-OAuth
    # since `facebook` should be defined in app start time
    if 'oauth_verifier' in request.args:
        data = facebook.handle_oauth1_response()
    elif 'code' in request.args:
        data = facebook.handle_oauth2_response()
    else:
        data = facebook.handle_unknown_response()
    facebook.free_request_token()
    # ---

    if data is None:
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
