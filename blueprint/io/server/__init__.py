import base64
from flask import Flask, Response, abort, redirect, render_template, request
import hashlib
import json
import os
import re
import sys
import urlparse

from blueprint import Blueprint
from blueprint import cfg
import backend
import librato
import statsd


app = Flask(__name__)


def _blueprint(secret, name):
    """
    Fetch a blueprint from S3 and turn it into a real Blueprint object.

    The name can't be given as a kwarg or Blueprint.__init__ will go
    looking for the JSON in Git.
    """
    data = backend.get_blueprint(secret, name)
    if data is None:
        return None
    elif data is False:
        return False
    b = Blueprint()
    b.name = name
    b.update(json.loads(data))
    return b


def _server():
    """
    Reconstitute the name of this Blueprint I/O Server.
    """
    return urlparse.urlunparse((request.environ.get('wsgi.url_scheme',
                                                    'https'),
                                request.environ.get('HTTP_HOST',
                                                    'devstructure.com'),
                                '', '', '', ''))


class MeteredResponse(Response):
    """
    HTTP responses that account for the outbound bandwidth they consume.
    """
    def __init__(self, *args, **kwargs):
        super(MeteredResponse, self).__init__(*args, **kwargs)
        content_length = len(kwargs.get('response', ''))
        if 0 < content_length:
            librato.count('blueprint-io-server.bandwidth.out', content_length)
            statsd.update('blueprint-io-server.bandwidth.out', content_length)


@app.errorhandler(400)
def bad_request(e):
    return MeteredResponse(response='',
                           status=400,
                           content_type='text/plain')


@app.errorhandler(404)
def not_found(e):
    return MeteredResponse(response='',
                           status=404,
                           content_type='text/plain')


@app.errorhandler(502)
def bad_gateway(e):
    return MeteredResponse(response='',
                           status=502,
                           content_type='text/plain')


def validate_secret(secret):
    if re.match(r'^[0-9A-Za-z_-]{64}$', secret) is None:
        abort(400)


def validate_name(name):
    if re.search(r'[/ \t\r\n]', name) is not None:
        abort(400)


def validate_sha(sha):
    if re.match(r'^[0-9a-f]{40}$', sha) is None:
        abort(400)


def validate_content_length():
    if cfg.getint('io', 'max_content_length') < request.content_length:
        abort(413)


@app.route('/secret', methods=['GET'])
def secret():
    while 1:
        s = base64.urlsafe_b64encode(os.urandom(48))
        try:
            iter(backend.list(s)).next()
        except StopIteration:
            break
    return MeteredResponse(response='{0}\n'.format(s),
                           status=201,
                           content_type='text/plain')


browser_pattern = re.compile(r'Chrome|Gecko|Microsoft|Mozilla|Safari|WebKit')


@app.route('/<secret>/<name>', methods=['GET'])
def get_blueprint(secret, name):
    validate_secret(secret)
    validate_name(name)

    content_length = backend.head_blueprint(secret, name)
    if content_length is None:
        abort(404)

    # Pretty HTML for browsers.
    if browser_pattern.search(request.environ.get('HTTP_USER_AGENT', '')) \
       or 'html' == request.args.get('format'):
        librato.count('blueprint-io-server.renders')
        statsd.increment('blueprint-io-server.renders')
        return render_template('blueprint.html', b=_blueprint(secret, name))

    # Raw JSON for everybody else.
    else:
        librato.count('blueprint-io-server.requests.get')
        statsd.increment('blueprint-io-server.requests.get')
        librato.count('blueprint-io-server.bandwidth.out', content_length)
        statsd.update('blueprint-io-server.bandwidth.out', content_length)
        return redirect(backend.url_for_blueprint(secret, name), code=301)


