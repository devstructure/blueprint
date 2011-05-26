"""
Search for `yum` packages to include in the blueprint.
"""

import logging
import subprocess

from blueprint import ignore


def yum(b):
    logging.info('searching for Yum packages')

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Debian-based
    # system.
    try:
        p = subprocess.Popen(['rpm',
                              '--qf=%{NAME}\x1E%{GROUP}\x1E%{EPOCH}' # No ,
                              '\x1E%{VERSION}-%{RELEASE}\x1E%{ARCH}\n',
                              '-qa'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return

    for line in p.stdout:
        package, group, epoch, version, arch = line.strip().split('\x1E')
        if ignore.package('yum', package):
            continue
        if '(none)' != epoch:
            version = '{0}:{1}'.format(epoch, version)
        if '(none)' != arch:
            version = '{0}.{1}'.format(version, arch)
        b.packages['yum'][package].append(version)
