"""
Instantiate Blueprint objects for the command-line tools.  Use of these
functions outside of command-line tools is not advised, as in many cases
they exit the Python interpreter.
"""

import logging
import os
import sys

import blueprint
import context_managers
import rules


def create(options, args):
    """
    Instantiate and return a Blueprint object from either standard input or by
    reverse-engineering the system.
    """
    try:
        with context_managers.mkdtemp():

            if not os.isatty(sys.stdin.fileno()):
                try:
                    b = blueprint.Blueprint.load(sys.stdin, args[0])
                except ValueError:
                    logging.error(
                        'standard input contains invalid blueprint JSON')
                    sys.exit(1)
            else:
                b = blueprint.Blueprint.create(args[0])

            if options.subtrahend:
                logging.info('subtracting {0}'.format(options.subtrahend))
                b_s = blueprint.Blueprint.checkout(options.subtrahend)
                b = b - b_s

            b.commit(options.message or '')
            return b

    except blueprint.NameError:
        logging.error('invalid blueprint name')
        sys.exit(1)


def read(options, args):
    """
    Instantiate and return a Blueprint object from either standard input or by
    reading from the local Git repository.
    """
    try:
        name = args[0]
    except IndexError:
        name = None
    name, stdin = '-' == name and (None, True) or (name, False)
    try:
        if not os.isatty(sys.stdin.fileno()) or stdin:
            try:

                # TODO This implementation won't be able to find source
                # tarballs that should be associated with the blueprint
                # on standard input.
                return blueprint.Blueprint.load(sys.stdin, name)

            except ValueError:
                logging.error('standard input contains invalid blueprint JSON')
                sys.exit(1)
        if name is not None:
            return blueprint.Blueprint.checkout(name)
    except blueprint.NotFoundError:
        logging.error('blueprint {0} does not exist'.format(name))
        sys.exit(1)
    except blueprint.NameError:
        logging.error('invalid blueprint name {0}'.format(name))
        sys.exit(1)
    logging.error('no blueprint found on standard input')
    sys.exit(1)


def read_rules(options, args):
    """
    Instantiate and return a Blueprint object created by rules read from
    either standard input or the given pathname.
    """
    try:
        pathname = args[0]
    except IndexError:
        pathname = None
    pathname, stdin = '-' == pathname and (None, True) or (pathname, False)
    r = rules.none()
    if not os.isatty(sys.stdin.fileno()) or stdin:
        r.parse(sys.stdin)
        with context_managers.mkdtemp():
            b = blueprint.Blueprint.rules(r, 'blueprint-rendered-rules')
            b.commit(options.message or '')
            return b
    if pathname is not None:
        name, _ = os.path.splitext(os.path.basename(pathname))
        try:
            r.parse(open(pathname))
            with context_managers.mkdtemp():
                b = blueprint.Blueprint.rules(r, name)
                b.commit(options.message or '')
                return b
        except blueprint.NameError:
            logging.error('invalid blueprint name {0}'.format(name))
            sys.exit(1)
        except IOError:
            logging.error('{0} does not exist'.format(pathname))
            sys.exit(1)
    logging.error('no rules found on standard input')
    sys.exit(1)
