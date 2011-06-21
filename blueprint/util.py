"""
Utility functions.
"""

import json
import os
import os.path
import re
import subprocess


def arch():
    """
    Return the system's architecture according to dpkg or rpm.
    """
    try:
        p = subprocess.Popen(['dpkg', '--print-architecture'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError as e:
        p = subprocess.Popen(['rpm', '--eval', '%_arch'],
                             close_fds=True, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        return None
    return stdout.rstrip()


def lsb_release_codename():
    """
    Return the OS release's codename.
    """
    if hasattr(lsb_release_codename, '_cache'):
        return lsb_release_codename._cache
    try:
        p = subprocess.Popen(['lsb_release', '-c'], stdout=subprocess.PIPE)
    except OSError:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    match = re.search(r'\t(\w+)$', stdout)
    if match is None:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    lsb_release_codename._cache = match.group(1)
    return lsb_release_codename._cache


def parse_service(pathname):
    """
    Parse a potential service init script or config file into the
    manager and service name or raise `ValueError`.
    """
    dirname, basename = os.path.split(pathname)
    if '/etc/init' == dirname:
        service, ext = os.path.splitext(basename)
        if '.conf' != ext:
            raise ValueError("not an Upstart config")
        return ('upstart', service)
    elif '/etc/init.d' == dirname \
        and (not os.path.islink(pathname) \
        or '/lib/init/upstart-job' != os.readlink(pathname)):
        return ('sysvinit', basename)
    else:
        raise ValueError("not a service")


def rubygems_update():
    """
    Determine whether the `rubygems-update` gem is needed.  It is needed
    on Lucid and older systems.
    """
    codename = lsb_release_codename()
    return codename is not None and codename[0] < 'm'


def rubygems_virtual():
    """
    Determine whether RubyGems is baked into the Ruby 1.9 distribution.
    It is on Maverick and newer systems.
    """
    codename = lsb_release_codename()
    return codename is not None and codename[0] >= 'm'


def rubygems_path():
    """
    Determine based on the OS release where RubyGems will install gems.
    """
    if lsb_release_codename() is None or rubygems_update():
        return '/usr/lib/ruby/gems'
    return '/var/lib/gems'


def via_sudo():
    """
    Return `True` if Blueprint was invoked via `sudo`(8), which indicates
    that privileges must be dropped when writing to the filesystem.
    """
    return 'SUDO_UID' in os.environ \
        and 'SUDO_GID' in os.environ \
        and -1 != os.environ.get('SUDO_COMMAND', '').find('blueprint')


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super(JSONEncoder, self).default(o)
