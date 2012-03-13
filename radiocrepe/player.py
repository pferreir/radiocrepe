from client import Client
import time
import os
import sys

from subprocess import Popen


class Player(object):

    def __init__(self, server, content_dir='content'):
        self._client = Client(server, content_dir=content_dir)
        self._exit = False
        self._content_dir = content_dir

    def run(self):
        self._client.initialize()
        for song in self._client.iter_songs():
            if song:
                self._client.download(song)
                self.play(song)
            else:
                time.sleep(5)

    def play(self, meta):
        print u'Playing "{artist} - {title}"'.format(**meta)
        p = Popen([self._cmd, os.path.join(self._content_dir, meta['uid'] + '.sng')])
        p.wait()

    def shutdown(self):
        self._client.shutdown()


class MPlayer(Player):
    _cmd = 'mplayer'


class VLCPlayer(Player):
    _cmd = 'vlc'


players = {
    'mplayer': MPlayer,
    'vlc': VLCPlayer
}


def main(server, player_name):
    player = players[player_name](server)
    try:
        player.run()
    except KeyboardInterrupt:
        player.shutdown()
        sys.exit(-1)
