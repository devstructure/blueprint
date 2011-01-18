import getpass
import os
import os.path
import shutil
import tempfile

class breakout(object):
    """
    Break out of the current sandbox into the base sandbox for the duration
    of the `with` statement that calls this context manager.

    """

    def __enter__(self):
        """
        Break out of the current sandbox into the base sandbox.  Save the
        name of the sandbox and the original working directory for later.

        As documented many places around the web, breakout is accomplished
        by creating a `chroot` that does not contain the current working
        directory and ascending until the true root directory is reached.
        """
        self.cwd = os.getcwd()
        with root():
            tempdir = tempfile.mkdtemp()
            os.chdir('/')
            os.chroot(tempdir)
            tempdir = os.path.join(os.getcwd(), tempdir[1:])
            self.name = os.path.basename(os.getcwd())
            if '' == self.name:
                self.name = None
            while '/' != os.getcwd():
                os.chdir('..')
            os.chroot('.')
            os.rmdir(tempdir)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Return to the original sandbox and the original working directory.

        This function doesn't implement full device rebinding a la
        `sandbox-use`(1) and doesn't have to because it always uses a
        sandbox that has been used since the last boot, meaning all devices
        are already mounted properly.
        """
        if self.name is not None:
            with root():
                os.chroot(os.path.join('/var/sandboxes', self.name))
        if self.cwd is None:
            self.cwd = os.getenv('HOME',
                                 os.path.join('/home', getpass.getuser()))
        os.chdir(self.cwd)

class cd(object):
    """
    Run in an alternative working directory in this context.
    """

    def __init__(self, new_cwd):
        self.new_cwd = new_cwd

    def __enter__(self):
        self.old_cwd = os.getcwd()
        os.chdir(self.new_cwd)

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

    def __enter__(self):
        os.chdir(self.tempdir)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.cwd)
        shutil.rmtree(self.tempdir)

class root(object):
    """
    Run effectively as root in this context.  Return to being a normal
    user afterward.
    """

    def __enter__(self):
        self.euid = os.geteuid()
        os.seteuid(0)

    def __exit__(self, exc_type, exc_value, traceback):
        os.seteuid(self.euid)
