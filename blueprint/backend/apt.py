"""
Search for `apt` packages to include in the blueprint.
"""

import logging
import subprocess

from blueprint import ignore


def apt(b):
    logging.info('searching for APT packages')

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Yum/RPM-based
    # system.
    try:
        p = subprocess.Popen(['dpkg-query',
                              '-f=${Package} ${Version}\n',
                              '-W'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return

    for line in p.stdout:
        package, version = line.strip().split()
        if ignore.package('apt', package):
            continue

        b.packages['apt'][package].append(version)

        # Create service resources for each service in this package.
        p = subprocess.Popen(['dpkg-query', '-L', package],
                             close_fds=True, stdout=subprocess.PIPE)
        for line in p.stdout:
            b.add_service(line.rstrip(), packages=[package])
