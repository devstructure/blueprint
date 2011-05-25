"""
Search for configuration files to include in the blueprint.
"""

import base64
from collections import defaultdict
import errno
import glob
import grp
import hashlib
import logging
import os.path
import pwd
import re
import stat
import subprocess

from blueprint import ignore


# An extra list of pathnames and MD5 sums that will be checked after no
# match is found in `dpkg`(1)'s list.  If a pathname is given as the value
# then that file's contents will be hashed.
#
# Many of these files are distributed with packages and copied from
# `/usr/share` in the `postinst` program.
#
# XXX Update `blueprintignore`(5) if you make changes here.
MD5SUMS = {'/etc/adduser.conf': ['/usr/share/adduser/adduser.conf'],
           '/etc/apparmor.d/tunables/home.d/ubuntu':
               ['2a88811f7b763daa96c20b20269294a4'],
           '/etc/chatscripts/provider': ['/usr/share/ppp/provider.chatscript'],
           '/etc/default/console-setup':
               ['0fb6cec686d0410993bdf17192bee7d6',
                'b684fd43b74ac60c6bdafafda8236ed3',
                '/usr/share/console-setup/console-setup'],
           '/etc/default/grub': ['ee9df6805efb2a7d1ba3f8016754a119',
                                 'ad9283019e54cedfc1f58bcc5e615dce'],
           '/etc/default/irqbalance': ['7e10d364b9f72b11d7bf7bd1cfaeb0ff'],
           '/etc/default/keyboard': ['06d66484edaa2fbf89aa0c1ec4989857'],
           '/etc/default/locale': ['164aba1ef1298affaa58761647f2ceba',
                                   '7c32189e775ac93487aa4a01dffbbf76'],
           '/etc/default/rcS': ['/usr/share/initscripts/default.rcS'],
           '/etc/environment': ['44ad415fac749e0c39d6302a751db3f2'],
           '/etc/hosts.allow': ['8c44735847c4f69fb9e1f0d7a32e94c1'],
           '/etc/hosts.deny': ['92a0a19db9dc99488f00ac9e7b28eb3d'],
           '/etc/initramfs-tools/modules':
                ['/usr/share/initramfs-tools/modules'],
           '/etc/inputrc': ['/usr/share/readline/inputrc'],
           '/etc/iscsi/iscsid.conf': ['6c6fd718faae84a4ab1b276e78fea471'],
           '/etc/kernel-img.conf': ['f1ed9c3e91816337aa7351bdf558a442'],
           '/etc/ld.so.conf': ['4317c6de8564b68d628c21efa96b37e4'],
           '/etc/networks': ['/usr/share/base-files/networks'],
           '/etc/nsswitch.conf': ['/usr/share/base-files/nsswitch.conf'],
           '/etc/ppp/chap-secrets': ['faac59e116399eadbb37644de6494cc4'],
           '/etc/ppp/pap-secrets': ['698c4d412deedc43dde8641f84e8b2fd'],
           '/etc/ppp/peers/provider': ['/usr/share/ppp/provider.peer'],
           '/etc/profile': ['/usr/share/base-files/profile'],
           '/etc/python/debian_config': ['7f4739eb8858d231601a5ed144099ac8'],
           '/etc/rc.local': ['10fd9f051accb6fd1f753f2d48371890'],
           '/etc/rsyslog.d/50-default.conf':
                ['/usr/share/rsyslog/50-default.conf'],
           '/etc/security/opasswd': ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/sgml/xml-core.cat': ['bcd454c9bf55a3816a134f9766f5928f'],
           '/etc/shells': ['0e85c87e09d716ecb03624ccff511760'],
           '/etc/ssh/sshd_config': ['e24f749808133a27d94fda84a89bb27b',
                                    '8caefdd9e251b7cc1baa37874149a870'],
           '/etc/sudoers': ['02f74ccbec48997f402a063a172abb48'],
           '/etc/ufw/after.rules': ['/usr/share/ufw/after.rules'],
           '/etc/ufw/after6.rules': ['/usr/share/ufw/after6.rules'],
           '/etc/ufw/before.rules': ['/usr/share/ufw/before.rules'],
           '/etc/ufw/before6.rules': ['/usr/share/ufw/before6.rules'],
           '/etc/ufw/ufw.conf': ['/usr/share/ufw/ufw.conf']}


