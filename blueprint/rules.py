from collections import defaultdict
import fnmatch
import glob
import json
import logging
import os
import os.path
import re
import subprocess

from blueprint import deps
from blueprint import util


# The default list of ignore patterns.  Typically, the value of each key
# will be False.  Providing True will negate the meaning of the pattern
# and cause matching files to be included in blueprints.
#
# XXX Update `blueprintignore`(5) if you make changes here.
IGNORE = {'*~': False,
          '*.blueprint-template.*': False,
          '*.dpkg-*': False,
          '/etc/.git': False,
          '/etc/.pwd.lock': False,
          '/etc/X11/default-display-manager': False,
          '/etc/adjtime': False,
          '/etc/alternatives': False,
          '/etc/apparmor': False,
          '/etc/apparmor.d': False,
          '/etc/blkid/blkid.tab': False,
          '/etc/ca-certificates.conf': False,
          '/etc/console-setup': False,

          # TODO Only if it's a symbolic link to ubuntu.
          '/etc/dpkg/origins/default': False,

          '/etc/fstab': False,
          '/etc/group-': False,
          '/etc/group': False,
          '/etc/gshadow-': False,
          '/etc/gshadow': False,
          '/etc/hostname': False,
          '/etc/init.d/.legacy-bootordering': False,
          '/etc/initramfs-tools/conf.d/resume': False,
          '/etc/ld.so.cache': False,
          '/etc/localtime': False,
          '/etc/lvm/cache': False,
          '/etc/mailcap': False,
          '/etc/mtab': False,
          '/etc/modules': False,

          # TODO Only if it's a symbolic link to /var/run/motd.
          '/etc/motd': False,

          '/etc/network/interfaces': False,
          '/etc/passwd-': False,
          '/etc/passwd': False,
          '/etc/pki/rpm-gpg': True,
          '/etc/popularity-contest.conf': False,
          '/etc/prelink.cache': False,
          '/etc/resolv.conf': False,  # Most people use the defaults.
          '/etc/rc.d': False,
          '/etc/rc0.d': False,
          '/etc/rc1.d': False,
          '/etc/rc2.d': False,
          '/etc/rc3.d': False,
          '/etc/rc4.d': False,
          '/etc/rc5.d': False,
          '/etc/rc6.d': False,
          '/etc/rcS.d': False,
          '/etc/shadow-': False,
          '/etc/shadow': False,
          '/etc/ssh/ssh_host_key*': False,
          '/etc/ssh/ssh_host_*_key*': False,
          '/etc/ssl/certs': False,
          '/etc/sysconfig/clock': False,
          '/etc/sysconfig/i18n': False,
          '/etc/sysconfig/keyboard': False,
          '/etc/sysconfig/network': False,
          '/etc/sysconfig/network-scripts': False,
          '/etc/timezone': False,
          '/etc/udev/rules.d/70-persistent-*.rules': False,
          '/etc/yum.repos.d': True}


CACHE = '/tmp/blueprintignore'


def defaults():
    """
    Parse `/etc/blueprintignore` and `~/.blueprintignore` to build the
    default `Rules` object.
    """
    r = None

    # Check for a fresh cache of the complete blueprintignore(5) rules.
    if _mtime('/etc/blueprintignore') < _mtime(CACHE) \
    and _mtime(os.path.expanduser('~/.blueprintignore')) < _mtime(CACHE) \
    and _mtime(__file__) < _mtime(CACHE):
        try:
            r = Rules(json.load(open(CACHE)))
            logging.info('using cached blueprintignore(5) rules')
            return r
        except (OSError, ValueError):
            pass

    # Cache things that are ignored by default first.
    r = Rules({
        'file': IGNORE.items(),
        'package': [('apt', package, False) for package in _apt()] +
                   [('yum', package, False) for package in _yum()],
        'service': [('sysvinit', 'skeleton', False)],
        'source': [('/', False),
                   ('/usr/local', True)],
    })

    # Cache the patterns stored in the blueprintignore files.
    logging.info('parsing blueprintignore(5) rules')
    try:
        for pathname in ['/etc/blueprintignore',
                         os.path.expanduser('~/.blueprintignore')]:
            r.parse(open(pathname), negate=True)

    except IOError:
        pass

    # Store the cache to disk.
    f = _cache_open(CACHE, 'w')
    json.dump(r, f, indent=2, sort_keys=True)
    f.close()

    return r


