from client import Client
import time
import os
import sys

import vlc


class Player(object):

    def __init__(self, config):
        cdir = os.path.expanduser('~/.radiocrepe/songs/')

        if not os.path.exists(cdir):
            os.makedirs(cdir)

        self._client = Client(config.server, content_dir=cdir)
        self._exit = False
        self._content_dir = cdir
        self._config = config
        self._playing = False
        self._index = 0

    def initialize(self, config):
        """
        Overload this
        """

    def run(self):
        self._client.initialize()
        self.initialize()

        last_ts = None

        while not self._exit:
            for song in self._client.iter_songs():
                if song and song['time'] != last_ts:
                    self._enqueue(song)
                    last_ts = song['time']

                    if not self._playing:
                        self._play_index(self._index)
                else:
                    time.sleep(5)

    def on_song_start(self):
        self._playing = True
        self._index += 1
        self._client.notify_start()

    def on_stop(self):
        self._client.notify_stop()

    def shutdown(self):
        self._client.shutdown()


def callback_wrap(self, callback):
    def _wrapper(*args, **kwargs):
        return callback(self, *args, **kwargs)
    return _wrapper


class VLCPlayer(Player):
    def initialize(self):
        if self._config.mode == 'stream':
            args = "--sout=#gather:transcode{{vcodec=none,acodec=mp4a,ab=128,channels=2,samplerate=44100}}:rtp{{sdp=rtsp://{host}:5544/}} --no-sout-rtp-sap --rtsp-host={host} --no-sout-standard-sap --ttl=1 --sout-keep".format(**self._config.__dict__)
        else:
            args = ""

        self._instance = vlc.Instance(args)
        self._list = self._instance.media_list_new()
        self._vlc_l = self._instance.media_list_player_new()
        self._vlc_l.set_media_list(self._list)
        self._vlc = self._instance.media_player_new()
        self._vlc_l.set_media_player(self._vlc)

        self._evt_mgr = self._vlc.event_manager()
        self._evt_mgr.event_attach(vlc.EventType.MediaPlayerPlaying,
                             callback_wrap(self, self._nextItem))
        self._evt_mgr.event_attach(vlc.EventType.MediaPlayerEndReached,
                             callback_wrap(self, self._stopped))

    def _enqueue(self, meta):
        self._client.download(meta)
        self._list.add_media('file://' + os.path.join(
            os.getcwd(), self._content_dir, meta['uid'] + '.sng'))

    def _nextItem(self, player, event):
        self.on_song_start()

    def _stopped(self, player, event):
        self._playing = False
        self.on_stop()

    def _play_index(self, index):
        self._vlc_l.play_item_at_index(index)


players = {
    'vlc': VLCPlayer
    }


def main(config):
    player = players[config.player](config)
    try:
        player.run()
    except KeyboardInterrupt:
        player.shutdown()
        sys.exit(-1)
