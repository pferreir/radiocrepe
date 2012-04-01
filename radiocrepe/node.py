#stdlib
from threading import Thread
from itertools import islice
import time
from urllib import  urlencode
import os
import atexit
import requests

# 3rd party
from flask import Flask, json, Response

# radiocrepe
from radiocrepe.storage import NodeStorage
from radiocrepe.util import load_config


app = Flask(__name__)


def auth_request(config):
    return requests.auth.HTTPDigestAuth(config['user_id'], config['secret_key'])


@app.route('/song/<uid>/')
def song(uid):
    storage = NodeStorage.bind(app.config)
    meta = storage.get(uid, None)
    if meta is None:
        return 'song not found', 404
    else:
        f = storage.file(uid)
        return Response(f, direct_passthrough=True, mimetype=meta['mime'],
                        content_type=meta['mime'],
                        headers={'Content-Disposition': "attachment; filename=" + os.path.basename(meta['fpath'])})


class StorageThread(Thread):

    def __init__(self, config, logger):
        super(StorageThread, self).__init__()
        self._config = config
        self.daemon = True
        self._logger = logger

    def _upload(self, batch):
        self._logger.info('Notifying server of batch of %d songs' % len(batch))
        data = {
            'node_id': self._config['node_id'],
            'server': "{host}:{port}".format(**self._config),
            'songs': json.dumps(batch)
            }

        r = requests.post("http://%s/node/upload/" % self._config['server'],
                          data=urlencode(data), auth=auth_request(self._config))
        if r.status_code == 200:
            return True
        else:
            self._logger.error('upload failed (%s): %s' % (r.status_code, r.content))
            return False

    def run(self):
        storage = NodeStorage.bind(self._config)
        storage.initialize()
        storage.update()

        records = storage.new_records()

        # notify server about new stuff
        while True:
            batch = list(islice(records, 50))
            if not batch:
                break
            if not self._upload(batch):
                return

        storage.last_sent = int(time.time())


def attach_to_server(logger, config):
    r = requests.post("http://%s/node/attach/" % config['server'],
                      data=urlencode({'node_id': config['node_id'],
                                     'address': "{host}:{port}".format(**config)}),
                      auth=auth_request(config))

    if r.status_code == 200:
        return True
    else:
        logger.error('attach failed (%s): %s' % (r.status_code, r.content))
        return False


def detach_from_server(logger, config):
    r = requests.post("http://%s/node/detach/" % config['server'],
                      data=urlencode({'node_id': config['node_id']}),
                      auth=auth_request(config))

    if r.status_code == 200:
        return True
    else:
        logger.error('detach failed (%s): %s' % (r.status_code, r.content))
        return False


def main(args, logger, handler):
    config = load_config(args)

    if 'node_id' not in config:
        print "No 'node_id' set. Please add one in your config file."
        return

    app.config.update(config)
    app.logger.addHandler(handler)

    attach_to_server(logger, app.config)
    atexit.register(detach_from_server, logger, config)

    t = StorageThread(config, logger)
    t.start()

    app.run(debug=config.get('debug', False),
            host=config['host'], port=int(config['port']))
