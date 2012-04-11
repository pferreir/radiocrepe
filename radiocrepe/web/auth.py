from flask import Blueprint, url_for, request, session, redirect, current_app
from flaskext.oauth import OAuth

from radiocrepe.db import NodeIndex
from radiocrepe.db.users import User
from radiocrepe.web.live import broadcast

import os
import hashlib


class OAuthAuthenticator(object):
    pass


class FacebookAuthenticator(OAuthAuthenticator):

    def configure(self, config):
        self._facebook = oauth.remote_app(
            'facebook',
            base_url='https://graph.facebook.com/',
            request_token_url=None,
            access_token_url='/oauth/access_token',
            authorize_url='https://www.facebook.com/dialog/oauth',
            request_token_params={'scope': 'email'},
            consumer_key=config['oauth_key'],
            consumer_secret=config['oauth_secret'])

        return self._facebook

    def get_user_data(self):
            return self._facebook.get('/me?fields=id,name,picture')


class GitHubAuthenticator(OAuthAuthenticator):

    def configure(self, config):
        self._github = oauth.remote_app(
            'github',
            base_url='https://api.github.com/',
            request_token_url=None,
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            consumer_key=config['oauth_key'],
            consumer_secret=config['oauth_secret'])

        return self._github

    def get_user_data(self):
        data = self._github.get('/user').data
        return {
            "picture": data['avatar_url'],
            "name": data['name'],
            "id": data["id"],
            "email": data["email"]
            }


OAUTH_CONFIGS = {
    'facebook': FacebookAuthenticator,
    'github': GitHubAuthenticator
    }


def get_oauth_token():
    return session.get('oauth_token')


def configure_auth(app):
    config = app.config

    app.auth = {}

    if 'oauth_provider' not in config or \
      config['oauth_provider'] not in OAUTH_CONFIGS:
        raise Exception('Please select a valid oauth provider!')

    if 'oauth_key' not in config or 'oauth_secret' not in config:
        raise Exception('Please set your oauth key/secret!')

    provider = config['oauth_provider']
    authenticator = OAUTH_CONFIGS[provider]()
    remote_app = authenticator.configure(config)

    app.auth = {
        'authenticator': authenticator,
        'provider': provider,
        'app': remote_app
    }
    remote_app.tokengetter(get_oauth_token)


oauth = OAuth()
web_auth = Blueprint('auth', __name__,
                 template_folder='templates')


@web_auth.route('/login/')
def login():
    return current_app.auth['app'].authorize(
        callback=url_for('auth.oauth_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


@web_auth.route('/logout/')
def logout():
    session.pop('user')
    return redirect(request.referrer or url_for('index'))


@web_auth.route('/login/authorized/')
def oauth_authorized():

    remote_app = current_app.auth['app']

    # ripped off from Flask-OAuth
    # since `remote_app` should be defined in app start time
    if 'oauth_verifier' in request.args:
        data = remote_app.handle_oauth1_response()
    elif 'code' in request.args:
        data = remote_app.handle_oauth2_response()
    else:
        data = remote_app.handle_unknown_response()
    remote_app.free_request_token()
    # ---

    if data is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )

    db = NodeIndex(current_app.config)

    session['oauth_token'] = (data['access_token'], '')

    user = current_app.auth['authenticator'].get_user_data()
    identity = current_app.auth['provider'] + ':' + str(user['id'])
    user_id = hashlib.sha1(identity).hexdigest()

    user_db = User.get(db.session, user_id)

    session['user_id'] = user_id
    session['user'] = user

    if not user_db:
        user_db = User(user_id=user_id, identity=identity,
                    secret_key=os.urandom(10).encode('hex'))
        db.add(user_db)

    db.query(User).filter_by(user_id=user_id).update({
        'name': user['name'],
        'picture': user['picture']
    })

    db.session.commit()

    broadcast('login', user_db.dict(private=False))

    next_page = request.args.get('next')

    if next_page:
        return redirect(next_page)
    else:
        return redirect(url_for('index'))
