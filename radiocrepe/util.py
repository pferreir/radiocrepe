import ConfigParser


def load_config(args):
    config = dict(host='localhost',
                  port=5000,
                  title='Radiocrepe',
                  content_dir='.')

    if args.c:
        config_ini = ConfigParser.ConfigParser()
        config_ini.read(args.c)

        for section in config_ini.sections():
            for k, v in config_ini.items(section):
                if v:
                    config[k] = unicode(v)
        if config_ini.has_option('site', 'debug'):
            config['debug'] = config_ini.getboolean('site', 'debug')

    for k, v in args.__dict__.iteritems():
        if v is not None:
            config[k] = v

    return config
