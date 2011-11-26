"""
Search for npm packages to include in the blueprint.  This assumes that
Node itself is installed via Chris Lea's PPAs, either
<https://launchpad.net/~chris-lea/+archive/node.js> or
<https://launchpad.net/~chris-lea/+archive/node.js-devel>.
"""

import logging
import re
import subprocess


def npm(b, r):
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
            if not r.ignore_package('nodejs', package):
                b.add_package('nodejs', package, version)
    except OSError:
        pass
