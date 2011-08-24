"""
Search for npm packages to include in the blueprint.
"""

import logging
import re
import subprocess

from blueprint import util
from blueprint import ignore


def npm(b):
    logging.info('searching for npm packages')

    # Precompile a pattern for parsing the output of `{pear,pecl} list`.
    pattern = re.compile(r'^\S+ (\S+)@(\S+)$')

    try:
        p = subprocess.Popen(['npm', 'ls', '-g'],
                             close_fds=True,
                             stdout=subprocess.PIPE)
        for line in p.stdout:
            match = pattern.match(line.rstrip())
            if match is None:
                continue
            package, version = match.group(1), match.group(2)
            b.add_package('npm', package, version)
    except OSError:
        pass
