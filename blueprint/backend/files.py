import base64
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

    # Visit every file in /etc except those on the exclusion list above.
    def visit(b, dirname, filenames):
        if dirname in EXCLUDE:
            return
        for filename in filenames:
            pathname = os.path.join(dirname, filename)
            if pathname in EXCLUDE:
                continue

            # Because of limitations in the Python grammar and in PEP-8,
            # do the bulk of each visit in a subroutine.
            _visit(b, pathname)

    os.path.walk('/etc', visit, b)

def _visit(b, pathname):
    try:
        content = open(pathname).read()
    except IOError:
        #logging.warning('{0} not readable'.format(pathname))
        return

    # Don't store files which are part of a package and are unchanged
    # from the distribution.
    if hashlib.md5(content).hexdigest() == _md5(pathname):
        return

    # Don't store DevStructure's default /etc/fuse.conf.  (This is
    # a legacy condition.)
    if '/etc/fuse.conf' == pathname:
        try:
            if 'user_allow_other\n' == open(pathname).read():
                return
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
    # a blueprint and really shouldn't appear in /etc at all.
    else:
        logging.warning('{0} is not a regular file or symbolic link'
                        ''.format(pathname))
        return

    pw = pwd.getpwuid(s.st_uid)
    gr = grp.getgrgid(s.st_gid)
    b.files[pathname] = dict(content=content,
                             encoding=encoding,
                             group=gr.gr_name,
                             mode='{0:o}'.format(s.st_mode),
                             owner=pw.pw_name)

def _md5(pathname):
    """
    Find the MD5 sum of the packaged version of pathname or None if the
    pathname does not come from a Debian package.
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
