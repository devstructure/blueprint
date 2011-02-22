"""
Chef code generator.
"""

import errno
from collections import defaultdict
import os
import os.path
import re
import tarfile

class Cookbook(object):
    """
    A cookbook is a collection of Chef resources plus the files and other
    supporting objects needed to run it.
    """

    def __init__(self, name, comment=None):
        """
        """
        self.name = str(name)
        self.comment = comment
        self.resources = []
        self.files = {}

    def add(self, resource):
        """
        Resources must be added in the order they're expected to run.
        Chef does not support managing dependencies explicitly.
        """
        self.resources.append(resource)

    def apt_package(self, name, **kwargs):
        """
        Create a package resource provided by APT.
        """
        self.add(Resource('apt_package', name, **kwargs))

    def gem_package(self, name, **kwargs):
        """
        Create a package resource provided by RubyGems.
        """
        self.add(Resource('gem_package', name, **kwargs))

    def execute(self, name, **kwargs):
        """
        Create an execute resource.
        """
        self.add(Resource('execute', name, **kwargs))

    def directory(self, name, **kwargs):
        """
        Create a directory resource.
        """
        self.add(Resource('directory', name, **kwargs))

    def link(self, name, **kwargs):
        """
        Create a (symbolic) link resource.
        """
        self.add(Resource('link', name, **kwargs))

    def file(self, name, content, **kwargs):
        """
        Create a file or cookbook_file resource depending on whether the
        cookbook is dumped to a string or to files.
        """
        self.add(File(name, content, **kwargs))

    def _dump(self, w, inline=False):
        """
        Generate Chef code.  This will call the callable `w` with each
        line of output.  `dumps` and `dumpf` use this to append to a list
        and write to a file with the same code.

        If present, a comment is written first.  Next, resources are written
        in the order they were added to the recipe.
        """
        if self.comment is not None:
            w(self.comment)
        for resource in self.resources:
            w(resource.dumps(inline))

    def dumps(self):
        """
        Generate a string containing Chef code and all file contents.
        """
        out = []
        return ''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing Chef code and templates.  The directory
        structure generated is that of a cookbook with a default recipe and
        cookbook files.
        """
        os.mkdir(self.name)
        f = open(os.path.join(self.name, 'metadata.rb'), 'w')
        f.close()
        os.mkdir(os.path.join(self.name, 'recipes'))
        filename = os.path.join(self.name, 'recipes/default.rb')
        f = open(filename, 'w')
        self._dump(f.write, inline=False)
        f.close()
        for resource in self.resources:
            if 'cookbook_file' != resource.type:
                continue
            pathname = os.path.join(self.name, 'files/default',
                resource.name[1:])
            try:
                os.makedirs(os.path.dirname(pathname))
            except OSError as e:
                if errno.EEXIST != e.errno:
                    raise e
            f = open(pathname, 'w')
            f.write(resource.content)
            f.close()
        if gzip:
            filename = 'chef-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return filename

class Resource(dict):
    """
    A Chef resource has a type, a name, and some parameters.  Nothing has
    to be unique as resources are dealt with in order rather than by building
    a dependency graph.

    """

    def __init__(self, type, name, **kwargs):
        """
        Don't instantiate this class directly.  Instead, use the methods made
        available in the Cookbook class.
        """
        super(Resource, self).__init__(**kwargs)
        self.type = type
        self.name = name

    @staticmethod
    def _dumps(value):
        """
        Return a value as it should be written.  If the value starts with
        a ':', it will be written as-is.  Otherwise, it will be written as
        a string.
        """
        if value is None:
            return 'nil'
        elif True == value:
            return 'true'
        elif False == value:
            return 'false'
        elif 0 < len(value) and ':' == value[0]:
            return value
        if isinstance(value, unicode):
            value = str(value)
        return repr(value)

    def dumps(self, inline=False):
        """
        Stringify differently depending on the number of options so the
        output always looks like Ruby code should look.  Parentheses are
        always employed here due to grammatical inconsistencies when using
        braces surrounding a block.
        """
        if 0 == len(self):
            return '{0}({1})\n'.format(self.type, self._dumps(self.name))
        elif 1 == len(self):
            key, value = self.items()[0]
            return '{0}({1}) {{ {2} {3} }}\n'.format(self.type,
                                                     self._dumps(self.name),
                                                     key,
                                                     self._dumps(value))
        else:
            out = ['{0}({1}) do\n'.format(self.type, self._dumps(self.name))]
            for key, value in sorted(self.iteritems()):
                out.append('\t{0} {1}\n'.format(key, self._dumps(value)))
            out.append('end\n')
            return ''.join(out)

class File(Resource):
    """
    Special Chef file or cookbook_file resource.
    """

    def __init__(self, name, content=None, **kwargs):
        """
        File resources handle their content explicitly because in some
        cases it is not written as a normal parameter.
        """
        super(File, self).__init__('file', name, **kwargs)
        self.content = content

    def dumps(self, inline=False):
        """
        Decide whether to write as a file with content or a cookbook_file
        that leaves its content to be dealt with later.
        """
        if inline:
            if self.content is not None:
                self['content'] = self.content
                del self.content
            self.type = 'file'
            del self['source']
        else:
            self.type = 'cookbook_file'
        return super(File, self).dumps(inline)
