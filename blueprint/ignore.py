import fnmatch
import glob
import logging
import os.path
import re
import subprocess


# The default list of ignore patterns.
#
# XXX Update `blueprintignore`(5) if you make changes here.
IGNORE = ('*.dpkg-*',
          '/etc/.git',
          '/etc/.pwd.lock',
          '/etc/alternatives',
          '/etc/apparmor',
          '/etc/apparmor.d',
          '/etc/ca-certificates.conf',
          # TODO Only if it's a symbolic link to ubuntu.
          '/etc/dpkg/origins/default',
          '/etc/fstab',
          '/etc/group-',
          '/etc/group',
          '/etc/gshadow-',
          '/etc/gshadow',
          '/etc/hostname',
          '/etc/init.d/.legacy-bootordering',
          '/etc/initramfs-tools/conf.d/resume',
          '/etc/ld.so.cache',
          '/etc/localtime',
          '/etc/mailcap',
          '/etc/mtab',
          '/etc/modules',
          '/etc/motd',  # TODO Only if it's a symbolic link to /var/run/motd.
          '/etc/network/interfaces',
          '/etc/passwd-',
          '/etc/passwd',
          '/etc/popularity-contest.conf',
          '/etc/prelink.cache',
          '/etc/resolv.conf',  # Most people use the defaults.
          '/etc/rc.d',
          '/etc/rc0.d',
          '/etc/rc1.d',
          '/etc/rc2.d',
          '/etc/rc3.d',
          '/etc/rc4.d',
          '/etc/rc5.d',
          '/etc/rc6.d',
          '/etc/rcS.d',
          '/etc/shadow-',
          '/etc/shadow',
          '/etc/ssl/certs',
          '/etc/sysconfig/network',
          '/etc/timezone',
          '/etc/udev/rules.d/70-persistent-*.rules')


def apt_exclusions():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    CACHE = '/tmp/blueprint-apt-exclusions'
    OLDCACHE = '/tmp/blueprint-exclusions'

    # Read from a cached copy.  Move the old cache location to the new one
    # if necessary.
    try:
        os.rename(OLDCACHE, CACHE)
    except OSError:
        pass
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for apt packages to exclude')

    # Start with the root package for the various Ubuntu installations.
    s = set(['ubuntu-minimal', 'ubuntu-standard', 'ubuntu-desktop'])

    # Find the essential and required packages.  Every server's got 'em, no
    # one wants to muddle their blueprint with 'em.
    for field in ('Essential', 'Priority'):
        p = subprocess.Popen(['dpkg-query',
                              '-f=${{Package}} ${{{0}}}\n'.format(field),
                              '-W'],
                             close_fds=True, stdout=subprocess.PIPE)
        for line in p.stdout:
            try:
                package, property = line.rstrip().split()
                if property in ('yes', 'important', 'required', 'standard'):
                    s.add(package)
            except ValueError:
                pass

    # Walk the dependency tree all the way to the leaves.
    tmp_s = s
    pattern_sub = re.compile(r'\([^)]+\)')
    pattern_split = re.compile(r'[,\|]')
    while 1:
        new_s = set()
        for package in tmp_s:
            p = subprocess.Popen(
                ['dpkg-query',
                 '-f', '${Pre-Depends}\n${Depends}\n${Recommends}\n',
                 '-W', package],
                close_fds=True, stdout=subprocess.PIPE)
            for line in p.stdout:
                line = line.strip()
                if '' == line:
                    continue
                for part in pattern_split.split(pattern_sub.sub('', line)):
                    new_s.add(part.strip())

        # If there is to be a next iteration, `new_s` must contain some
        # packages not yet in `s`.
        tmp_s = new_s - s
        if 0 == len(tmp_s):
            break
        s |= new_s

    # Write to a cache.
    logging.info('caching excluded apt packages')
    f = open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s


