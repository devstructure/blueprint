"""
Search for configuration files to include in the blueprint.
"""

import base64
import fnmatch
import glob
import grp
import hashlib
import logging
import os.path
import pwd
import stat
import subprocess

EXCLUDE = ('/etc/alternatives',
           '/etc/group-',
           '/etc/group',
           '/etc/gshadow-',
           '/etc/gshadow',
           '/etc/ld.so.cache',
           '/etc/mtab',
           '/etc/passwd-',
           '/etc/passwd',
           '/etc/rc0.d',
           '/etc/rc1.d',
           '/etc/rc2.d',
           '/etc/rc3.d',
           '/etc/rc4.d',
           '/etc/rc5.d',
           '/etc/rc6.d',
           '/etc/rcS.d',
           '/etc/shadow-',
           '/etc/shadow')

def files(b):
    logging.info('searching for configuration files')

    # Visit every file in `/etc` except those on the exclusion list above.
    for dirpath, dirnames, filenames in os.walk('/etc'):

        # Don't even bother recursing into hard-coded excluded directories.
        if dirpath in EXCLUDE:
            del dirnames[:]
            continue

        # Determine if this entire directory should be ignored by default.
        # FIXME This doesn't actually work right without a recursive
        # implementation.  (Ignoring /foo won't currently affect /foo/bar.)
        ignored = _ignore(os.path.basename(dirpath), dirpath)

        for filename in filenames:
            pathname = os.path.join(dirpath, filename)

            # Ignore hard-coded excluded files.
            if pathname in EXCLUDE:
                continue

            # Ignore files that match in the `gitignore`(5)-style
            # `~/.blueprintignore` file.
            if _ignore(filename, pathname, ignored=ignored):
                continue

            # The content is used even for symbolic links to determine whether
            # it has changed from the packaged version.
            try:
                content = open(pathname).read()
            except IOError:
                #logging.warning('{0} not readable'.format(pathname))
                continue

            # Don't store files which are part of a package and are unchanged
            # from the distribution.
            if hashlib.md5(content).hexdigest() == _md5(pathname):
                if _ignore(filename, pathname, ignored=True):
                    continue

            # Don't store DevStructure's default `/etc/fuse.conf`.  (This is
            # a legacy condition.)
            if '/etc/fuse.conf' == pathname:
                try:
                    if 'user_allow_other\n' == open(pathname).read():
                        if _ignore(filename, pathname, ignored=True):
                            continue
                except IOError:
                    pass

            s = os.lstat(pathname)

            # A symbolic link's content is the link target.
            if stat.S_ISLNK(s.st_mode):
                content = os.readlink(pathname)
                encoding = 'plain'

            # A regular file is stored as plain text only if it is valid
            # UTF-8, which is required for JSON serialization.
            elif stat.S_ISREG(s.st_mode):
                try:
                    content.decode('UTF-8')
                    encoding = 'plain'
                except UnicodeDecodeError:
                    content = base64.b64encode(content)
                    encoding = 'base64'

            # Other types, like FIFOs and sockets are not supported within
            # a blueprint and really shouldn't appear in `/etc` at all.
            else:
                logging.warning('{0} is not a regular file or symbolic link'
                                ''.format(pathname))
                continue

            pw = pwd.getpwuid(s.st_uid)
            gr = grp.getgrgid(s.st_gid)
            b.files[pathname] = dict(content=content,
                                     encoding=encoding,
                                     group=gr.gr_name,
                                     mode='{0:o}'.format(s.st_mode),
                                     owner=pw.pw_name)

def _ignore(filename, pathname, ignored=False):
    """
    Return `True` if the `gitignore`(5)-style `~/.blueprintignore` file says
    the given file should be ignored.  The starting state of the file may be
    overridden by setting `ignored` to `True`.

    This accepts the filename as well as the pathname so as to avoid
    unnecessary O(n) string manipulations in a loop that traverses the
    entire `/etc` tree of the filesystem.
    """

    # Cache the patterns stored in the `~/.blueprintignore` file.
    if not hasattr(_ignore, '_cache'):
        _ignore._cache = []
        try:
            for pattern in open(os.path.expanduser('~/.blueprintignore')):
                pattern = pattern.rstrip()
                if '' == pattern or '#' == pattern[0]:
                    continue
                if '!' == pattern[0]:
                    _ignore._cache.append((pattern[1:], True))
                else:
                    _ignore._cache.append((pattern, False))
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
    for pattern, negate in _ignore._cache:
        if ignored != negate:
            continue
        if ignored:
            if match(filename, pathname, pattern):
                return False
        else:
            ignored = match(filename, pathname, pattern)

    return ignored

def _md5(pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from a Debian package.
    """
    p = subprocess.Popen(['dpkg-query', '-S', pathname],
                         close_fds=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        return None
    package, _ = stdout.split(':')
    try:
        for line in open('/var/lib/dpkg/info/{0}.md5sums'.format(package)):
            if line.endswith('{0}\n'.format(pathname[1:])):
                return line[0:32]
    except IOError:
        pass
    try:
        for line in open('/var/lib/dpkg/status'):
            if line.startswith(' {0} '.format(pathname)):
                return line[-33:-1]
    except IOError:
        pass
    return None
