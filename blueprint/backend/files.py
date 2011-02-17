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

# The default list of ignore patterns.
#
# XXX Update `blueprintignore`(5) if you make changes here.
IGNORE = ('/etc/.pwd.lock',
          '/etc/alternatives',
          '/etc/apparmor',
          '/etc/apparmor.d',
          '/etc/ca-certificates.conf',
          '/etc/dpkg/origins/default', # TODO Only if it's a symbolic link to ubuntu.
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
          '/etc/motd', # TODO Only if it's a symbolic link to /var/run/motd.
          '/etc/network/interfaces',
          '/etc/passwd-',
          '/etc/passwd',
          '/etc/popularity-contest.conf',
          '/etc/resolv.conf', # Most people use the defaults.
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
          '/etc/timezone',
          '/etc/udev/rules.d/70-persistent-*.rules')

# An extra list of pathnames and MD5 sums that will be checked after no
# match is found in `dpkg`(1)'s list.  If a pathname is given as the value
# then that file's contents will be hashed.
#
# Many of these files are distributed with packages and copied from
# `/usr/share` in the `postinst` program.
#
# XXX Update `blueprintignore`(5) if you make changes here.
MD5SUMS = {'/etc/adduser.conf': '/usr/share/adduser/adduser.conf',
           '/etc/apparmor.d/tunables/home.d/ubuntu':
               '2a88811f7b763daa96c20b20269294a4',
           '/etc/chatscripts/provider': '/usr/share/ppp/provider.chatscript',
           '/etc/default/console-setup': '0fb6cec686d0410993bdf17192bee7d6',
           '/etc/default/grub': 'ee9df6805efb2a7d1ba3f8016754a119',
           '/etc/default/irqbalance': '7e10d364b9f72b11d7bf7bd1cfaeb0ff',
           '/etc/default/locale': '164aba1ef1298affaa58761647f2ceba',
           '/etc/default/rcS': '/usr/share/initscripts/default.rcS',
           '/etc/environment': '44ad415fac749e0c39d6302a751db3f2',
           '/etc/hosts.allow': '8c44735847c4f69fb9e1f0d7a32e94c1',
           '/etc/hosts.deny': '92a0a19db9dc99488f00ac9e7b28eb3d',
           '/etc/initramfs-tools/modules':
                '/usr/share/initramfs-tools/modules',
           '/etc/inputrc': '/usr/share/readline/inputrc',
           '/etc/iscsi/iscsid.conf': '6c6fd718faae84a4ab1b276e78fea471',
           '/etc/kernel-img.conf': 'f1ed9c3e91816337aa7351bdf558a442',
           '/etc/ld.so.conf': '4317c6de8564b68d628c21efa96b37e4',
           '/etc/networks': '/usr/share/base-files/networks',
           '/etc/nsswitch.conf': '/usr/share/base-files/nsswitch.conf',
           '/etc/ppp/chap-secrets': 'faac59e116399eadbb37644de6494cc4',
           '/etc/ppp/pap-secrets': '698c4d412deedc43dde8641f84e8b2fd',
           '/etc/ppp/peers/provider': '/usr/share/ppp/provider.peer',
           '/etc/profile': '/usr/share/base-files/profile',
           '/etc/python/debian_config': '7f4739eb8858d231601a5ed144099ac8',
           '/etc/rc.local': '10fd9f051accb6fd1f753f2d48371890',
           '/etc/rsyslog.d/50-default.conf':
                '/usr/share/rsyslog/50-default.conf',
           '/etc/security/opasswd': 'd41d8cd98f00b204e9800998ecf8427e',
           '/etc/sgml/xml-core.cat': 'bcd454c9bf55a3816a134f9766f5928f',
           '/etc/shells': '0e85c87e09d716ecb03624ccff511760',
           '/etc/ssh/sshd_config': 'e24f749808133a27d94fda84a89bb27b',
           '/etc/sudoers': '02f74ccbec48997f402a063a172abb48',
           '/etc/ufw/after.rules': '/usr/share/ufw/after.rules',
           '/etc/ufw/after6.rules': '/usr/share/ufw/after6.rules',
           '/etc/ufw/before.rules': '/usr/share/ufw/before.rules',
           '/etc/ufw/before6.rules': '/usr/share/ufw/before6.rules',
           '/etc/ufw/ufw.conf': '/usr/share/ufw/ufw.conf'}

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

            # Ignore files that are from the `base-files` package (which
            # doesn't include MD5 sums for every file for some reason),
            # unchanged from their packaged version, or match in `MD5SUMS`.
            package = _dpkg_query_S(pathname)
            if 'base-files' == package:
                continue
            if package is not None:
                md5sum = _dpkg_md5sum(package, pathname)
            elif pathname in MD5SUMS:
                md5sum = MD5SUMS[pathname]
                if '/' == md5sum[0]:
                    try:
                        md5sum = hashlib.md5(open(md5sum).read()).hexdigest()
                    except IOError:
                        md5sum = None
            else:
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

            # A symbolic link's content is the link target.
            if stat.S_ISLNK(s.st_mode):
                content = os.readlink(pathname)

                # Ignore symbolic links providing backwards compatibility
                # between SystemV init and Upstart.
                if '/lib/init/upstart-job' == content:
                    continue

                # Ignore symbolic links into the Debian alternatives system.
                # These are almost certainly managed by packages.
                if content.startswith('/etc/alternatives/'):
                    continue

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

def _dpkg_query_S(pathname):
    """
    Return the name of the package that contains `pathname` or `None`.
    """
    p = subprocess.Popen(['dpkg-query', '-S', pathname],
                         close_fds=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if 0 != p.returncode:

        # If `pathname` isn't in a package but is a symbolic link, see if
        # the symbolic link is in a package.  `postinst` programs commonly
        # display this pattern.
        try:
            return _dpkg_query_S(os.readlink(pathname))

        except OSError:
            return None
    package, _ = stdout.split(':')
    return package

def _dpkg_md5sum(package, pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from a Debian package.
    """
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
