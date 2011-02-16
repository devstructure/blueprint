"""
Search for configuration files to include in the blueprint.
"""

import base64
from collections import defaultdict
import fnmatch
import glob
import grp
import hashlib
import logging
import os.path
import pwd
import stat
import subprocess

# The default list of ignore patterns.  Update `blueprintignore`(5) if you
# make changes here.
IGNORE = ('/etc/alternatives',
          '/etc/apparmor.d/cache',
          '/etc/ca-certificates.conf',
          '/etc/group-',
          '/etc/group',
          '/etc/gshadow-',
          '/etc/gshadow',
          '/etc/initramfs-tools/conf.d/resume',
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

# An extra list of pathnames and MD5 sums that will be checked after no
# match is found in `dpkg`(1)'s list.  If a pathname is given as the value
# then that file's contents will be hashed.
MD5SUMS = {'/etc/apparmor.d/tunables/home.d/ubuntu':
               '2a88811f7b763daa96c20b20269294a4',
           '/etc/iscsi/iscsid.conf': '6c6fd718faae84a4ab1b276e78fea471',
           '/etc/ppp/peers/provider': '/usr/share/ppp/provider.peer',
           '/etc/python/debian_config': '7f4739eb8858d231601a5ed144099ac8'}

def files(b):
    logging.info('searching for configuration files')

    # Visit every file in `/etc` except those on the exclusion list above.
    for dirpath, dirnames, filenames in os.walk('/etc'):

        # Determine if this entire directory should be ignored by default.
        ignored = _ignore(os.path.basename(dirpath), dirpath)

        # Track the ctime of each file in this directory.  Weed out false
        # positives by ignoring files with common ctimes.
        ctimes = defaultdict(lambda: 0)

        # Collect up the full pathname to each file and `lstat` them all.
        files = [(pathname, os.lstat(pathname))
                 for pathname in [os.path.join(dirpath, filename)
                                  for filename in filenames]]

        # Map the ctimes of each directory entry.
        for pathname, s in files:
            ctimes[s.st_ctime] += 1
        for dirname in dirnames:
            ctimes[os.lstat(os.path.join(dirpath, dirname)).st_ctime] += 1

        for pathname, s in files:

            # Ignore files that match in the `gitignore`(5)-style
            # `~/.blueprintignore` file.  Default to ignoring files that
            # share their ctime with other files in the directory.  This
            # is a very strong indication that the file is original to
            # the system and should be ignored.
            if _ignore(filename,
                       pathname,
                       ignored=ignored or 1 < ctimes[s.st_ctime]):
                continue

            # The content is used even for symbolic links to determine whether
            # it has changed from the packaged version.
            try:
                content = open(pathname).read()
            except IOError:
                #logging.warning('{0} not readable'.format(pathname))
                continue

            # Ignore files that are unchanged from their packaged version
            # or match in the `MD5SUMS` dict.
            md5sum = _dpkg_md5sum(pathname)
            if md5sum is None and pathname in MD5SUMS:
                md5sum = MD5SUMS[pathname]
                if '/' == md5sum[0]:
                    try:
                        md5sum = hashlib.md5(open(md5sum).read()).hexdigest()
                    except IOError:
                        md5sum = None
            if hashlib.md5(content).hexdigest() == md5sum:
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

            # At this point, it's almost certain the file is going to be
            # included in the blueprint.

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
        _ignore._cache = [(pattern, False) for pattern in IGNORE]
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

def _dpkg_md5sum(pathname):
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
