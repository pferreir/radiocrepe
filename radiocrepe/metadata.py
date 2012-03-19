from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError


def flac_read(fpath):
    audio = FLAC(fpath)
    audio.pprint()
    return {
        'artist': audio.get('artist', [None])[0],
        'album': audio.get('album', [None])[0],
        'title': audio.get('title', [None])[0]
        }


def id3_read(fpath):
    try:
        audio = EasyID3(fpath)
    except ID3NoHeaderError:
        return None
    return {
        'artist': audio.get('artist', [None])[0],
        'album': audio.get('album', [None])[0],
        'title': audio.get('title', [None])[0]
        }


MIME_TYPES = {
    'audio/mpeg': id3_read,
    'audio/x-flac': flac_read
    }
