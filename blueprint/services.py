"""
Search harder for service dependencies.  The APT, Yum, and files backends
have already found the services of note but the file and package resources
which need to trigger restarts have not been fully enumerated.
"""

import logging
import os.path
import subprocess


def _service(b, manager, service, deps):
    if 'packages' not in deps:
        return

    # Build a map of the directory that contains each file in the
    # blueprint to the pathname of that file.
    dirs = dict([(os.path.dirname(pathname), pathname)
                 for pathname in b.files])
    for dirname in ('/etc', '/etc/init', '/etc/init.d'):
        dirs.pop(dirname, None)

    # Add dependencies for every file in the blueprint that's also in
    # this service's package or in a directory in this service's package.
    for package in deps['packages']:
        try:
            p = subprocess.Popen(['dpkg-query', '-L', package],
                                 close_fds=True, stdout=subprocess.PIPE)
        except OSError as e:
            p = subprocess.Popen(['rpm', '-ql', package],
                                 close_fds=True, stdout=subprocess.PIPE)
        for line in p.stdout:
            pathname = line.rstrip()
            if pathname in b.files:
                b.services[manager][service]['files'].add(pathname)
            elif pathname in dirs:
                b.services[manager][service]['files'].add(dirs[pathname])


def services(b):
    logging.info('searching for service dependencies')
    for manager, services in b.services.iteritems():
        for service, deps in services.iteritems():
            _service(b, manager, service, deps)