def files(b):
    logging.info('searching for configuration files')

    # Visit every file in `/etc` except those on the exclusion list above.
    for dirpath, dirnames, filenames in os.walk('/etc'):

        # Determine if this entire directory should be ignored by default.
        ignored = ignore.file(dirpath)

        # Track the ctime of each file in this directory.  Weed out false
        # positives by ignoring files with common ctimes.
        ctimes = defaultdict(lambda: 0)

        # Collect up the full pathname to each file and `lstat` them all.
        files = []
        for filename in filenames:
            pathname = os.path.join(dirpath, filename)
            try:
                files.append((pathname, os.lstat(pathname)))
            except OSError as e:
                logging.warning('{0} caused {1} - try running as root'
                                ''.format(pathname, errno.errorcode[e.errno]))

        # Map the ctimes of each directory entry.
        for pathname, s in files:
            ctimes[s.st_ctime] += 1
        for dirname in dirnames:
            try:
                ctimes[os.lstat(os.path.join(dirpath, dirname)).st_ctime] += 1
            except OSError:
                pass

        for pathname, s in files:

            # Ignore files that match in the `gitignore`(5)-style
            # `~/.blueprintignore` file.  Default to ignoring files that
            # share their ctime with other files in the directory.  This
            # is a very strong indication that the file is original to
            # the system and should be ignored.
            if ignore.file(pathname, ignored or 1 < ctimes[s.st_ctime]):
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
            # are unchanged from their packaged version, or match in `MD5SUMS`.
            packages = _dpkg_query_S(pathname) + _rpm_qf(pathname)
            if 'base-files' in packages:
                continue
            if 0 < len(packages):
                md5sums = [_dpkg_md5sum(package, pathname)
                           for package in packages]
                # TODO Equivalent checksumming for RPMs.
            elif pathname in MD5SUMS:
                md5sums = MD5SUMS[pathname]
                for i in range(len(md5sums)):
                    if '/' != md5sums[i][0]:
                        continue
                    try:
                        md5sums[i] = hashlib.md5(open(
                            md5sums[i]).read()).hexdigest()
                    except IOError:
                        pass
            else:
                md5sums = []
            if 0 < len(md5sums) \
                and hashlib.md5(content).hexdigest() in md5sums \
                and ignore.file(pathname, True):
                continue
            if True in [_rpm_V(package, pathname) and ignore.file(pathname,
                                                                  True)
                        for package in packages]:
                continue

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
                    content = content.decode('UTF-8')
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

            try:
                pw = pwd.getpwuid(s.st_uid)
                owner = pw.pw_name
            except KeyError:
                owner = s.st_uid
            try:
                gr = grp.getgrgid(s.st_gid)
                group = gr.gr_name
            except KeyError:
                group = s.st_gid
            b.files[pathname] = dict(content=content,
                                     encoding=encoding,
                                     group=group,
                                     mode='{0:o}'.format(s.st_mode),
                                     owner=owner)


def _dpkg_query_S(pathname):
    """
    Return a list of package names that contain `pathname` or `[]`.  This
    really can be a list thanks to `dpkg-divert`(1).
    """

    # Cache the pathname-to-package mapping.
    if not hasattr(_dpkg_query_S, '_cache'):
        _dpkg_query_S._cache = defaultdict(set)
        cache_ref = _dpkg_query_S._cache
        for listname in glob.iglob('/var/lib/dpkg/info/*.list'):
            package = os.path.splitext(os.path.basename(listname))[0]
            for line in open(listname):
                cache_ref[line.rstrip()].add(package)

    # Return the list of packages that contain this file, if any.
    if pathname in _dpkg_query_S._cache:
        return list(_dpkg_query_S._cache[pathname])

    # If `pathname` isn't in a package but is a symbolic link, see if the
    # symbolic link is in a package.  `postinst` programs commonly display
    # this pattern.
    try:
        return _dpkg_query_S(os.readlink(pathname))
    except OSError:
        pass

    return []


def _dpkg_md5sum(package, pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from a Debian package.
    """

    # Cache the MD5 sums for files in this package.
    if not hasattr(_dpkg_md5sum, '_cache'):
        _dpkg_md5sum._cache = defaultdict(dict)
    if package not in _dpkg_md5sum._cache:
        cache_ref = _dpkg_md5sum._cache[package]
        try:
            for line in open('/var/lib/dpkg/info/{0}.md5sums'.format(package)):
                md5sum, rel_pathname = line.split(None, 1)
                cache_ref['/{0}'.format(rel_pathname)] = md5sum
        except IOError:
            pass

    # Return this file's MD5 sum, if it can be found.
    try:
        return _dpkg_md5sum._cache[package][pathname]
    except KeyError:
        pass

    # Cache any MD5 sums stored in the status file.  These are typically
    # conffiles and the like.
    if not hasattr(_dpkg_md5sum, '_status_cache'):
        _dpkg_md5sum._status_cache = {}
        cache_ref = _dpkg_md5sum._status_cache
        try:
            pattern = re.compile(r'^ (\S+) ([0-9a-f]{32})')
            for line in open('/var/lib/dpkg/status'):
                match = pattern.match(line)
                if not match:
                    continue
                cache_ref[match.group(1)] = match.group(2)
        except IOError:
            pass

    # Return this file's MD5 sum, if it can be found.
    try:
        return _dpkg_md5sum._status_cache[pathname]
    except KeyError:
        pass

    return None


def _rpm_qf(pathname):
    """
    Return a list of package names that contain `pathname` or `[]`.  RPM
    might not actually support a single pathname being claimed by more
    than one package but `dpkg` does so the interface is maintained.
    """
    try:
        p = subprocess.Popen(['rpm', '--qf=%{NAME}\n', '-qf', pathname],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        return []
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        return []
    return [stdout.rstrip()]

def _rpm_V(package, pathname):
    """
    Return `True` if the given file has not been modified from its
    packaged state.
    """
    try:
        p = subprocess.Popen(['rpm', '-V', package],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        return True
    stdout, stderr = p.communicate()
    if 0 == p.returncode:
        return True
    pattern = re.compile(r'^..5......  . {0}$'.format(pathname))
    for line in stdout.splitlines():
        if pattern.match(line) is not None:
            return False
    return True
