"""
Search for PEAR/PECL packages to include in the blueprint.
"""

import logging
import re
import subprocess

def php(b):
    logging.info('searching for PEAR/PECL packages')

    # Precompile a pattern for parsing the output of `{pear,pecl} list`.
    pattern = re.compile(r'^([0-9a-zA-Z_]+)\s+([0-9][0-9a-zA-Z\.-]*)\s')

    # PEAR packages are managed by `php-pear` (obviously).  PECL packages
    # are managed by `php5-dev` because they require development headers
    # (less obvious but still makes sense).
    for manager, progname in (('php-pear', 'pear'),
                              ('php5-dev', 'pecl')):

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
            b.packages[manager][package].append(version)
