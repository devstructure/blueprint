import os
import shutil
import tempfile

from blueprint import util


class cd(object):
    """
    Run in an alternative working directory in this context.
    """

    def __init__(self, new_cwd):
        self.new_cwd = new_cwd

    def __enter__(self):
        self.old_cwd = os.getcwd()
        os.chdir(self.new_cwd)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.old_cwd)


class mkdtemp(object):
    """
    Run in a temporary working directory in this context.  Remove the
    temporary directory automatically afterward.
    """

    def __init__(self, dir=None):
        self.cwd = os.getcwd()
        if dir is None:
            dir = tempfile.gettempdir()
        self.tempdir = tempfile.mkdtemp(dir=dir)
        if util.via_sudo():
            uid = int(os.environ['SUDO_UID'])
            gid = int(os.environ['SUDO_GID'])
            os.chown(self.tempdir, uid, gid)

    def __enter__(self):
        os.chdir(self.tempdir)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.cwd)
        shutil.rmtree(self.tempdir)
