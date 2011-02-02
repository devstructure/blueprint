"""
Search for Python packages to include in the blueprint.
"""

import glob
import logging
import os
import re
import subprocess

def pypi(b):
    logging.info('searching for Python packages')

    # Precompile a pattern to extract the manager from a pathname.
    pattern_manager = re.compile(r'lib/(python[^/]+)/(dist|site)-packages')

    # Precompile patterns for differentiating between packages built by
    # `easy_install` and packages built by `pip`.
    pattern_egg = re.compile(r'\.egg$')
    pattern_egginfo = re.compile(r'\.egg-info$')

    # Precompile a pattern for extracting package names and version numbers.
    pattern = re.compile(r'^([^-]+)-([^-]+).*\.egg(-info)?$')

    # Look for packages in the typical places.  `pip` has its `freeze`
    # subcommand but there is no way but diving into the directory tree to
    # figure out what packages were `easy_install`ed.  If `VIRTUAL_ENV`
    # appears in the environment, treat the directory it names just like
    # the global package directories.
    globnames = ['/usr/local/lib/python*/dist-packages',
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
                package, version = match.group(1), match.group(2)

                # This package was installed via `easy_install`.  Make sure
                # its version of Python is in the blueprint so it can be
                # used as a package manager.
                if pattern_egg.search(entry):
                    p = subprocess.Popen(['dpkg-query',
                                          '-f=${Version}',
                                          '-W',
                                          manager],
                                         close_fds=True,
                                         stdout=subprocess.PIPE)
                    stdout, stderr = p.communicate()
                    if 0 != p.returncode:
                        continue
                    versions = b.packages['apt'][manager]
                    if stdout not in versions:
                        versions.append(stdout)
                    b.packages[manager][package].append(version)

                # This package was installed via `pip`.  Figure out how `pip`
                # was installed and use that as this package's manager.
                elif pattern_egginfo.search(entry):
                    p = subprocess.Popen(['dpkg-query', '-W', 'python-pip'],
                                         close_fds=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    p.communicate()
                    if 0 != p.returncode:
                        b.packages['pip'][package].append(version)
                    else:
                        b.packages['python-pip'][package].append(version)
