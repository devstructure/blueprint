"""
Puppet code generator.
"""

import base64
import codecs
from collections import defaultdict
import errno
import logging
import os
import os.path
import re
import tarfile

from blueprint import util
from blueprint import walk


def puppet(b, relaxed=False):
    """
    Generate Puppet code.
    """
    m = Manifest(b.name, comment=b.DISCLAIMER)

    # Set the default `PATH` for exec resources.
    m.add(Exec.defaults(path=os.environ['PATH']))

    def source(dirname, filename, gen_content, url):
        """
        Create file and exec resources to fetch and extract a source tarball.
        """
        pathname = os.path.join('/tmp', filename)
        if url is not None:
            m['sources'].add(Exec(
                '/bin/sh -c \'curl -o "{0}" "{1}" || wget -O "{0}" "{1}"\''.
                    format(pathname, url),
                before=Exec.ref(dirname),
                creates=pathname))
        elif gen_content is not None:
            m['sources'].add(File(
                pathname,
                b.name,
                gen_content(),
                before=Exec.ref(dirname),
                owner='root',
                group='root',
                mode='0644',
                source='puppet:///modules/{0}{1}'.format(b.name, pathname)))
        if '.zip' == pathname[-4:]:
            m['sources'].add(Exec('unzip {0}'.format(pathname),
                                  alias=dirname,
                                  cwd=dirname))
        else:
            m['sources'].add(Exec('tar xf {0}'.format(pathname),
                                  alias=dirname,
                                  cwd=dirname))

    def file(pathname, f):
        """
        Create a file resource.
        """
        if 'template' in f:
            logging.warning('file template {0} won\'t appear in generated '
                            'Puppet modules'.format(pathname))
            return

        # Create resources for parent directories and let the
        # autorequire mechanism work out dependencies.
        dirnames = os.path.dirname(pathname).split('/')[1:]
        for i in xrange(len(dirnames)):
            m['files'].add(File(os.path.join('/', *dirnames[0:i + 1]),
                                ensure='directory'))

        # Create the actual file resource.
        if '120000' == f['mode'] or '120777' == f['mode']:
            m['files'].add(File(pathname,
                                None,
                                None,
                                owner=f['owner'],
                                group=f['group'],
                                ensure=f['content']))
            return
        if 'source' in f:
            m['files'].add(Exec(
                'curl -o "{0}" "{1}" || wget -O "{0}" "{1}"'.
                    format(pathname, f['source']),
                before=File.ref(pathname),
                creates=pathname,
                require=File.ref(os.path.dirname(pathname))))
            m['files'].add(File(pathname,
                                owner=f['owner'],
                                group=f['group'],
                                mode=f['mode'][-4:],
                                ensure='file'))
        else:
            content = f['content']
            if 'base64' == f['encoding']:
                content = base64.b64decode(content)
            m['files'].add(File(pathname,
                                b.name,
                                content,
                                owner=f['owner'],
                                group=f['group'],
                                mode=f['mode'][-4:],
                                ensure='file'))

    deps = []
    def before_packages(manager):
        """
        Create exec resources to configure the package managers.
        """
        packages = b.packages.get(manager, [])
        if 0 == len(packages):
            return
        if 1 == len(packages) and manager in packages:
            return
        if 'apt' == manager:
            m['packages'].add(Exec('apt-get -q update',
                                   before=Class.ref('apt')))
        elif 'yum' == manager:
            m['packages'].add(Exec('yum makecache', before=Class.ref('yum')))
        deps.append(manager)

    def package(manager, package, version):
        """
        Create a package resource.
        """
        ensure = 'installed' if relaxed or version is None else version

        # `apt` and `yum` are easy since they're the default for their
        # respective platforms.
        if manager in ('apt', 'yum'):
            m['packages'][manager].add(Package(package, ensure=ensure))

            # If APT is installing RubyGems, get complicated.  This would
            # make sense to do with Yum, too, but there's no consensus on
            # where, exactly, you might find RubyGems from Yum.  Going
            # the other way, it's entirely likely that doing this sort of
            # forced upgrade goes against the spirit of Blueprint itself.
            match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
            if match is not None and util.rubygems_update():
                m['packages'][manager].add(Exec('/bin/sh -c "' # No ,
                    '/usr/bin/gem{0} install --no-rdoc --no-ri ' # No ,
                    'rubygems-update; /usr/bin/ruby{0} ' # No ,
                    '$(PATH=$PATH:/var/lib/gems/{0}/bin ' # No ,
                    'which update_rubygems)"'.format(match.group(1)),
                    require=Package.ref(package)))

            if 'nodejs' == package:
                m['packages'][manager].add(Exec('/bin/sh -c " { ' # No ,
                    'curl http://npmjs.org/install.sh || ' # No ,
                    'wget -O- http://npmjs.org/install.sh ' # No ,
                    '} | sh"',
                    creates='/usr/bin/npm',
                    require=Package.ref(package)))

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        elif 'rpm' == manager:
            m['packages']['rpm'].add(Package(package,
                                             ensure='installed',
                                             provider='rpm',
                                             source=version))

        # RubyGems for Ruby 1.8 is easy, too, because Puppet has a
        # built in provider.  This is called simply "rubygems" on
        # RPM-based distros.
        elif manager in ('rubygems', 'rubygems1.8'):
            m['packages'][manager].add(Package(package,
                                               ensure=ensure,
                                               provider='gem'))

        # Other versions of RubyGems are slightly more complicated.
        elif re.search(r'ruby', manager) is not None:
            match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)',
                             manager)
            m['packages'][manager].add(Exec(
                manager(package, version, relaxed),
                creates='{0}/{1}/gems/{2}-{3}'.format(util.rubygems_path(),
                                                      match.group(1),
                                                      package,
                                                      version)))

        # Python works basically like alternative versions of Ruby
        # but follows a less predictable directory structure so the
        # directory is not known ahead of time.  This just so happens
        # to be the way everything else works, too.
        else:
            m['packages'][manager].add(Exec(manager(package,
                                                    version,
                                                    relaxed)))

    restypes = {'files': File,
                'packages': Package,
                'sources': Exec}
    def service(manager, service):
        """
        Create a service resource and subscribe to its dependencies.
        """

        # Transform dependency list into a subscribe parameter.
        subscribe = []
        def service_file(m, s, pathname):
            subscribe.append(File.ref(pathname))
        walk.walk_service_files(b, manager, service, service_file=service_file)
        def service_package(m, s, pm, package):
            subscribe.append(Package.ref(package))
        walk.walk_service_packages(b,
                                   manager,
                                   service,
                                   service_package=service_package)
        def service_source(m, s, dirname):
            subscribe.append(Exec.ref(b.sources[dirname]))
        walk.walk_service_sources(b,
                                  manager,
                                  service,
                                  service_source=service_source)

        kwargs = {'enable': True,
                  'ensure': 'running',
                  'subscribe': subscribe}
        if 'upstart' == manager:
            kwargs['provider'] = 'upstart'
        m['services'][manager].add(Service(service, **kwargs))

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)
    if 1 < len(deps):
        m['packages'].dep(*[Class.ref(dep) for dep in deps])

    # Strict ordering of classes.  Don't bother with services since
    # they manage their own dependencies.
    deps = []
    if 0 < len(b.sources):
        deps.append('sources')
    if 0 < len(b.files):
        deps.append('files')
    if 0 < len(b.packages):
        deps.append('packages')
    if 1 < len(deps):
        m.dep(*[Class.ref(dep) for dep in deps])

    return m


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
        if name is None:
            self.name = 'blueprint-generated-puppet-module'
        else:
            self.name, _ = re.subn(r'\.', '--', unicode(name))
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
        w(u'{0}class {1} {{\n'.format(tab, self.name))
        tab_extra = '{0}\t'.format(tab)

        # Type-level defaults.
        for type, resource in sorted(self.defaults.iteritems()):
            w(resource.dumps(inline, tab_extra))

        # Declare relationships between resources that appear outside the
        # scope of individual resources.
        for deps in self.deps:
            w(u'{0}{1}\n'.format(tab_extra,
                                 ' -> '.join([repr(dep) for dep in deps])))

        # Resources in this manifest.
        for type, resources in sorted(self.resources.iteritems()):
            if 1 < len(resources):
                w(u'{0}{1} {{\n'.format(tab_extra, type))
                for name, resource in sorted(resources.iteritems()):
                    resource.style = Resource.PARTIAL
                    w(resource.dumps(inline, tab_extra))
                w(u'{0}}}\n'.format(tab_extra))
            elif 1 == len(resources):
                w(resources.values()[0].dumps(inline, tab_extra))

        # Child manifests.
        for name, manifest in sorted(self.manifests.iteritems()):
            manifest._dump(w, inline, tab_extra)

        # Close the class.
        w(u'{0}}}\n'.format(tab))

        # Include the class that was just defined in its parent.  Everything
        # is included but is still namespaced.
        if self.parent is not None:
            w(u'{0}include {1}\n'.format(tab, self.name))

    def dumps(self):
        """
        Generate a string containing Puppet code and all file contents.
        This output would be suitable for use with `puppet apply` or for
        displaying an entire blueprint on a single web page.
        """
        out = []
        self._dump(out.append, inline=True)
        return u''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing Puppet code and templates.  The directory
        structure generated is that of a module named by the main manifest.
        """
        os.mkdir(self.name)
        os.mkdir(os.path.join(self.name, 'manifests'))
        filename = os.path.join(self.name, 'manifests/init.pp')
        f = codecs.open(filename, 'w', encoding='utf-8')
        self._dump(f.write, inline=False)
        f.close()
        for pathname, dirname, content in self.files():
            pathname = os.path.join(self.name, dirname, pathname[1:])
            try:
                os.makedirs(os.path.dirname(pathname))
            except OSError as e:
                if errno.EEXIST != e.errno:
                    raise e
            if isinstance(content, unicode):
                f = codecs.open(pathname, 'w', encoding='utf-8')
            else:
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
        return u'{0}[\'{1}\']'.format(self.type.capitalize(), self.name)

    @property
    def type(self):
        """
        The type of a resource is read-only and derived from the class name.
        """
        return self._type

    @classmethod
    def _dumps(cls, value, bare=True):
        """
        Return a value as it should be written.
        """
        if value is None:
            return 'undef'
        elif True == value:
            return 'true'
        elif False == value:
            return 'false'
        elif any([isinstance(value, t) for t in (int, long, float)]):
            return value
        elif bare and re.match(r'^[0-9a-zA-Z]+$', u'{0}'.format(
            value)) is not None:
            return value
        elif hasattr(value, 'bare') or isinstance(value, util.BareString):
            return value.replace(u'$', u'\\$')
        elif isinstance(value, Resource):
            return repr(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            if 1 == len(value):
                return cls._dumps(value[0])
            else:
                return '[' + ', '.join([cls._dumps(v) for v in value]) + ']'
        return repr(unicode(value).replace(u'$', u'\\$'))[1:]

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
            out.append(u'{0}{1} {{ {2}:'.format(tab,
                                                self.type,
                                                self._dumps(self.name, False)))
        elif self.PARTIAL == self.style:
            out.append(u'{0}\t{1}:'.format(tab, self._dumps(self.name, False)))
            tab_params = '{0}\t'.format(tab)
        elif self.DEFAULTS == self.style:
            out.append(u'{0}{1} {{'.format(tab, self.type.capitalize()))

        # Handle resources with parameters.
        if 0 < len(self):

            # Find the maximum parameter name length so => operators will
            # line up as coding standards dictate.
            l = max([len(key) for key in self.iterkeys()])

            # Serialize parameter values.  Certain values don't require
            # quotes.
            for key, value in sorted(self.iteritems()):
                key = u'{0}{1}'.format(key, ' ' * (l - len(key)))
                out.append(u'{0}\t{1} => {2},'.format(tab_params,
                                                      key,
                                                      self._dumps(value)))

            # Close the resource as the style dictates.
            if self.COMPLETE == self.style:
                out.append(u'{0}}}\n'.format(tab))
            elif self.PARTIAL == self.style:
                out.append(u'{0};\n'.format(out.pop()[0:-1]))
            elif self.DEFAULTS == self.style:
                out.append(u'{0}}}\n'.format(tab))

        # Handle resources without parameters.
        else:
            if self.COMPLETE == self.style:
                out.append(u'{0} }}\n'.format(out.pop()))
            elif self.PARTIAL == self.style:
                out.append(u'{0};\n'.format(out.pop()))
            elif self.DEFAULTS == self.style:
                out.append(u'{0}}}\n'.format(out.pop()))

        return '\n'.join(out)


class Class(Resource):
    """
    Puppet class resource.
    """

    def __repr__(self):
        """
        Puppet class resource names cannot contain dots due to limitations
        in the grammar.
        """
        name, count = re.subn(r'\.', '--', unicode(self.name))
        return u'{0}[\'{1}\']'.format(self.type.capitalize(), name)


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

            # TODO Leaky abstraction.  The source attribute is perfectly
            # valid but the check here assumes it is only ever used for
            # placing source tarballs.
            if 'source' in self:
                raise ValueError("source tarballs can't be dumped as strings.")

            if getattr(self, 'content', None) is not None:
                self['content'] = self.content
                del self.content
        else:
            if self.content is not None and 'source' not in self:
                self['content'] = util.BareString(u'template(\'{0}/{1}\')'.
                                                  format(self.modulename,
                                                         self.name[1:]))
        return super(File, self).dumps(inline, tab)


class Exec(Resource):
    """
    Puppet exec resource.
    """
    pass


class Package(Resource):
    """
    Puppet package resource.
    """
    pass


class Service(Resource):
    """
    Puppet service resource.
    """
    pass
