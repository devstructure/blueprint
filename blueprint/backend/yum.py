"""
Search for `yum` packages to include in the blueprint.
"""

import logging
import subprocess

CACHE = '/tmp/blueprint-yum-exclusions'

def yum(b):
    logging.info('searching for yum packages')

    try:
        p = subprocess.Popen(['rpm',
                              '-qa',
                              '--qf=%{NAME}\x1E%{GROUP}\x1E%{EPOCH}' # No ,
                              '\x1E%{VERSION}-%{RELEASE}.%{ARCH}\n'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return
    for line in p.stdout:
        package, group, epoch, version = line.strip().split('\x1E')
        if '(none)' != epoch:
            version = '{0}:{1}'.format(epoch, version)
        b.packages['yum'][package].append(version)