def none():
    """
    Build a `Rules` object that ignores every resource.
    """
    return Rules({'file': [('*', False)],
                  'package': [('*', '*', False)],
                  'service': [('*', '*', False)],
                  'source': [('/', False)]})


def _apt():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    CACHE = '/tmp/blueprint-apt-exclusions'

    # Read from a cached copy.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for APT packages to exclude')

    # Start with the root packages for the various Ubuntu installations.
    s = set(['grub-pc',
             'installation-report',
             'language-pack-en',
             'language-pack-gnome-en',
             'linux-generic-pae',
             'linux-server',
             'os-prober',
             'ubuntu-desktop',
             'ubuntu-minimal',
             'ubuntu-standard',
             'wireless-crda'])

    # Find the essential and required packages.  Every server's got 'em, no
    # one wants to muddle their blueprint with 'em.
    for field in ('Essential', 'Priority'):
        try:
            p = subprocess.Popen(['dpkg-query',
                                  '-f=${{Package}} ${{{0}}}\n'.format(field),
                                  '-W'],
                                 close_fds=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except OSError:
            _cache_open(CACHE, 'w').close()
            return s
        for line in p.stdout:
            try:
                package, property = line.rstrip().split()
                if property in ('yes', 'important', 'required', 'standard'):
                    s.add(package)
            except ValueError:
                pass

    # Walk the dependency tree all the way to the leaves.
    s = deps.apt(s)

    # Write to a cache.
    logging.info('caching excluded APT packages')
    f = _cache_open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s


def _yum():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    CACHE = '/tmp/blueprint-yum-exclusions'

    # Read from a cached copy.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for Yum packages to exclude')

    # Start with a few groups that install common packages.
    s = set(['gpg-pubkey'])
    pattern = re.compile(r'^   (\S+)')
    try:
        p = subprocess.Popen(['yum', 'groupinfo',
                              'core','base', 'gnome-desktop'],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        _cache_open(CACHE, 'w').close()
        return s
    for line in p.stdout:
        match = pattern.match(line)
        if match is not None:
            s.add(match.group(1))

    # Walk the dependency tree all the way to the leaves.
    s = deps.yum(s)

    # Write to a cache.
    logging.info('caching excluded Yum packages')
    f = _cache_open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s


def _cache_open(pathname, mode):
    f = open(pathname, mode)
    if util.via_sudo():
        uid = int(os.environ['SUDO_UID'])
        gid = int(os.environ['SUDO_GID'])
        os.fchown(f.fileno(), uid, gid)
    return f


def _mtime(pathname):
    try:
        return os.stat(pathname).st_mtime
    except OSError:
        return 0


class Rules(defaultdict):
    """
    Ordered lists of rules for ignoring/unignoring particular resources.
    This is used for both `blueprintignore`(5) and `blueprint-rules`(1).
    """

    def __init__(self, *args, **kwargs):
        super(Rules, self).__init__(list, *args, **kwargs)

    def _ignore_pathname(self, restype, dirname, pathname, ignored=False):
        """
        Return `True` if the `gitignore`(5)-style `~/.blueprintignore`
        file says the given file should be ignored.  The starting state
        of the file may be overridden by setting `ignored` to `True`.
        """
        pathname = util.unicodeme(pathname)

        # Determine if the `pathname` matches the `pattern`.  `filename` is
        # given as a convenience.  See `gitignore`(5) for the rules in play.
        def match(filename, pathname, pattern):
            dir_only = '/' == pattern[-1]
            pattern = pattern.rstrip('/')
            if '/' not in pattern:
                if fnmatch.fnmatch(filename, pattern):
                    return os.path.isdir(pathname) if dir_only else True
            else:
                for p in glob.glob(os.path.join(dirname, pattern)):
                    p = util.unicodeme(p)
                    if pathname == p or pathname.startswith('{0}/'.format(p)):
                        return os.path.isdir(pathname) if dir_only else True
            return False

        # Iterate over exclusion rules until a match is found.  Then iterate
        # over inclusion rules that appear later.  If there are no matches,
        # include the file.  If only an exclusion rule matches, exclude the
        # file.  If an inclusion rule also matches, include the file.
        filename = os.path.basename(pathname)
        for pattern, negate in self[restype]:
            if ignored != negate or not match(filename, pathname, pattern):
                continue
            ignored = not ignored

        return ignored

    def ignore_file(self, pathname, ignored=False):
        """
        Return `True` if the given pathname should be ignored.
        """
        return self._ignore_pathname('file', '/etc', pathname, ignored)

    def ignore_package(self, manager, package, ignored=False):
        """
        Iterate over package exclusion rules looking for exact matches. As
        with files, search for a negated rule after finding a match. Return
        `True` to indicate the package should be ignored.
        """
        for m, p, negate in self['package']:
            if ignored != negate \
            or manager != m and '*' != m \
            or package != p and '*' != p:
                continue
            ignored = not ignored
        return ignored

    def ignore_service(self, manager, service, ignored=False):
        """
        Return `True` if a given service should be ignored.
        """
        for m, s, negate in self['service']:
            if ignored != negate \
            or manager != m and '*' != m \
            or service != s and '*' != s:
                continue
            ignored = not ignored
        return ignored

    def ignore_source(self, pathname, ignored=False):
        """
        Return `True` if the given pathname should be ignored.  Negated rules
        on directories will create new source tarballs.  Other rules will
        ignore files within those tarballs.
        """
        return self._ignore_pathname('source', '/', pathname, ignored)


    def parse(self, f, negate=False):
        """
        Parse rules from the given file-like object.  This is used both for
        `blueprintignore`(5) and for `blueprint-rules`(1).
        """
        for pattern in f:
            pattern = pattern.rstrip()

            # Comments and blank lines.
            if '' == pattern or '#' == pattern[0]:
                continue

            # Negated lines.
            if '!' == pattern[0]:
                pattern = pattern[1:]
                ignored = negate
            else:
                ignored = not negate

            # Normalize file resources, which don't need the : and type
            # qualifier, into the same format as others, like packages.
            if ':' == pattern[0]:
                try:
                    restype, pattern = pattern[1:].split(':', 2)
                except ValueError:
                    continue
            else:
                restype = 'file'

            # Ignore a package and its dependencies or unignore a single
            # package.  Empirically, the best balance of power and
            # granularity comes from this arrangement.  Take
            # build-esseantial's mutual dependence with dpkg-dev as an
            # example of why.
            if 'package' == restype:
                try:
                    manager, package = pattern.split('/')
                except ValueError:
                    logging.warning('invalid package rule "{0}"'.
                                    format(pattern))
                    continue
                self['package'].append((manager, package, ignored))
                if not ignored:
                    for dep in getattr(deps,
                                       manager,
                                       lambda(arg): [])(package):
                        self['package'].append((manager, dep, ignored))

            elif 'service' == restype:
                try:
                    manager, service = pattern.split('/')
                except ValueError:
                    logging.warning('invalid service rule "{0}"'.
                                    format(pattern))
                    continue
                self['service'].append((manager, service, ignored))

            # Ignore or unignore a file, glob, or directory tree.
            else:
                self[restype].append((pattern, ignored))

        return self
