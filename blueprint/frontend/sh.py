"""
Shell code generator.
"""

import codecs
from collections import defaultdict
import gzip as gziplib
import os
import os.path
import re
import tarfile

from blueprint import util


def sh(b, relaxed=False, server='https://devstructure.com', secret=None):
    """
    Generate shell code.
    """
    s = Script(b.name, comment=b.DISCLAIMER)

    # Build an inverted index (lookup table, like in hardware, hence the name)
    # of service dependencies to services.
    lut = {'files': defaultdict(set),
           'packages': defaultdict(lambda: defaultdict(set)),
           'sources': defaultdict(set)}
    def service_file(manager, service, pathname):
        lut['files'][pathname].add((manager, service))
    def service_package(manager, service, package_manager, package):
        lut['packages'][package_manager][package].add((manager, service))
    def service_source(manager, service, dirname):
        lut['sources'][dirname].add((manager, service))
    b.walk(service_file=service_file,
           service_package=service_package,
           service_source=service_source)

    def source(dirname, filename, gen_content, url):
        """
        Extract a source tarball.
        """
        if dirname in lut['sources']:
            s.add('MD5SUM="$(find "{0}" -printf %T@\\\\n | md5sum)"', dirname)
        if url is not None:
            s.add('curl -o "{0}" "{1}" || wget -O "{0}" "{1}"', filename, url)
            if '.zip' == pathname[-4:]:
                s.add('unzip "{0}" -d "{1}"', filename, dirname)
            else:
                s.add('tar xf "{0}" -C "{1}"', filename, dirname)
        elif secret is not None:
            s.add('curl -O "{0}/{1}/{2}/{3}" || wget "{0}/{1}/{2}/{3}"',
                  server,
                  secret,
                  b.name,
                  filename)
            s.add('tar xf "{0}" -C "{1}"', filename, dirname)
        elif gen_content is not None:
            s.add('tar xf "{0}" -C "{1}"',
                  filename,
                  dirname,
                  sources={filename: gen_content()})
        for manager, service in lut['sources'][dirname]:
            s.add('[ "$MD5SUM" != "$(find "{0}" -printf %T@\\\\n ' # No ,
                  '| md5sum)" ] && {1}=1',
                  dirname,
                  manager.env_var(service))

    def file(pathname, f):
        """
        Place a file.
        """
        if pathname in lut['files']:
            s.add('MD5SUM="$(md5sum "{0}" 2>/dev/null)"', pathname)
        s.add('mkdir -p "{0}"', os.path.dirname(pathname))
        if '120000' == f['mode'] or '120777' == f['mode']:
            s.add('ln -s "{0}" "{1}"', f['content'], pathname)
        else:
            if 'source' in f:
                s.add('curl -o "{0}" "{1}" || wget -O "{0}" "{1}"',
                      pathname,
                      f['source'])
            else:
                eof = 'EOF'
                while re.search(r'{0}'.format(eof), f['content']):
                    eof += 'EOF'
                s.add(
                    '{0} >"{1}" <<{2}',
                    'base64 --decode' if 'base64' == f['encoding'] else 'cat',
                    pathname,
                    eof)
                s.add(raw=f['content'])
                if 0 < len(f['content']) and '\n' != f['content'][-1]:
                    eof = '\n{0}'.format(eof)
                s.add(eof)
            if 'root' != f['owner']:
                s.add('chown {0} "{1}"', f['owner'], pathname)
            if 'root' != f['group']:
                s.add('chgrp {0} "{1}"', f['group'], pathname)
            if '100644' != f['mode']:
                s.add('chmod {0} "{1}"', f['mode'][-4:], pathname)
        for manager, service in lut['files'][pathname]:
            s.add('[ "$MD5SUM" != "$(md5sum "{0}")" ] && {1}=1',
                  pathname,
                  manager.env_var(service))

    def before_packages(manager):
        """
        Configure the package managers.
        """
        if manager not in b.packages:
            return
        if 'apt' == manager:
            s.add('export APT_LISTBUGS_FRONTEND="none"')
            s.add('export APT_LISTCHANGES_FRONTEND="none"')
            s.add('export DEBIAN_FRONTEND="noninteractive"')
            s.add('apt-get -q update')
        elif 'yum' == manager:
            s.add('yum makecache')

    def package(manager, package, version):
        """
        Install a package.
        """
        if manager == package:
            return

        if manager in lut['packages'] and package in lut['packages'][manager]:
            env_vars = ['{0}=1'.format(m.env_var(service))
                        for m, service in lut['packages'][manager][package]]
            s.add(manager.gate(package, version, relaxed) + ' || {{ ' \
                  + manager.install(package, version, relaxed) + '; ' \
                  + '; '.join(env_vars) + '; }}')
        else:
            s.add(manager(package, version, relaxed))

        if manager not in ('apt', 'rpm', 'yum'):
            return

        # See comments on this section in `blueprint.frontend.puppet`.
        match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
        if match is not None and util.rubygems_update():
            s.add('/usr/bin/gem{0} install --no-rdoc --no-ri ' # No ,
                  'rubygems-update', match.group(1))
            s.add('/usr/bin/ruby{0} $(PATH=$PATH:/var/lib/gems/{0}/bin ' # No ,
                  'which update_rubygems)', match.group(1))

        if 'nodejs' == package:
            s.add('which npm || {{ ' # No ,
                  'curl http://npmjs.org/install.sh || ' # No ,
                  'wget -O- http://npmjs.org/install.sh ' # No ,
                  '}} | sh')

    def service(manager, service):
        s.add(manager(service))

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)

    return s


class Script(object):
    """
    A script is a list of shell commands.  The pomp and circumstance is
    only necessary for providing an interface like the Puppet and Chef
    code generators.
    """

    def __init__(self, name, comment=None):
        if name is None:
            self.name = 'blueprint-generated-shell-script'
        else:
            self.name = name
        self.out = [comment if comment is not None else '',
                    'set -x\n',
                    'cd "$(dirname "$0")"\n']
        self.sources = {}

    def add(self, s='', *args, **kwargs):
        if 'raw' in kwargs:
            self.out.append(kwargs['raw'].
                replace(u'\\', u'\\\\').
                replace(u'$', u'\\$').
                replace(u'`', u'\\`'))
        else:
            self.out.append((unicode(s) + u'\n').format(*args))
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
            f = codecs.open(filename, 'w', encoding='utf-8')
        elif gzip:
            filename = '{0}.sh.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.sh'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')
        for out in self.out:
            f.write(out)
        f.close()
        for filename2, content in sorted(self.sources.iteritems()):
            f2 = open(os.path.join(self.name, filename2), 'w')
            f2.write(content)
            f2.close()
        if gzip and 0 != len(self.sources):
            filename = 'sh-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return filename
