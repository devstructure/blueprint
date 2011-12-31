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


# Patterns for determining which Upstart services should be included, based
# on the events used to start them.
pattern_upstart_1 = re.compile(r'start\s+on\s+runlevel\s+\[[2345]', re.S)
pattern_upstart_2 = re.compile(r'start\s+on\s+\([^)]*(?:filesystem|filesystems|local-filesystems|mounted|net-device-up|remote-filesystems|startup|virtual-filesystems)[^)]*\)', re.S)


def parse_service(pathname):
    """
    Parse a potential service init script or config file into the
    manager and service name or raise `ValueError`.  Use the Upstart
    "start on" stanzas and SysV init's LSB headers to restrict services to
    only those that start at boot and run all the time.
    """
    dirname, basename = os.path.split(pathname)
    if '/etc/init' == dirname:
        service, ext = os.path.splitext(basename)

        # Ignore extraneous files in /etc/init.
        if '.conf' != ext:
            raise ValueError('not an Upstart config')

        # Ignore services that don't operate on the (faked) main runlevels.
        try:
            content = open(pathname).read()
        except IOError:
            raise ValueError('not a readable Upstart config')
        if not (pattern_upstart_1.search(content) \
                or pattern_upstart_2.search(content)):
            raise ValueError('not a running service')

        return ('upstart', service)
    elif '/etc/init.d' == dirname or '/etc/rc.d/init.d' == dirname:

        # Let Upstart handle its services.
        if os.path.islink(pathname) \
            and '/lib/init/upstart-job' == os.readlink(pathname):
            raise ValueError('proxy for an Upstart config')

        # Ignore services that don't operate on the main runlevels.
        try:
            content = open(pathname).read()
        except IOError:
            raise ValueError('not a readable SysV init script')
        if not re.search(r'(?:Default-Start|chkconfig):\s*[2345]', content):
            raise ValueError('not a running service')

        return ('sysvinit', basename)
    else:
        raise ValueError('not a service')


def rubygems_unversioned():
    """
    Determine whether RubyGems is suffixed by the Ruby language version.
    It ceased to be on Oneiric.  It always has been on RPM-based distros.
    """
    codename = lsb_release_codename()
    return codename is None or codename[0] >= 'o'


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
        and 'blueprint' in os.environ.get('SUDO_COMMAND', '')


class BareString(unicode):
    """
    Strings of this type will not be quoted when written into a Puppet
    manifest or Chef cookbook.
    """
    pass


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super(JSONEncoder, self).default(o)

def json_dumps(o):
    return JSONEncoder(indent=2, sort_keys=True).encode(o)


def unicodeme(s):
    if isinstance(s, unicode):
        return s
    for encoding in ('utf_8', 'latin_1'):
        try:
            return unicode(s, encoding)
        except UnicodeDecodeError:
            pass
    # TODO Issue a warning?
    return s
