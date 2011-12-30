"""
Python interface to StatsD, cribbed from Steve Ivy <steveivy@gmail.com>'s
python_example.py in the standard distribution.
"""

from ConfigParser import NoOptionError, NoSectionError
import logging
import random
import socket
import sys

from blueprint import cfg


try:
    host, port = cfg.get('statsd', 'host'), cfg.getint('statsd', 'port')
except (NoOptionError, NoSectionError, ValueError):
    host = port = None


def timing(stat, time, sample_rate=1):
    """
    Log timing information.
    >>> statsd.timing('some.time', 500)
    """
    # TODO First positional argument may be string or list like the others.
    _send({stat: '{0}|ms'.format(time)}, sample_rate)


def increment(stats, sample_rate=1):
    """
    Increments one or more stats counters.
    >>> statsd.increment('some.int')
    >>> statsd.increment('some.int', 0.5)
    """
    update(stats, 1, sample_rate)


def decrement(stats, sample_rate=1):
    """
    Decrements one or more stats counters.
    >>> statsd.decrement('some.int')
    """
    update(stats, -1, sample_rate)


def update(stats, delta=1, sample_rate=1):
    """
    Updates one or more stats counters by arbitrary amounts.
    >>> statsd.update('some.int', 10)
    """
    if type(stats) is not list:
        stats = [stats]
    _send(dict([(stat, '{0}|c'.format(delta)) for stat in stats]), sample_rate)


def _send(data, sample_rate=1):
    """
    Squirt the metrics over UDP.
    """
    if host is None or port is None:
        return
    sampled_data = {}
    if 1 > sample_rate:
        if random.random() <= sample_rate:
            for k, v in data.iteritems():
                sampled_data[k] = '{0}|@{1}'.format(v, sample_rate)
    else:
        sampled_data = data
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for k, v in sampled_data.iteritems():
            #print('{0}:{1}'.format(k, v))
            s.sendto('{0}:{1}'.format(k, v), (host, port))
    except:
        logging.error(repr(sys.exc_info()))
