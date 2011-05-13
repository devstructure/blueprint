import fnmatch
import glob
import os.path

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

def ignore(pathname, ignored=False):
    """
    Return `True` if the `gitignore`(5)-style `~/.blueprintignore` file says
    the given file should be ignored.  The starting state of the file may be
    overridden by setting `ignored` to `True`.
    """

    # Cache the patterns stored in the `~/.blueprintignore` file.
    if not hasattr(ignore, '_cache'):
        ignore._cache = [(pattern, False) for pattern in IGNORE]
        try:
            for pattern in open(os.path.expanduser('~/.blueprintignore')):
                pattern = pattern.rstrip()
                if '' == pattern or '#' == pattern[0]:
                    continue
                if '!' == pattern[0]:
                    ignore._cache.append((pattern[1:], True))
                else:
                    ignore._cache.append((pattern, False))
        except IOError:
            pass

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
    for pattern, negate in ignore._cache:
        if ignored != negate:
            continue
        if ignored:
            if match(filename, pathname, pattern):
                return False
        else:
            ignored = match(filename, pathname, pattern)

    return ignored
