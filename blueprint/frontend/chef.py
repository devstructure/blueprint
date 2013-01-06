"""
Chef code generator.
"""

import base64
import codecs
import errno
import logging
import os
import os.path
import re
import tarfile

from blueprint import util
from blueprint import walk


def chef(b, relaxed=False):
    """
    Generate Chef code.
    """
    c = Cookbook(b.name, comment=b.DISCLAIMER)

    def source(dirname, filename, gen_content, url):
        """
        Create a cookbook_file and execute resource to fetch and extract
        a source tarball.
        """
        pathname = os.path.join('/tmp', filename)
        if url is not None:
            c.execute('curl -o "{0}" "{1}" || wget -O "{0}" "{1}"'.
                          format(pathname, url),
                      creates=pathname)
        elif gen_content is not None:
            c.file(pathname,
                   gen_content(),
                   owner='root',
                   group='root',
                   mode='0644',
                   backup=False,
                   source=pathname[1:])
        if '.zip' == pathname[-4:]:
            c.execute('{0}'.format(pathname),
                      command='unzip "{0}"'.format(pathname),
                      cwd=dirname)
        else:
            c.execute('{0}'.format(pathname),
                      command='tar xf "{0}"'.format(pathname),
                      cwd=dirname)

    def file(pathname, f):
        """
        Create a cookbook_file resource.
        """
        if 'template' in f:
            logging.warning('file template {0} won\'t appear in generated '
                            'Chef cookbooks'.format(pathname))
            return
        c.directory(os.path.dirname(pathname),
                    group='root',
                    mode='0755',
                    owner='root',
                    recursive=True)
        if '120000' == f['mode'] or '120777' == f['mode']:
            c.link(pathname,
                   group=f['group'],
                   owner=f['owner'],
                   to=f['content'])
            return
        if 'source' in f:
            c.remote_file(pathname,
                          backup=False,
                          group=f['group'],
                          mode=f['mode'][-4:],
                          owner=f['owner'],
                          source=f['source'])
        else:
            content = f['content']
            if 'base64' == f['encoding']:
                content = base64.b64decode(content)
            c.file(pathname,
                   content,
                   backup=False,
                   group=f['group'],
                   mode=f['mode'][-4:],
                   owner=f['owner'],
                   source=pathname[1:])

    def before_packages(manager):
        """
        Create execute resources to configure the package managers.
        """
        packages = b.packages.get(manager, [])
        if 0 == len(packages):
            return
        if 1 == len(packages) and manager in packages:
            return
        if 'apt' == manager:
            c.execute('apt-get -q update')
        elif 'yum' == manager:
            c.execute('yum makecache')

    def package(manager, package, version):
        """
        Create a package resource.
        """
        if manager == package:
            return

        if manager in ('apt', 'yum'):
            if relaxed or version is None:
                c.package(package)
            else:
                c.package(package, version=version)

            # See comments on this section in `puppet` above.
            match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
            if match is not None and util.rubygems_update():
                c.execute('/usr/bin/gem{0} install --no-rdoc --no-ri ' # No ,
                          'rubygems-update'.format(match.group(1)))
                c.execute('/usr/bin/ruby{0} ' # No ,
                          '$(PATH=$PATH:/var/lib/gems/{0}/bin ' # No ,
                          'which update_rubygems)"'.format(match.group(1)))

            if 'nodejs' == package:
                c.execute('{ ' # No ,
                          'curl http://npmjs.org/install.sh || ' # No ,
                          'wget -O- http://npmjs.org/install.sh ' # No ,
                          '} | sh',
                          creates='/usr/bin/npm')

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        elif 'rpm' == manager:
            c.rpm_package(package, source=version)

        # All types of gems get to have package resources.
        elif 'rubygems' == manager:
            if relaxed or version is None:
                c.gem_package(package)
            else:
                c.gem_package(package, version=version)
        elif re.search(r'ruby', manager) is not None:
            match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)',
                             manager)
            if relaxed or version is None:
                c.gem_package(package,
                    gem_binary='/usr/bin/gem{0}'.format(match.group(1)))
            else:
                c.gem_package(package,
                    gem_binary='/usr/bin/gem{0}'.format(match.group(1)),
                    version=version)

        # Everything else is an execute resource.
        else:
            c.execute(manager(package, version, relaxed))

    def service(manager, service):
        """
        Create a service resource and subscribe to its dependencies.
        """

        # Transform dependency list into a subscribes attribute.
        # TODO Breaks inlining.
        subscribe = []
        def service_file(m, s, pathname):
            f = b.files[pathname]
            if '120000' == f['mode'] or '120777' == f['mode']:
                subscribe.append('link[{0}]'.format(pathname))
            else:
                subscribe.append('cookbook_file[{0}]'.format(pathname))
        walk.walk_service_files(b, manager, service, service_file=service_file)
        def service_package(m, s, pm, package):
            subscribe.append('package[{0}]'.format(package))
        walk.walk_service_packages(b,
                                   manager,
                                   service,
                                   service_package=service_package)
        def service_source(m, s, dirname):
            subscribe.append('execute[{0}]'.format(b.sources[dirname]))
        walk.walk_service_sources(b,
                                  manager,
                                  service,
                                  service_source=service_source)
        subscribe = util.BareString('resources(' \
            + ', '.join([repr(s) for s in subscribe]) + ')')

        kwargs = {'action': [[':enable', ':start']],
                  'subscribes': [':restart', subscribe]}
        if 'upstart' == manager:
            kwargs['provider'] = util.BareString(
                'Chef::Provider::Service::Upstart')
        c.service(service, **kwargs)

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)

    return c


