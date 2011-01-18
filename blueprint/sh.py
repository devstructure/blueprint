"""
Shell code generator.
"""

import gzip as gziplib
import os
import os.path
import tarfile

class Script(object):
    """
    A script is a list of shell commands.  The pomp and circumstance is
    only necessary for providing an interface like the Puppet and Chef
    code generators.
    """

    def __init__(self, name, comment=None):
        self.name = name
        self.comment = comment
        self.out = []
        self.sources = {}

    def add(self, s='', *args, **kwargs):
        if 'raw' in kwargs:
            self.out.append(kwargs['raw'])
        else:
            self.out.append('{0}\n'.format(s).format(*args))
        for filename, content in kwargs.get('sources', {}).iteritems():
            self.sources[filename] = content

    def dumps(self):
        """
        Generate a string containing shell code and all file contents.
        """
        return ''.join(self.out)

    def dumpf(self, gzip=False):
        """
        Generate a file containing shell code and all file contents.
        """
        if 0 != len(self.sources):
            os.mkdir(self.name)
            filename = os.path.join(self.name, 'bootstrap.sh')
            f = open(filename, 'w')
        elif gzip:
            filename = '{0}.sh.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.sh'.format(self.name)
            f = open(filename, 'w')
        f.write(self.comment)
        f.write('cd "$(dirname "$0")"\n')
        for filename2, content in sorted(self.sources.iteritems()):
            f2 = open(os.path.join(self.name, filename2), 'w')
            f2.write(content)
            f2.close()
        for out in self.out:
            f.write(out)
        f.close()
        if gzip and 0 != len(self.sources):
            filename = 'sh-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return filename
