#stdlib
from threading import Thread
from itertools import islice
import time
from urllib2 import urlopen, HTTPError
from urllib import  urlencode
from contextlib import closing
import uuid
import os

# 3rd party
from flask import Flask, json, Response

# radiocrepe
from radiocrepe.storage import Storage
from radiocrepe.util import load_config


app = Flask(__name__)


@app.route('/song/<uid>/')
def song(uid):
    storage = Storage.bind(app.config)
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
        try:
            with closing(urlopen("http://%s/node/upload/" %
                                 self._config['server'],
                                 urlencode(data))):
                return True
        except HTTPError:
            return False

    def run(self):
        storage = Storage.bind(self._config)
        storage.initialize()
        storage.update()

        records = storage.new_records()

        # notify server about new stuff
        while True:
            batch = list(islice(records, 50))
            if not batch:
                break
            self._upload(batch)

        storage.last_sent = int(time.time())


def main(args, logger, handler):
    config = load_config(args)

    if 'node_id' not in config:
        config['node_id'] = uuid.uuid4()

    app.config.update(config)
    app.logger.addHandler(handler)

    t = StorageThread(config, logger)
    t.start()

    app.run(debug=config.get('debug', False),
            host=config['host'], port=int(config['port']))
