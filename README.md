# Radiocrepe


## Usage

Start a server:

    $ radiocrepe server -c config.ini

There is a `radiocrepe.ini` file in the source code that you can adapt to your needs.

If you have a last.fm API key you can use the option `lastfm_key` for extra awesomeness (pictures!)

Start a player somewhere else:

    $ radiocrepe player localhost:5000

## Authentication

If you want to use GitHub OAuth, you'll need to add the DigiCert Root CA to your `httplib2` CA certificates:

    curl -L https://github.com/ask/python-github2/raw/master/github2/DigiCert_High_Assurance_EV_Root_CA.crt >> /path/to/your/httplib2/cacerts.txt