@app.route('/<secret>/<name>', methods=['PUT'])
def put_blueprint(secret, name):
    validate_secret(secret)
    validate_name(name)

    librato.count('blueprint-io-server.bandwidth.in', request.content_length)
    statsd.update('blueprint-io-server.bandwidth.in', request.content_length)
    validate_content_length()

    # Validate the blueprint JSON format.  This could stand more rigor
    # or, dare I say it, a schema?
    try:
        for k in request.json.iterkeys():
            if k not in ('arch', 'files', 'packages', 'services', 'sources'):
                abort(400)
    except ValueError:
        abort(400)

    # Remove tarballs referenced by the old blueprint but not the new one.
    b = _blueprint(secret, name)
    if b is not None and b is not False:
        for filename in set(b.sources.itervalues()) - \
                        set(request.json.get('sources', {}).itervalues()):
            backend.delete_tarball(secret, name, filename[0:-4])

    # Store the blueprint JSON in S3.
    if not backend.put_blueprint(secret, name, request.data):
        abort(502)

    return MeteredResponse(response='',
                           status=202,
                           content_type='text/plain')


@app.route('/<secret>/<name>/<sha>.tar', methods=['GET'])
def get_tarball(secret, name, sha):
    validate_secret(secret)
    validate_name(name)
    sha = sha.lower()
    validate_sha(sha)

    content_length = backend.head_tarball(secret, name, sha)
    if content_length is None:
        abort(404)

    librato.count('blueprint-io-server.requests.get')
    statsd.increment('blueprint-io-server.requests.get')
    librato.count('blueprint-io-server.bandwidth.out', content_length)
    statsd.update('blueprint-io-server.bandwidth.out', content_length)

    return redirect(backend.url_for_tarball(secret, name, sha), code=301)


@app.route('/<secret>/<name>/<sha>.tar', methods=['PUT'])
def put_tarball(secret, name, sha):
    validate_secret(secret)
    validate_name(name)
    sha = sha.lower()
    validate_sha(sha)

    librato.count('blueprint-io-server.bandwidth.in', request.content_length)
    statsd.update('blueprint-io-server.bandwidth.in', request.content_length)
    validate_content_length()

    # Validate the tarball content.
    if hashlib.sha1(request.data).hexdigest() != sha:
        abort(400)

    # Ensure the tarball appears in the blueprint.
    b = _blueprint(secret, name)
    if b is None:
        abort(404)
    elif b is False:
        abort(502)
    if '{0}.tar'.format(sha) not in b.sources.itervalues():
        abort(400)

    # Store the tarball in S3.
    if not backend.put_tarball(secret, name, sha, request.data):
        abort(502)

    return MeteredResponse(response='',
                           status=202,
                           content_type='text/plain')


@app.route('/<secret>/<name>/<name2>.sh', methods=['GET'])
def sh(secret, name, name2):
    if 'user-data' == name2:
        return user_data(secret, name)
    if name != name2:
        abort(400)
    validate_secret(secret)
    validate_name(name)

    # Generate POSIX shell code from the blueprint.
    b = _blueprint(secret, name)
    if b is None:
        abort(404)
    elif b is False:
        abort(502)
    s = b.sh(server=_server(), secret=secret)
    s.out.insert(0, '#!/bin/sh\n\n')
    return MeteredResponse(response=s.dumps(),
                           status=200,
                           content_type='text/plain')


@app.route('/<secret>/<name>/user-data.sh', methods=['GET'])
def user_data(secret, name):
    validate_secret(secret)
    validate_name(name)
    b = _blueprint(secret, name)
    if b is None:
        abort(404)
    elif b is False:
        abort(502)
    return MeteredResponse(response="""#!/bin/sh

set -e

TMPDIR="$(mktemp -d)"
cd "$TMPDIR"
trap "rm -rf \\"$TMPDIR\\"" EXIT

wget "{0}/{1}/{2}/{2}.sh"

sh "$(ls)"
""".format(_server(), secret, name),
                           status=200,
                           content_type='text/plain')


if '__main__' == __name__:
    app.run(host='0.0.0.0', debug=True)
