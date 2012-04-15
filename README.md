# Radiocrepe


Radiocrepe is a web application that allows you to run your own "office radio" at your workplace. It was initially inspired by [GitHub Play](https://github.com/holman/play) but it provides a different feature set, namely streaming (using VLC's Python bindings) and a distributed storage model.


## Dependencies

 * [SQLAlchemy](http://www.sqlalchemy.org/)
 * [Mutagen](http://code.google.com/p/mutagen/)
 * [python-magic](https://github.com/ahupp/python-magic)
 * [requests](https://github.com/ahupp/python-magic)
 * [Flask](http://flask.pocoo.org/)
 * [python-oauth2](https://github.com/simplegeo/python-oauth2)
 * [Flask-OAuth](http://packages.python.org/Flask-OAuth/)
 * [webassets](http://elsdoerfer.name/docs/webassets/)
 * [Flask-Assets](http://elsdoerfer.name/docs/flask-assets/)
 * [gevent](http://www.gevent.org/)
 * [gevent-websocket](http://www.gelens.org/code/gevent-websocket/)
 * [VLC Python bindings](http://wiki.videolan.org/Python_bindings) - these are not automatically installed, make sure they are available in your system


## Usage

Start a server:

    $ radiocrepe server -c server_config.ini

There is a `server.ini` file in the source code that you can adapt to your needs.

If you have a last.fm API key you can use the option `lastfm_key` for extra awesomeness (pictures!)

For each storage, start a node instance:

    $ radiocrepe node -c node_config.ini

There's also a `node.ini` example in the package.

Start a player somewhere else:

    $ radiocrepe player localhost:5000


## Authentication

If you want to use GitHub OAuth, you'll need to add the DigiCert Root CA to your `httplib2` CA certificates:

    curl -L https://github.com/ask/python-github2/raw/master/github2/DigiCert_High_Assurance_EV_Root_CA.crt >> /path/to/your/httplib2/cacerts.txt


## 3rd party components

This app bundles the following 3rd party components:

 * [Iconic](http://somerandomdude.com/work/iconic/) by P. J. Onori;
 * [backbone.js](http://documentcloud.github.com/backbone/) by DocumentCloud;
 * [underscore.js](http://documentcloud.github.com/underscore/) by DocumentCloud;
 * [jQuery](http://jquery.com) by John Resig;
 * [handlebars.js](http://handlebarsjs.com/) by Yehuda Katz;
 * [qTip2](http://craigsworks.com/projects/qtip2/) by Craig Thompson;
