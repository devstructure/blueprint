"""
Search for `apt` packages to include in the blueprint.
"""

import logging
import re
import subprocess

CACHE = '/tmp/blueprint-exclusions'

def apt(b):
    logging.info('searching for apt packages')

    p = subprocess.Popen(['dpkg-query',
                          '-f=${Package} ${Version}\n',
                          '-W'],
                         close_fds=True, stdout=subprocess.PIPE)
    s = exclusions()
    for line in p.stdout:
        package, version = line.strip().split()
        if package in s:
            continue
        b.packages['apt'][package].append(version)

def exclusions():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    # Read from a cached copy.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass

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
            package, property = line.rstrip().split()
            if property in ('yes', 'important', 'required', 'standard'):
                s.add(package)

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
    f = open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s
