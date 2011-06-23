"""
Search harder for service dependencies.  The APT, Yum, and files backends
have already found the services of note but the file and package resources
which need to trigger restarts have not been fully enumerated.
"""

from collections import defaultdict
import logging
import os.path
import re
import subprocess


# Pattern for matching pathnames in init scripts and such.
pattern = re.compile(r'(/[/0-9A-Za-z_.-]+)')


def _service_files(b, manager, service, deps):
    """
    Extract fully-qualified pathnames from files on which this service
    depends as further dependencies.
    """
    if 'files' not in deps:
        return

    # Add the service init script or config to the list of files considered.
    pathnames = set(deps['files']) # This makes a copy, which is desired.
    if 'sysvinit' == manager:
        pathnames.add('/etc/init.d/{0}'.format(service))
    elif 'upstart' == manager:
        pathnames.add('/etc/init/{0}.conf'.format(service))

    # Add dependencies for every pathname extracted from init scripts and
    # other dependent files.
    for pathname in pathnames:
        content = open(pathname).read()
        for match in pattern.finditer(content):
            if match.group(1) in b.files:
                b.add_service_file(manager, service, match.group(1))
        for dirname in b.sources.iterkeys():
            if -1 != content.find(dirname):
                b.add_service_source(manager, service, dirname)


def _service_packages(b, manager, service, deps):
    """
    Extract files from packages on which this service depends as further
    dependencies.
    """
    if 'packages' not in deps:
        return

    # Build a map of the directory that contains each file in the
    # blueprint to the pathname of that file.
    dirs = defaultdict(list)
    for pathname in b.files:
        dirname = os.path.dirname(pathname)
        if dirname not in ('/etc', '/etc/init', '/etc/init.d'):
            dirs[dirname].append(pathname)

    # Add dependencies for every file in the blueprint that's also in
    # this service's package or in a directory in this service's package.
    for package_manager, packages in deps['packages'].iteritems():
        if 'apt' == package_manager:
            argv = ['dpkg-query', '-L']
        elif 'yum' == package_manager:
            argv = ['rpm', '-ql']
        else:
            continue
        for package in packages:
            p = subprocess.Popen(argv + [package],
                                 close_fds=True,
                                 stdout=subprocess.PIPE)
            for line in p.stdout:
                pathname = line.rstrip()
                if pathname in b.files:
                    b.add_service_file(manager, service, pathname)
                elif pathname in dirs:
                    b.add_service_file(manager, service, *dirs[pathname])


def services(b):
    logging.info('searching for service dependencies')
    for manager, services in b.services.iteritems():
        for service, deps in services.iteritems():

            # Order is important here because many files of note
            # are only discovered by the _service_packages step.
            _service_packages(b, manager, service, deps)
            _service_files(b, manager, service, deps)
