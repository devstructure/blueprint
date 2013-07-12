"""
Search for `apt` packages to include in the blueprint.
"""

import os
import logging
import subprocess

from blueprint import util


def apt(b, r):
    logging.info('searching for APT packages')

    # Define a default output format string for dpkg-query.
    output_format = '${Status}\x1E${binary:Package}\x1E${Version}\n'

    # Try running dpkg --print-foreign-architectures to see if dpkg is
    # multi-arch aware.  If not, revert to old style output_format.
    try:
        with open(os.devnull, 'w') as fnull:
            rv = subprocess.call(['dpkg', '--print-foreign-architectures'],
                                    stdout = fnull, stderr = fnull)
            if rv != 0:
                output_format = '${Status}\x1E${Package}\x1E${Version}\n'
    except OSError:
        return

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Yum/RPM-based
    # system.
    try:
        p = subprocess.Popen(['dpkg-query','-Wf', output_format],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return

    for line in p.stdout:
        status, package, version = line.strip().split('\x1E')
        if 'install ok installed' != status:
            continue
        if r.ignore_package('apt', package):
            continue

        b.add_package('apt', package, version)

        # Create service resources for each service init script or config
        # found in this package.
        p = subprocess.Popen(['dpkg-query', '-L', package],
                             close_fds=True, stdout=subprocess.PIPE)
        for line in p.stdout:
            try:
                manager, service = util.parse_service(line.rstrip())
                if not r.ignore_service(manager, service):
                    b.add_service(manager, service)
                    b.add_service_package(manager, service, 'apt', package)
            except ValueError:
                pass
