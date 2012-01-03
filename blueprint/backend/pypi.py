"""
Search for Python packages to include in the blueprint.
"""

import glob
import logging
import os
import re
import subprocess


# Precompile a pattern to extract the manager from a pathname.
pattern_manager = re.compile(r'lib/(python[^/]*)/(dist|site)-packages')

# Precompile patterns for differentiating between packages built by
# `easy_install` and packages built by `pip`.
pattern_egg = re.compile(r'\.egg$')
pattern_egginfo = re.compile(r'\.egg-info$')

# Precompile a pattern for extracting package names and version numbers.
pattern = re.compile(r'^([^-]+)-([^-]+).*\.egg(-info)?$')


def pypi(b, r):
    logging.info('searching for Python packages')

    # Look for packages in the typical places.  `pip` has its `freeze`
    # subcommand but there is no way but diving into the directory tree to
    # figure out what packages were `easy_install`ed.  If `VIRTUAL_ENV`
    # appears in the environment, treat the directory it names just like
    # the global package directories.
    globnames = ['/usr/lib/python*/dist-packages',
                 '/usr/lib/python*/site-packages',
                 '/usr/local/lib/python*/dist-packages',
                 '/usr/local/lib/python*/site-packages']
    virtualenv = os.getenv('VIRTUAL_ENV')
    if virtualenv is not None:
        globnames.extend(['{0}/lib/python*/dist-packages'.format(virtualenv),
                          '{0}/lib/python*/dist-packages'.format(virtualenv)])
    for globname in globnames:
        for dirname in glob.glob(globname):
            manager = pattern_manager.search(dirname).group(1)
            for entry in os.listdir(dirname):
                match = pattern.match(entry)
                if match is None:
                    continue
                package, version = match.group(1, 2)
                pathname = os.path.join(dirname, entry)

                # Symbolic links indicate this is actually a system package
                # that injects files into the PYTHONPATH.
                if os.path.islink(pathname):
                    continue

                # Assume this is a Debian-based system and let `OSError`
                # looking for `dpkg-query` prove this is RPM-based.  In
                # that case, the dependencies get a bit simpler.
                try:
                    _dpkg_query(b, r,
                                manager, package, version,
                                entry, pathname)
                except OSError:
                    try:
                        _rpm(b, r, manager, package, version, entry, pathname)
                    except OSError:
                        logging.warning('neither dpkg nor rpm found')


def _dpkg_query(b, r, manager, package, version, entry, pathname):
    """
    Resolve dependencies on Debian-based systems.
    """

    # If this Python package is actually part of a system
    # package, abandon it.
    p = subprocess.Popen(['dpkg-query', '-S', pathname],
                         close_fds=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.communicate()
    if 0 == p.returncode:
        return

    # This package was installed via `easy_install`.  Make
    # sure its version of Python is in the blueprint so it
    # can be used as a package manager.
    if pattern_egg.search(entry):
        p = subprocess.Popen(['dpkg-query', '-f=${Version}', '-W', manager],
                             close_fds=True,
                             stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if 0 != p.returncode:
            return
        versions = b.packages['apt'][manager]
        if stdout not in versions:
            versions.add(stdout)
        if not r.ignore_package(manager, package):
            b.add_package(manager, package, version)

    # This package was installed via `pip`.  Figure out how
    # `pip` was installed and use that as this package's
    # manager.
    elif pattern_egginfo.search(entry) and os.path.exists(
        os.path.join(pathname, 'installed-files.txt')):
        p = subprocess.Popen(['dpkg-query', '-W', 'python-pip'],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if 0 != p.returncode:
            if not r.ignore_package('pip', package):
                b.add_package('pip', package, version)
        else:
            if not r.ignore_package('python-pip', package):
                b.add_package('python-pip', package, version)


def _rpm(b, r, manager, package, version, entry, pathname):
    """
    Resolve dependencies on RPM-based systems.
    """

    # If this Python package is actually part of a system
    # package, abandon it.
    p = subprocess.Popen(['rpm', '-qf', pathname],
                         close_fds=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.communicate()
    if 0 == p.returncode:
        return

    # This package was installed via `easy_install`.  Make
    # sure Python is in the blueprint so it can be used as
    # a package manager.
    if pattern_egg.search(entry):
        p = subprocess.Popen(['rpm',
                              '--qf=%{VERSION}-%{RELEASE}.%{ARCH}',
                              '-q',
                              'python'],
                             close_fds=True,
                             stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if 0 != p.returncode:
            return
        versions = b.packages['yum']['python']
        if stdout not in versions:
            versions.add(stdout)
        if not r.ignore_package('python', package):
            b.add_package('python', package, version)

    # This package was installed via `pip`.  Figure out how
    # `pip` was installed and use that as this package's
    # manager.
    elif pattern_egginfo.search(entry) and os.path.exists(
        os.path.join(pathname, 'installed-files.txt')):
        p = subprocess.Popen(['rpm', '-q', 'python-pip'],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if 0 != p.returncode:
            if not r.ignore_package('pip', package):
                b.add_package('pip', package, version)
        else:
            if not r.ignore_package('python-pip', package):
                b.add_package('python-pip', package, version)
