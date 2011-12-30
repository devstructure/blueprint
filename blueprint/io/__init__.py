import logging
import sys

from blueprint import Blueprint
from blueprint import cfg
from blueprint import git
import http


def pull(server, secret, name):
    """
    Pull a blueprint from the secret and name on the configured server.
    """
    r = http.get('/{0}/{1}'.format(secret, name), server=server)
    if 200 == r.status:
        b = Blueprint.load(r, name)

        for filename in b.sources.itervalues():
            logging.info('fetching source tarballs - this may take a while')
            r = http.get('/{0}/{1}/{2}'.format(secret, name, filename),
                         server=server)
            if 200 == r.status:
                try:
                    f = open(filename, 'w')
                    f.write(r.read())
                except OSError:
                    logging.error('could not open {0}'.format(filename))
                    return None
                finally:
                    f.close()
            elif 404 == r.status:
                logging.error('{0} not found'.format(filename))
                return None
            elif 502 == r.status:
                logging.error('upstream storage service failed')
                return None
            else:
                logging.error('unexpected {0} fetching tarball'.
                              format(r.status))
                return None

        return b
    elif 404 == r.status:
        logging.error('blueprint not found')
    elif 502 == r.status:
        logging.error('upstream storage service failed')
    else:
        logging.error('unexpected {0} fetching blueprint'.format(r.status))
    return None


def push(server, secret, b):
    """
    Push a blueprint to the secret and its name on the configured server.
    """

    r = http.put('/{0}/{1}'.format(secret, b.name),
                 b.dumps(),
                 {'Content-Type': 'application/json'},
                 server=server)
    if 202 == r.status:
        pass
    elif 400 == r.status:
        logging.error('malformed blueprint')
        return None
    elif 502 ==  r.status:
        logging.error('upstream storage service failed')
        return None
    else:
        logging.error('unexpected {0} storing blueprint'.format(r.status))
        return None

    if b._commit is None and 0 < len(b.sources):
        logging.warning('blueprint came from standard input - '
                        'source tarballs will not be pushed')
    elif b._commit is not None:
        tree = git.tree(b._commit)
        for dirname, filename in sorted(b.sources.iteritems()):
            blob = git.blob(tree, filename)
            content = git.content(blob)
            logging.info('storing source tarballs - this may take a while')
            r = http.put('/{0}/{1}/{2}'.format(secret, b.name, filename),
                         content,
                         {'Content-Type': 'application/x-tar'},
                         server=server)
            if 202 == r.status:
                pass
            elif 400 == r.status:
                logging.error('tarball content or name not expected')
                return None
            elif 404 == r.status:
                logging.error('blueprint not found')
                return None
            elif 413 == r.status:
                logging.error('tarballs can\'t exceed 64MB')
                return None
            elif 502 == r.status:
                logging.error('upstream storage service failed')
                return None
            else:
                logging.error('unexpected {0} storing tarball'.
                              format(r.status))
                return None

    return '{0}/{1}/{2}'.format(server, secret, b.name)


def secret(server):
    """
    Fetch a new secret from the configured server.
    """
    r = http.get('/secret', server=server)
    if 201 == r.status:
        secret = r.read().rstrip()
        logging.warning('created secret {0}'.format(secret))
        logging.warning('to set as the default secret, store it in ~/.blueprint.cfg:')
        sys.stderr.write('\n[io]\nsecret = {0}\nserver = {1}\n\n'.
            format(secret, cfg.get('io', 'server')))
        return secret
    elif 502 == r.status:
        logging.error('upstream storage service failed')
        return None
    else:
        logging.error('unexpected {0} creating secret'.format(r.status))
        return None
