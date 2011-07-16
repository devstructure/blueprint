from ConfigParser import ConfigParser, NoOptionError
import os.path
import sys


# Parse the configuration file for a valid Blueprint I/O Server.
cfg = ConfigParser(defaults={'server': 'https://devstructure.com'})
getattr(cfg, '_sections')['default'] = getattr(cfg, '_dict')()
cfg.read(['/etc/blueprint-io.cfg',
          os.path.expanduser('~/.blueprint-io.cfg')])
for option in ('server',):
    if not cfg.has_option('default', option):
        sys.stderr.write('cfg: missing {0}\n'.format(option))
        sys.exit(1)


def secret():
    """
    Return the configured secret.
    """
    try:
        return cfg.get('default', 'secret')
    except NoOptionError:
        return None

def server():
    """
    Return the configured blueprint-io server or default.
    """
    return cfg.get('default', 'server')