def yum_exclusions():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    CACHE = '/tmp/blueprint-yum-exclusions'

    # Read from a cached copy.  Move the old cache location to the new one
    # if necessary.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for yum packages to exclude')

    # Start with a few groups that install common packages.
    s = set()
    pattern = re.compile(r'^   (\S+)')
    try:
        p = subprocess.Popen(['yum', 'groupinfo',
                              'core','base', 'gnome-desktop'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        open(CACHE, 'w').close()
        return s
    for line in p.stdout:
        match = pattern.match(line)
        if match is None:
            continue
        p2 = subprocess.Popen(['rpm',
                               '-q',
                               '--qf=%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}',
                               match.group(1)],
                              close_fds=True, stdout=subprocess.PIPE)
        stdout, stderr = p2.communicate()
        s.add((match.group(1), stdout))

    # Walk the dependency tree all the way to the leaves.
    tmp_s = s
    pattern = re.compile(r'provider: ([^.]+)\.\S+ (\S+)')
    while 1:
        new_s = set()
        for package, spec in tmp_s:
            p = subprocess.Popen(['yum', 'deplist', spec],
                close_fds=True, stdout=subprocess.PIPE)
            for line in p.stdout:
                match = pattern.search(line)
                if match is None:
                    continue
                new_s.add((match.group(1), '-'.join(match.group(1, 2))))

        # If there is to be a next iteration, `new_s` must contain some
        # packages not yet in `s`.
        tmp_s = new_s - s
        if 0 == len(tmp_s):
            break
        s |= new_s

    # Now that the tree has been walked, discard the version-qualified names,
    # leaving just the package names.
    s = set([package for package, spec in s])

    # Write to a cache.
    logging.info('caching excluded yum packages')
    f = open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s


# Cache things that are ignored by default first.
_cache = {
    'file': [(pattern, False) for pattern in IGNORE],
    'package': [('apt', package, False) for package in apt_exclusions()] +
                [('yum', package, False) for package in yum_exclusions()],
}

# Cache the patterns stored in the `~/.blueprintignore` file.
try:
    for pattern in open(os.path.expanduser('~/.blueprintignore')):
        pattern = pattern.rstrip()

        # Comments and blank lines.
        if '' == pattern or '#' == pattern[0]:
            continue

        # Negated lines.
        if '!' == pattern[0]:
            pattern = pattern[1:]
            ignored = True
        else:
            ignored = False

        # Normalize file resources, which don't need the : and type qualifier,
        # into the same format as others, like packages.
        if ':' == pattern[0]:
            try:
                restype, pattern = pattern[1:].split(':', 2)
            except ValueError:
                continue
        else:
            restype = 'file'
        if restype not in _cache:
            continue

        if 'file' == restype:
            _cache['file'].append((pattern, ignored))

        elif 'package' == restype:
            try:
                manager, package = pattern.split('/')
            except ValueError:
                logging.warning('invalid package ignore "{0}"'.format(pattern))
                continue
            _cache['package'].append((manager, package, False))

        else:
            logging.warning('unrecognized ignore type "{0}"'.format(restype))
            continue

except IOError:
    pass


def file(pathname, ignored=False):
    """
    Return `True` if the `gitignore`(5)-style `~/.blueprintignore` file says
    the given file should be ignored.  The starting state of the file may be
    overridden by setting `ignored` to `True`.
    """

    # Determine if the `pathname` matches the `pattern`.  `filename` is
    # given as a convenience.  See `gitignore`(5) for the rules in play.
    def match(filename, pathname, pattern):
        dir_only = '/' == pattern[-1]
        pattern = pattern.rstrip('/')
        if -1 == pattern.find('/'):
            if fnmatch.fnmatch(filename, pattern):
                return os.path.isdir(pathname) if dir_only else True
        else:
            for p in glob.glob(os.path.join('/etc', pattern)):
                if pathname == p or pathname.startswith('{0}/'.format(p)):
                    return True
        return False

    # Iterate over exclusion rules until a match is found.  Then iterate
    # over inclusion rules that appear later.  If there are no matches,
    # include the file.  If only an exclusion rule matches, exclude the
    # file.  If an inclusion rule also matches, include the file.
    filename = os.path.basename(pathname)
    for pattern, negate in _cache['file']:
        if ignored != negate or not match(filename, pathname, pattern):
            continue
        if ignored:
            return False
        else:
            ignored = True

    return ignored


def package(manager, package, ignored=False):
    """
    Iterate over package exclusion rules looking for exact matches.  As with
    files, search for a negated rule after finding a match.  Return True to
    indicate the package should be ignored.
    """
    for m, p, negate in _cache['package']:
        if ignored != negate or manager != m or package != p and '*' != p:
            continue
        if ignored:
            return False
        else:
            ignored = True
    return ignored
