import os.path
import subprocess
import sys

class GitError(EnvironmentError):
    pass

def init():
    """
    Initialize the Git repository.
    """
    dirname = repo()
    try:
        os.makedirs(dirname)
    except OSError:
        pass
    p = subprocess.Popen(['git', '--git-dir', repo(), 'init', '--bare'],
                         close_fds=True, stdout=sys.stderr)
    p.communicate()
    if 0 != p.returncode:
        #sys.exit(p.returncode)
        raise GitError(p.returncode)

def git(*args, **kwargs):
    """
    Execute a Git command.  Raises GitError on non-zero exits unless the
    raise_exc keyword argument is falsey.
    """
    p = subprocess.Popen(['git',
                          '--git-dir', repo(),
                          '--work-tree', os.getcwd()] + list(args),
                         close_fds=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(kwargs.get('stdin'))
    if 0 != p.returncode and kwargs.get('raise_exc', True):
        raise GitError(p.returncode)
    return p.returncode, stdout

def repo():
    """
    Return the full path to the Git repository.
    """
    return os.path.expanduser('~/.blueprints.git')

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
    status, stdout = git('show', '--format=%T', commit)
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
