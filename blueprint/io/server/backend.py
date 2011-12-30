import boto
import boto.exception
import httplib
import socket

from blueprint import cfg
import librato
import statsd


access_key = cfg.get('s3', 'access_key')
bucket = cfg.get('s3', 'bucket')
protocol = 'https' if cfg.getboolean('s3', 'use_https') else 'http'
region = cfg.get('s3', 'region')
s3_region = 's3' if 'US' == region else 's3-{0}'.format(region)
secret_key = cfg.get('s3', 'secret_key')


def delete(key):
    """
    Remove an object from S3.  DELETE requests are free but this function
    still makes one billable request to account for freed storage.
    """
    content_length = head(key)
    if content_length is None:
        return None
    librato.count('blueprint-io-server.requests.delete')
    statsd.increment('blueprint-io-server.requests.delete')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    try:
        b.delete_key(key)
        # TODO librato.something('blueprint-io-server.storage', -content_length)
        statsd.update('blueprint-io-server.storage', -content_length)
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            boto.exception.S3ResponseError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def delete_blueprint(secret, name):
    return delete(key_for_blueprint(secret, name))


def delete_tarball(secret, name, sha):
    return delete(key_for_tarball(secret, name, sha))


def get(key):
    """
    Fetch an object from S3.  This function makes one billable request.
    """
    librato.count('blueprint-io-server.requests.get')
    statsd.increment('blueprint-io-server.requests.get')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    k = b.new_key(key)
    try:
        return k.get_contents_as_string()
    except boto.exception.S3ResponseError:
        return None
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def get_blueprint(secret, name):
    return get(key_for_blueprint(secret, name))


def get_tarball(secret, name, sha):
    return get(key_for_tarball(secret, name, sha))


def head(key):
    """
    Make a HEAD request for an object in S3.  This is needed to find the
    object's length so it can be accounted.  This function makes one
    billable request and anticipates another.
    """
    librato.count('blueprint-io-server.requests.head')
    statsd.increment('blueprint-io-server.requests.head')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    try:
        k = b.get_key(key)
        if k is None:
            return None
        return k.size
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def head_blueprint(secret, name):
    return head(key_for_blueprint(secret, name))


def head_tarball(secret, name, sha):
    return head(key_for_tarball(secret, name, sha))


def key_for_blueprint(secret, name):
    return '{0}/{1}/{2}'.format(secret,
                                name,
                                'blueprint.json')


def key_for_tarball(secret, name, sha):
    return '{0}/{1}/{2}.tar'.format(secret,
                                    name,
                                    sha)


def list(key):
    """
    List objects in S3 whose keys begin with the given prefix.  This
    function makes at least one billable request.
    """
    librato.count('blueprint-io-server.requests.list')
    statsd.increment('blueprint-io-server.requests.list')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    return b.list(key)
    try:
        return True
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def put(key, data):
    """
    Store an object in S3.  This function makes one billable request.
    """
    librato.count('blueprint-io-server.requests.put')
    statsd.increment('blueprint-io-server.requests.put')
    # TODO librato.something('blueprint-io-server.storage', len(data))
    statsd.update('blueprint-io-server.storage', len(data))
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    k = b.new_key(key)
    try:
        k.set_contents_from_string(data,
                                   policy='public-read',
                                   reduced_redundancy=True)
        return True
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def put_blueprint(secret, name, data):
    return put(key_for_blueprint(secret, name), data)


def put_tarball(secret, name, sha, data):
    return put(key_for_tarball(secret, name, sha), data)


def url_for(key):
    return '{0}://{1}.{2}.amazonaws.com/{3}'.format(protocol,
                                                    bucket,
                                                    s3_region,
                                                    key)


def url_for_blueprint(secret, name):
    return url_for(key_for_blueprint(secret, name))


def url_for_tarball(secret, name, sha):
    return url_for(key_for_tarball(secret, name, sha))
