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
                success = d.code == 200
            return True
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


class Client(object):
    def __init__(self, url):
        self._httpc = HTTPClient(url)
        self._exit = False
        self._last = None

    def iter_songs(self):
        while not self._exit:
            queue = self._httpc.get_queue()
            if queue:
                for meta in queue:
                    if not self._last or \
                      meta['ts_add'] > self._last['ts_add']:
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

    def shutdown(self):
        print 'shutting down'
        self._exit = True
