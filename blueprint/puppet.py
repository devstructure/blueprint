"""
Puppet code generator.
"""

import errno
from collections import defaultdict
import os
import os.path
import re
import tarfile

class Manifest(object):
    """
    A Puppet manifest contains resources and a tree of other manifests
    that may each contain resources.  Manifests are valid targets of
    dependencies and they are used heavily in the generated code to keep
    the inhumane-ness to a minimum.  A `Manifest` object generates a
    Puppet `class`.
    """

    def __init__(self, name, parent=None, comment=None):
        """
        Each class must have a name and might have a parent.  If a manifest
        has a parent, this signals it to `include` itself in the parent.
        """
        self.name, count = re.subn(r'\.', '--', str(name))
        self.parent = parent
        self.comment = comment
        self.manifests = defaultdict(dict)
        self.defaults = {}
        self.resources = defaultdict(dict)
        self.deps = []

    def __getitem__(self, name):
        """
        Manifests behave a bit like hashes in that their children can be
        traversed.  Note the children can't be assigned directly because
        that would break bidirectional parent-child relationships.
        """
        if name not in self.manifests:
            self.manifests[name] = self.__class__(name, self.name)
        return self.manifests[name]

    def add(self, resource):
        """
        Add a resource to this manifest.  Order is never important in Puppet
        since all dependencies must be declared.  Normal resources that have
        names are just added to the tree.  Resources that are declaring
        defaults for an entire type have `None` for their name, are stored
        separately, and are cumulative.
        """
        if resource.name:
            self.resources[resource.type][resource.name] = resource
        else:
            if resource.type in self.defaults:
                self.defaults[resource.type].update(resource)
            else:
                self.defaults[resource.type] = resource

    def dep(self, *args):
        """
        Declare a dependency between two or more resources.  The arguments
        will be taken from left to right to mean the left precedes the right.
        """
        self.deps.append(args)

    def files(self):
        """
        Generate the pathname and content of every file in this and any
        child manifests.
        """
        for name, resource in self.resources['file'].iteritems():
            if hasattr(resource, 'content') and resource.content is not None:
                if 'source' in resource:
                    yield name, 'files', resource.content
                else:
                    yield name, 'templates', resource.content
        for manifest in self.manifests.itervalues():
            for pathname, dirname, content in manifest.files():
                yield pathname, dirname, content

    def _dump(self, w, inline=False, tab=''):
        """
        Generate Puppet code.  This will call the callable `w` with each
        line of output.  `dumps` and `dumpf` use this to append to a list
        and write to a file with the same code.

        If present, a comment is written first.  This is followed by child
        manifests.  Within each manifest, any type defaults are written
        immediately before resources of that type.  Where possible, order
        is alphabetical.  If this manifest has a parent, the last action is
        to include this class in the parent.
        """
        if self.comment is not None:
            w(self.comment)

        # Wrap everything in a class.
        w('{0}class {1} {{\n'.format(tab, self.name))
        tab_extra = '{0}\t'.format(tab)

        # Type-level defaults.
        for type, resource in sorted(self.defaults.iteritems()):
            w(resource.dumps(inline, tab_extra))

        # Declare relationships between resources that appear outside the
        # scope of individual resources.
        for deps in self.deps:
            w('{0}{1}\n'.format(tab_extra,
                                ' -> '.join([repr(dep) for dep in deps])))

        # Resources in this manifest.
        for type, resources in sorted(self.resources.iteritems()):
            if 1 < len(resources):
                w('{0}{1} {{\n'.format(tab_extra, type))
                for name, resource in sorted(resources.iteritems()):
                    resource.style = Resource.PARTIAL
                    w(resource.dumps(inline, tab_extra))
                w('{0}}}\n'.format(tab_extra))
            elif 1 == len(resources):
                w(resources.values()[0].dumps(inline, tab_extra))

        # Child manifests.
        for name, manifest in sorted(self.manifests.iteritems()):
            manifest._dump(w, inline, tab_extra)

        # Close the class.
        w('{0}}}\n'.format(tab))

        # Include the class that was just defined in its parent.  Everything
        # is included but is still namespaced.
        if self.parent is not None:
            w('{0}include {1}\n'.format(tab, self.name))

    def dumps(self):
        """
        Generate a string containing Puppet code and all file contents.
        This output would be suitable for use with `puppet apply` or for
        displaying an entire blueprint on a single web page.
        """
        out = []
        self._dump(out.append, inline=True)
        return ''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing Puppet code and templates.  The directory
        structure generated is that of a module named by the main manifest.
        """
        os.mkdir(self.name)
        os.mkdir(os.path.join(self.name, 'manifests'))
        filename = os.path.join(self.name, 'manifests/init.pp')
        f = open(filename, 'w')
        self._dump(f.write, inline=False)
        f.close()
        for pathname, dirname, content in self.files():
            pathname = os.path.join(self.name, dirname, pathname[1:])
            try:
                os.makedirs(os.path.dirname(pathname))
            except OSError as e:
                if errno.EEXIST != e.errno:
                    raise e
            f = open(pathname, 'w')
            f.write(content)
            f.close()
        if gzip:
            filename = 'puppet-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return filename

class BareString(str):
    """
    Strings of this type will not be quoted when written into a Puppet
    manifest.
    """
    pass

class Resource(dict):
    """
    A Puppet resource is basically a named hash.  The name is unique to
    the Puppet catalog (which may contain any number of manifests in
    any number of modules).  The attributes that are expected vary
    by the resource's actual type.  This implementation uses the class
    name to determine the type, so do not instantiate `Resource`
    directly.
    """

    # These constants are arbitrary and only serve to control how resources
    # are written out as Puppet code.
    COMPLETE = 1
    PARTIAL = 2
    DEFAULTS = 3

    @classmethod
    def ref(cls, *args):
        """
        Reference an existing resource.  Useful for declaring dependencies
        between resources.

        It'd be great to do this with __getitem__ but that doesn't seem
        possible.
        """
        if 1 < len(args):
            return [cls.ref(arg) for arg in args]
        return cls(*args)

    @classmethod
    def defaults(cls, **kwargs):
        """
        Set defaults for a resource type.
        """
        resource = cls(None, **kwargs)
        resource.style = cls.DEFAULTS
        return resource

    def __init__(self, name, **kwargs):
        """
        A resource has a type (derived from the actual class), a name, and
        parameters, which it stores in the dictionary from which it inherits.
        By default, all resources will create COMPLETE representations.
        """
        super(Resource, self).__init__(**kwargs)
        self._type = self.__class__.__name__.lower()
        self.name = name
        self.style = self.COMPLETE

    def __repr__(self):
        """
        The string representation of a resource is the Puppet syntax for a
        reference as used when declaring dependencies.
        """
        return '{0}["{1}"]'.format(self.type.capitalize(), self.name)

    @property
    def type(self):
        """
        The type of a resource is read-only and derived from the class name.
        """
        return self._type

    @staticmethod
    def _dumps(value, bare=True):
        """
        Return a value as it should be written.
        """
        if value is None:
            return 'undef'
        elif True == value:
            return 'true'
        elif False == value:
            return 'false'
        elif bare and re.match(r'^[a-z]+$', '{0}\n'.format(value)) is not None:
            return value
        elif hasattr(value, 'bare'):
            return value
        if isinstance(value, BareString):
            return value
        if isinstance(value, unicode):
            value = str(value)
        return repr(value)

    def dumps(self, inline=False, tab=''):
        """
        Generate Puppet code for this resource, returned in a string.  The
        resource's style is respected, the Puppet coding standards are
        followed, and the indentation is human-readable.
        """
        out = []

        # Begin the resource and decide tab width based on the style.
        tab_params = tab
        if self.COMPLETE == self.style:
            out.append('{0}{1} {{ {2}:'.format(tab,
                                               self.type,
                                               self._dumps(self.name, False)))
        elif self.PARTIAL == self.style:
            out.append('{0}\t{1}:'.format(tab, self._dumps(self.name, False)))
            tab_params = '{0}\t'.format(tab)
        elif self.DEFAULTS == self.style:
            out.append('{0}{1} {{'.format(tab, self.type.capitalize()))

        # Handle resources with parameters.
        if 0 < len(self):

            # Find the maximum parameter name length so => operators will
            # line up as coding standards dictate.
            l = max([len(key) for key in self.iterkeys()])

            # Serialize parameter values.  Certain values don't require
            # quotes.
            for key, value in sorted(self.iteritems()):
                key = '{0}{1}'.format(key, ' ' * (l - len(key)))
                out.append('{0}\t{1} => {2},'.format(tab_params,
                                                     key,
                                                     self._dumps(value)))

            # Close the resource as the style dictates.
            if self.COMPLETE == self.style:
                out.append('{0}}}\n'.format(tab))
            elif self.PARTIAL == self.style:
                out.append('{0};\n'.format(out.pop()[0:-1]))
            elif self.DEFAULTS == self.style:
                out.append('{0}}}\n'.format(tab))

        # Handle resources without parameters.
        else:
            if self.COMPLETE == self.style:
                out.append('{0} }}\n'.format(out.pop()))
            elif self.PARTIAL == self.style:
                out.append('{0};\n'.format(out.pop()))
            elif self.DEFAULTS == self.style:
                out.append('{0}}}\n'.format(out.pop()))

        return '\n'.join(out)

class Package(Resource):
    """
    Puppet package resource.
    """
    pass

class Exec(Resource):
    """
    Puppet exec resource.
    """
    pass

class File(Resource):
    """
    Puppet file resource.
    """

    def __init__(self, name, modulename=None, content=None, **kwargs):
        """
        File resources handle their content explicitly because in some
        cases it is not written as a normal parameter.
        """
        super(File, self).__init__(name, **kwargs)
        self.modulename = modulename
        self.content = content

    def dumps(self, inline=False, tab=''):
        """
        Treat the content as a normal parameter if and only if the resource
        is being written inline.
        """
        if inline:

            # FIXME Leaky abstraction.  The source attribute is perfectly
            # valid but the check here assumes it is only ever used for
            # placing source tarballs.
            if 'source' in self:
                raise ValueError("source tarballs can't be dumped as strings.")

            if getattr(self, 'content', None) is not None:
                self['content'] = self.content
                del self.content
        else:
            if self.content is not None:
                self['content'] = BareString('template("{0}/{1}")'.format(
                    self.modulename,
                    self.name[1:]))
        return super(File, self).dumps(inline, tab)

class Class(Resource):
    """
    Puppet class resource.
    """

    def __repr__(self):
        """
        Puppet class resource names cannot contain dots due to limitations
        in the grammar.
        """
        name, count = re.subn(r'\.', '--', str(self.name))
        return '{0}["{1}"]'.format(self.type.capitalize(), name)
