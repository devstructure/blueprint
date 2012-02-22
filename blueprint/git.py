import logging
import os
import os.path
import subprocess
import sys

from blueprint import util


class GitError(EnvironmentError):
    pass


def unroot():
    """
    Drop privileges gained through sudo(1).
    """
    if util.via_sudo():
        uid = int(os.environ['SUDO_UID'])
        gid = int(os.environ['SUDO_GID'])
        os.setgid(gid)
        os.setegid(gid)
        os.setuid(uid)
        os.seteuid(uid)


def init():
    """
    Initialize the Git repository.
    """
    dirname = repo()
    try:
        os.makedirs(dirname)
        if util.via_sudo():
            uid = int(os.environ['SUDO_UID'])
            gid = int(os.environ['SUDO_GID'])
            os.chown(dirname, uid, gid)
    except OSError:
        pass
    try:
        p = subprocess.Popen(['git',
                              '--git-dir', dirname,
                              'init',
                              '--bare',
                              '-q'],
                             close_fds=True,
                             preexec_fn=unroot,
                             stdout=sys.stderr,
                             stderr=sys.stderr)
    except OSError:
        logging.error('git not found on PATH - exiting')
        sys.exit(1)
    p.communicate()
    if 0 != p.returncode:
        #sys.exit(p.returncode)
        raise GitError(p.returncode)


def git_args():
    """
    Return the basic arguments for running Git commands against
    the blueprints repository.
    """
    return ['git', '--git-dir', repo(), '--work-tree', os.getcwd()]


def git(*args, **kwargs):
    """
    Execute a Git command.  Raises GitError on non-zero exits unless the
    raise_exc keyword argument is falsey.
    """
    try:
        p = subprocess.Popen(git_args() + list(args),
                             close_fds=True,
                             preexec_fn=unroot,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
    except OSError:
        logging.error('git not found on PATH - exiting')
        sys.exit(1)
    stdout, stderr = p.communicate(kwargs.get('stdin'))
    if 0 != p.returncode and kwargs.get('raise_exc', True):
        raise GitError(p.returncode)
    return p.returncode, stdout


def repo():
    """
    Return the full path to the Git repository.
    """
    return os.path.expandvars('$HOME/.blueprints.git')


def rev_parse(refname):
    """
    Return the referenced commit or None.
    """
    status, stdout = git('rev-parse', '-q', '--verify', refname,
                         raise_exc=False)
    if 0 != status:
        return None
    return stdout.rstrip()


def tree(commit):
    """
    Return the tree in the given commit or None.
    """
    status, stdout = git('show', '--pretty=format:%T', commit)
    if 0 != status:
        return None
    return stdout[0:40]


def ls_tree(tree, dirname=[]):
    """
    Generate all the pathnames in the given tree.
    """
    status, stdout = git('ls-tree', tree)
    for line in stdout.splitlines():
        mode, type, sha, filename = line.split()
        if 'tree' == type:
            for entry in ls_tree(sha, dirname + [filename]):
                yield entry
        else:
            yield mode, type, sha, os.path.join(*dirname + [filename])


def blob(tree, pathname):
    """
    Return the SHA of the blob by the given name in the given tree.
    """
    for mode, type, sha, pathname2 in ls_tree(tree):
        if pathname == pathname2:
            return sha
    return None


def content(blob):
    """
    Return the content of the given blob.
    """
    status, stdout = git('show', blob)
    if 0 != status:
        return None
    return stdout


def cat_file(blob, pathname=None):
    """
    If `pathname` is `None`, return an open file handle to the blob in
    Git's object store, otherwise stream the blob to `pathname`, all via
    the git-cat-file(1) command.
    """
    args = git_args() + ['cat-file', 'blob', blob]
    if pathname is None:
        return subprocess.Popen(args,
                                close_fds=True,
                                preexec_fn=unroot,
                                stdout=subprocess.PIPE).stdout
    else:
        subprocess.Popen(args,
                         close_fds=True,
                         preexec_fn=unroot,
                         stdout=open(pathname, 'w')).communicate()


def write_tree():
    status, stdout = git('write-tree')
    if 0 != status:
        return None
    return stdout.rstrip()


def commit_tree(tree, message='', parent=None):
    if parent is None:
        status, stdout = git('commit-tree', tree, stdin=message)
    else:
        status, stdout = git('commit-tree', tree, '-p', parent, stdin=message)
    if 0 != status:
        return None
    return stdout.rstrip()


def configured():
    """
    Return `True` if the author is configured in Git.  This allows Blueprint
    to bail out early for users that don't have things configured just right.
    """
    return not git('config', 'user.name', raise_exc=False)[0] \
       and not git('config', 'user.email', raise_exc=False)[0]
