import logging
import re
import subprocess


def apt(s):
    """
    Walk the dependency tree of all the packages in set s all the way to
    the leaves.  Return the set of s plus all their dependencies.
    """
    logging.debug('searching for APT dependencies')
    if not isinstance(s, set):
        s = set([s])
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

    return s


def yum(s):
    """
    Walk the dependency tree of all the packages in set s all the way to
    the leaves.  Return the set of s plus all their dependencies.
    """
    logging.debug('searching for Yum dependencies')

    if not hasattr(yum, '_cache'):
        yum._cache = {}
        try:
            p = subprocess.Popen(['rpm',
                                  '-qa',
                                  '--qf=%{NAME}\x1E[%{PROVIDES}\x1F]\n'],
                                 close_fds=True,
                                 stdout=subprocess.PIPE)
            for line in p.stdout:
                name, caps = line.rstrip().split('\x1E')
                yum._cache.update([(cap, name) for cap in caps.split('\x1F')])
        except OSError:
            pass

    if not isinstance(s, set):
        s = set([s])

    tmp_s = s
    while 1:
        new_s = set()
        for package in tmp_s:
            try:
                p = subprocess.Popen(['rpm', '-qR', package],
                                     close_fds=True,
                                     stdout=subprocess.PIPE)
            except OSError:
                continue
            for line in p.stdout:
                cap = line.rstrip()[0:line.find(' ')]
                if 'rpmlib' == cap[0:6]:
                    continue
                try:
                    new_s.add(yum._cache[cap])
                except KeyError:
                    try:
                        p2 = subprocess.Popen(['rpm',
                                               '-q',
                                               '--qf=%{NAME}',
                                               '--whatprovides',
                                               cap],
                                              close_fds=True,
                                              stdout=subprocess.PIPE)
                        stdout, stderr = p2.communicate()
                        yum._cache[cap] = stdout
                        new_s.add(stdout)
                    except OSError:
                        pass

        # If there is to be a next iteration, `new_s` must contain some
        # packages not yet in `s`.
        tmp_s = new_s - s
        if 0 == len(tmp_s):
            break
        s |= new_s

    return s
