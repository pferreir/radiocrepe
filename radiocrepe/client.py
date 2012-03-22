from urllib2 import urlopen, HTTPError
from urllib import  urlencode
from contextlib import closing
import os
import re
import json
from glob import glob
from threading import Thread
import time
import signal


class HTTPClient(object):

    def __init__(self, server):
        self._server = server
        self._surl = 'http://%s' % server

    def enqueue(self, uid):
        try:
            with closing(urlopen(self._surl + '/enqueue/',
                                 urlencode({'uid': uid}))) as d:
                data = json.load(d)
            return True
        except HTTPError:
            return False

    def notify_start(self):
        try:
            with closing(urlopen(self._surl + '/notify/start/', '')) as d:
                data = json.load(d)
                success = d.code == 200
            return data
        except HTTPError:
            return False

    def notify_stop(self):
        try:
            with closing(urlopen(self._surl + '/notify/stop/', '')) as d:
                success = d.code == 200
            return True
        except HTTPError:
            return False

    def get_queue(self):
        return json.load(urlopen(self._surl + '/queue/'))

    def get_stream(self, uid):
        return urlopen(self._surl + '/song/' + uid + '/')

    def get_stream_next(self):
        nxt = self.ask_next()
        if nxt:
            return self.get_stream(nxt)
        else:
            return None


class Content(object):
    def __init__(self, content_dir):
        self._content_dir = content_dir
        self._songs = {}
        self._sync()

    def _read_hdr(self, fname):
        with open(fname, 'rb') as f:
            return json.load(f)

    def _sync(self):
        for f in glob(os.path.join(self._content_dir, '*.sng')):
            f = re.split(r'\.|/', f)[-2]
            self._songs[f] = self._read_hdr(os.path.join(
                self._content_dir, f + '.hdr'))

    def add(self, uid, meta):
        self._songs[uid] = meta

    def _save_hdr(self, uid):
        with open(os.path.join(self._content_dir, uid + '.hdr'), 'wb') as f:
            json.dump(self._songs[uid], f)

    def __contains__(self, uid):
        return uid in self._songs

    def store(self, uid, meta, stream):
        with open(os.path.join(self._content_dir, uid + '.sng'), 'wb') as f:
            f.write(stream.read())
        self.add(uid, meta)
        self._save_hdr(uid)

    def __getitem__(self, uid):
        return self._songs[uid]


class Client(object):
    def __init__(self, url, content_dir='content'):
        self._httpc = HTTPClient(url)
        self._content = Content(content_dir)
        self._thread = Thread(target=self._background)
        self._exit = False
        self._last = None

    def _background(self):
        """
        Periodically checks for new updates and pre-fetchs songs
        """
        while not self._exit:
            q = self._httpc.get_queue()
            for meta in q:
                self.download(meta)
            time.sleep(30)

    def initialize(self):
        # start background thread
        signal.signal(signal.SIGINT, self._sigint_handler)
        self._thread.daemon = True
        self._thread.start()

    def _sigint_handler(self, signal, frame):
        self._exit = True

    def iter_songs(self):
        while not self._exit:
            queue = self._httpc.get_queue()
            if queue:
                for meta in queue:
                    if not self._last or \
                      meta['time'] > self._last['time']:
                        print 'enqueueing', meta
                        yield meta
                        self._last = meta
            else:
                yield None
            time.sleep(5)

    def notify_start(self):
        self._httpc.notify_start()

    def notify_stop(self):
        self._httpc.notify_stop()

    def download(self, meta, force=False):
        uid = meta['uid']
        if not force:
            if uid in self._content:
                return
        print 'downloading', uid
        stream = self._httpc.get_stream(uid)
        self._content.store(uid, meta, stream)

    def shutdown(self):
        print 'shutting down'
        self._exit = True
        self._thread.join()
