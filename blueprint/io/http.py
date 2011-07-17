import errno
import httplib
import socket
import urlparse

from blueprint import cfg


def _connect(server=None):
    if server is None:
        server = cfg.get('io', 'server')
    url = urlparse.urlparse(server)
    if -1 == url.netloc.find(':'):
        port = url.port or 443 if 'https' == url.scheme else 80
    else:
        port = None
    if 'https' == url.scheme:
        return httplib.HTTPSConnection(url.netloc, port)
    else:
        return httplib.HTTPConnection(url.netloc, port)


def _request(verb, path, body=None, headers={}, server=None):
    c = _connect(server)
    try:
        c.request(verb, path, body, headers)
    except socket.error as e:
        if errno.EPIPE != e.errno:
            raise e
    return c.getresponse()


def delete(path, server=None):
    return _request('DELETE', path, server=server)


def get(path, headers={}, server=None):
    c = _connect(server)
    c.request('GET', path, None, headers)
    r = c.getresponse()
    while r.status in (301, 302, 307):
       url = urlparse.urlparse(r.getheader('Location'))
       r = get(url.path,
               {'Content-Type': r.getheader('Content-Type')},
               urlparse.urlunparse((url.scheme, url.netloc, '', '', '', '')))
    return r


def post(path, body, headers={}, server=None):
    return _request('POST', path, body, headers, server)


def put(path, body, headers={}, server=None):
    return _request('PUT', path, body, headers, server)
