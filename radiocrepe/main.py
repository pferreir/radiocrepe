import argparse
from radiocrepe import server
from radiocrepe import player


def main():
    parser = argparse.ArgumentParser(description='A simple office DJ')
    subparsers = parser.add_subparsers(help='sub-command help')

    server_parser = subparsers.add_parser('server', help='start an HTTP server')
    server_parser.set_defaults(action='server')
    server_parser.add_argument('music_dir')
    server_parser.add_argument('--port', default=5000)
    server_parser.add_argument('--host', default='localhost')
    server_parser.add_argument('--lastfm-key')
    server_parser.add_argument('--title', default='Radiocrepe')

    player_parser = subparsers.add_parser('player', help='start a player')
    player_parser.set_defaults(action='player')
    player_parser.add_argument('server')
    player_parser.add_argument('--player', default='mplayer')

    args = parser.parse_args()

    if args.action == 'server':
        server.main(args.music_dir, host=args.host, port=int(args.port),
                    lastfm_key=args.lastfm_key, title=args.title)
    else:
        player.main(args.server, args.player)
