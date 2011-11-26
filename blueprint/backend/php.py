"""
Search for PEAR/PECL packages to include in the blueprint.
"""

import logging
import re
import subprocess

from blueprint import util


def php(b, r):
    logging.info('searching for PEAR/PECL packages')

    # Precompile a pattern for parsing the output of `{pear,pecl} list`.
    pattern = re.compile(r'^([0-9a-zA-Z_]+)\s+([0-9][0-9a-zA-Z\.-]*)\s')

    # PEAR packages are managed by `php-pear` (obviously).  PECL packages
    # are managed by `php5-dev` because they require development headers
    # (less obvious but still makes sense).
    if util.lsb_release_codename() is None:
        pecl_manager = 'php-devel'
    else:
        pecl_manager = 'php5-dev'
    for manager, progname in (('php-pear', 'pear'),
                              (pecl_manager, 'pecl')):

        try:
            p = subprocess.Popen([progname, 'list'],
                                 close_fds=True, stdout=subprocess.PIPE)
        except OSError:
            continue
        for line in p.stdout:
            match = pattern.match(line)
            if match is None:
                continue
            package, version = match.group(1), match.group(2)
            if not r.ignore_package(manager, package):
                b.add_package(manager, package, version)
