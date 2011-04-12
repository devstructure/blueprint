"""
Search for `yum` packages to include in the blueprint.
"""

import logging
import re
import subprocess

CACHE = '/tmp/blueprint-yum-exclusions'

def yum(b):
    logging.info('searching for yum packages')

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Debian-based
    # system.
    try:
        p = subprocess.Popen(['rpm',
                              '--qf=%{NAME}\x1E%{GROUP}\x1E%{EPOCH}' # No ,
                              '\x1E%{VERSION}-%{RELEASE}.%{ARCH}\n',
                              '-qa'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return

    s = exclusions()
    for line in p.stdout:
        package, group, epoch, version = line.strip().split('\x1E')
        if package in s:
            continue
        if '(none)' != epoch:
            version = '{0}:{1}'.format(epoch, version)
        b.packages['yum'][package].append(version)

def exclusions():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    # Read from a cached copy.  Move the old cache location to the new one
    # if necessary.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for yum packages to exclude')

    # Start with a few groups that install common packages.
    s = set()
    pattern = re.compile(r'^   (\S+)')
    p = subprocess.Popen(['yum', 'groupinfo',
                          'core','base', 'gnome-desktop'],
                         close_fds=True, stdout=subprocess.PIPE)
    for line in p.stdout:
        match = pattern.match(line)
        if match is None:
            continue
        p2 = subprocess.Popen(['rpm',
                               '-q',
                               '--qf=%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}',
                               match.group(1)],
                              close_fds=True, stdout=subprocess.PIPE)
        stdout, stderr = p2.communicate()
        s.add((match.group(1), stdout))

    # Walk the dependency tree all the way to the leaves.
    tmp_s = s
    pattern = re.compile(r'provider: ([^.]+)\.\S+ (\S+)')
    while 1:
        new_s = set()
        for package, spec in tmp_s:
            p = subprocess.Popen(['yum', 'deplist', spec],
                close_fds=True, stdout=subprocess.PIPE)
            for line in p.stdout:
                match = pattern.search(line)
                if match is None:
                    continue
                new_s.add((match.group(1), '-'.join(match.group(1, 2))))

        # If there is to be a next iteration, `new_s` must contain some
        # packages not yet in `s`.
        tmp_s = new_s - s
        if 0 == len(tmp_s):
            break
        s |= new_s

    # Now that the tree has been walked, discard the version-qualified names,
    # leaving just the package names.
    s = set([package for package, spec in s])

    # Write to a cache.
    logging.info('caching excluded yum packages')
    f = open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s
