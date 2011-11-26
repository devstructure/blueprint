"""
Search for `apt` packages to include in the blueprint.
"""

import logging
import subprocess

from blueprint import util


def apt(b, r):
    logging.info('searching for APT packages')

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Yum/RPM-based
    # system.
    try:
        p = subprocess.Popen(['dpkg-query',
                              '-f=${Status}\x1E${Package}\x1E${Version}\n',
                              '-W'],
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