class Cookbook(object):
    """
    A cookbook is a collection of Chef resources plus the files and other
    supporting objects needed to run it.
    """

    def __init__(self, name, comment=None):
        """
        """
        if name is None:
            self.name = 'blueprint-generated-chef-cookbook'
        else:
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

    def remote_file(self, name, **kwargs):
        """
        Create a remote_file resource.
        """
        self.add(Resource('remote_file', name, **kwargs))

    def package(self, name, **kwargs):
        """
        Create a package resource provided by the default provider.
        """
        self.add(Resource('package', name, **kwargs))

    def rpm_package(self, name, **kwargs):
        """
        Create a package resource provided by RPM.
        """
        self.add(Resource('rpm_package', name, **kwargs))

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

    def service(self, name, **kwargs):
        """
        Create a service resource.
        """
        self.add(Resource('service', name, **kwargs))

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
        f = codecs.open(os.path.join(self.name, 'metadata.rb'), 'w', encoding='utf-8')
        f.close()
        os.mkdir(os.path.join(self.name, 'recipes'))
        filename = os.path.join(self.name, 'recipes/default.rb')
        f = codecs.open(filename, 'w', encoding='utf-8')
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
            if isinstance(resource.content, unicode):
                f = codecs.open(pathname, 'w', encoding='utf-8')
            else:
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

    @classmethod
    def _dumps(cls, value, recursive=False):
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
        elif any([isinstance(value, t) for t in (int, long, float)]):
            return value
        elif 1 < len(value) and ':' == value[0]:
            return value
        elif hasattr(value, 'bare') or isinstance(value, util.BareString):
            return value
        elif isinstance(value, cls):
            return repr(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            s = ', '.join([cls._dumps(v, True) for v in value])
            if recursive:
                return '[' + s + ']'
            else:
                return s
        return repr(unicode(value).replace(u'#{', u'\\#{'))[1:]

    def dumps(self, inline=False):
        """
        Stringify differently depending on the number of options so the
        output always looks like Ruby code should look.  Parentheses are
        always employed here due to grammatical inconsistencies when using
        braces surrounding a block.
        """
        if 0 == len(self):
            return u'{0}({1})\n'.format(self.type, self._dumps(self.name))
        elif 1 == len(self):
            key, value = self.items()[0]
            return u'{0}({1}) {{ {2} {3} }}\n'.format(self.type,
                                                      self._dumps(self.name),
                                                      key,
                                                      self._dumps(value))
        else:
            out = [u'{0}({1}) do\n'.format(self.type, self._dumps(self.name))]
            for key, value in sorted(self.iteritems()):
                out.append(u'  {0} {1}\n'.format(key, self._dumps(value)))
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
        elif self.content is not None and 'source' in self:
            self.type = 'cookbook_file'
        return super(File, self).dumps(inline)
