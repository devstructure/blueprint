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
    if not isinstance(s, set):
        s = set([s])
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
    return set([package for package, spec in s])
