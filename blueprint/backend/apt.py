"""
Search for `apt` packages to include in the blueprint.
"""

import logging
import os
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
