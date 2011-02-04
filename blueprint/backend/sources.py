"""
Search for software built from source to include in the blueprint as a tarball.
"""

import errno
import glob
import hashlib
import logging
import os
import os.path
import re
import stat
import tarfile

def sources(b):
    logging.info('searching for software built from source')
    tmpname = os.path.join(os.getcwd(), 'usr-local')

    exclude = []

    pattern_pip = re.compile(r'\.egg-info/installed-files.txt$')
    pattern_egg = re.compile(r'\.egg(?:-info)?(?:/|$)')
    pattern_pth = re.compile(
        r'lib/python[^/]+/(?:dist|site)-packages/easy-install.pth$')
    pattern_bin = re.compile(r'EASY-INSTALL(?:-ENTRY)?-SCRIPT')

    # Create a partial shallow copy of `/usr/local`.
    for dirpath, dirnames, filenames in os.walk('/usr/local'):
        dirpath2 = os.path.normpath(
            os.path.join(tmpname, os.path.relpath(dirpath, '/usr/local')))

        # Create this directory in the shallow copy with matching mode, owner,
        # and owning group.  Suggest running as `root` if this doesn't work.
        os.mkdir(dirpath2)
        s = os.lstat(dirpath)
        try:
            os.lchown(dirpath2, s.st_uid, s.st_gid)
            os.chmod(dirpath2, s.st_mode)
        except OSError as e:
            logging.warning('{0} caused {1} - try running as root'
                ''.format(dirpath, errno.errorcode[e.errno]))
            return

        for filename in filenames:
            pathname = os.path.join(dirpath, filename)
            pathname2 = os.path.join(dirpath2, filename)

            # Exclude files that are part of the RubyGems package.
            for globname in (
                os.path.join('/usr/lib/ruby/gems/*/gems/rubygems-update-*/lib',
                             pathname[1:]),
                os.path.join('/var/lib/gems/*/gems/rubygems-update-*/lib',
                             pathname[1:])):
                if 0 < len(glob.glob(globname)):
                    continue

            # Remember the path to all of `pip`'s `installed_files.txt` files.
            if pattern_pip.search(pathname):
                exclude.extend([os.path.join(dirpath2, line.rstrip())
                    for line in open(pathname)])

            # Likewise remember the path to Python eggs.
            if pattern_egg.search(pathname):
                exclude.append(pathname2)

            # Exclude `easy_install`'s bookkeeping file, too.
            if pattern_pth.search(pathname):
                continue

            # Exclude executable placed by Python packages.
            if pathname.startswith('/usr/local/bin/') and pattern_bin.match(
                open(pathname).read()):
                continue

            # Hard link this file into the shallow copy.  Suggest running as
            # `root` if this doesn't work though in practice the check above
            # will have already caught this problem.
            try:
                os.link(pathname, pathname2)
            except OSError as e:
                logging.warning('{0} caused {1} - try running as root'
                                ''.format(pathname,
                                          errno.errorcode[e.errno]))
                return

    # Unlink files that were remembered for exclusion above.
    for pathname in exclude:
        try:
            os.unlink(pathname)
        except OSError as e:
            if e.errno not in (errno.EISDIR, errno.ENOENT):
                raise e

    # Clean up dangling symbolic links.  This makes the assumption that
    # no one intends to leave dangling symbolic links hanging around
    # `/usr/local`, which I think is a good assumption.
    for dirpath, dirnames, filenames in os.walk(tmpname):
        for filename in filenames:
            pathname = os.path.join(dirpath, filename)
            s = os.lstat(pathname)
            if stat.S_ISLNK(s.st_mode):
                try:
                    os.stat(pathname)
                except OSError as e:
                    if errno.ENOENT == e.errno:
                        os.unlink(pathname)

    # Remove empty directories.  For any that hang around, match their
    # access and modification times to the source in `/usr/local`, otherwise
    # the hash of the tarball will not be deterministic.
    for dirpath, dirnames, filenames in os.walk(tmpname, topdown=False):
        try:
            os.rmdir(dirpath)
        except OSError:
            os.utime(dirpath, (s.st_atime, s.st_mtime))

    # If the shallow copy of `/usr/local` still exists, create a tarball
    # named by its SHA1 sum and include it in the blueprint.
    try:
        tar = tarfile.open('usr-local.tar', 'w')
        tar.add(tmpname, '.')
    except OSError:
        return
    finally:
        tar.close()
    sha1 = hashlib.sha1()
    f = open('usr-local.tar', 'r')
    [sha1.update(buf) for buf in iter(lambda: f.read(4096), '')]
    f.close()
    tarname = '{0}.tar'.format(sha1.hexdigest())
    os.rename('usr-local.tar', tarname)
    b.sources['/usr/local'] = tarname
