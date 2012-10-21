"""
Shell code generator.
"""

import codecs
from collections import defaultdict
import gzip as gziplib
import os
import os.path
import re
from shutil import copyfile
import tarfile
import unicodedata

from blueprint import git
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

    commit = git.rev_parse(b.name)
    tree = None if commit is None else git.tree(commit)
    def source(dirname, filename, gen_content, url):
        """
        Extract a source tarball.
        """
        if dirname in lut['sources']:
            s.add('MD5SUM="$(find "{0}" -printf %T@\\\\n | md5sum)"',
                  args=(dirname,))
        if url is not None:
            s.add_list(('curl -o "{0}" "{1}"',),
                       ('wget -O "{0}" "{1}"',),
                       args=(filename, url),
                       operator='||')
            if '.zip' == pathname[-4:]:
                s.add('unzip "{0}" -d "{1}"', args=(filename, dirname))
            else:
                s.add('mkdir -p "{1}" && tar xf "{0}" -C "{1}"', args=(filename, dirname))
        elif secret is not None:
            s.add_list(('curl -O "{0}/{1}/{2}/{3}"',),
                       ('wget "{0}/{1}/{2}/{3}"',),
                       args=(server, secret, b.name, filename),
                       operator='||')
            s.add('mkdir -p "{1}" && tar xf "{0}" -C "{1}"', args=(filename, dirname))
        elif gen_content is not None:
            s.add('mkdir -p "{1}" && tar xf "{0}" -C "{1}"', args=(filename, dirname))
            s.add_source(filename, git.blob(tree, filename))
        for manager, service in lut['sources'][dirname]:
            s.add_list(('[ "$MD5SUM" != "$(find "{0}" -printf %T@\\\\n '
                        '| md5sum)" ]',),
                       ('{1}=1',),
                       args=(dirname, manager.env_var(service)),
                       operator='&&')

    def file(pathname, f):
        """
        Place a file.
        """
        if pathname in lut['files']:
            s.add('MD5SUM="$(md5sum "{0}" 2>/dev/null)"', args=(pathname,))
        s.add('mkdir -p "{0}"', args=(os.path.dirname(pathname),))
        if '120000' == f['mode'] or '120777' == f['mode']:
            s.add('ln -s "{0}" "{1}"', args=(f['content'], pathname))
        else:
            if 'source' in f:
                s.add_list(('curl -o "{0}" "{1}"',),
                           ('wget -O "{0}" "{1}"',),
                           args=(pathname, f['source']),
                           operator='||')
            else:
                if 'template' in f:
                    s.templates = True
                    if 'base64' == f['encoding']:
                        commands = ('base64 --decode', 'mustache')
                    else:
                        commands = ('mustache',)
                    s.add_list(('set +x',),
                               ('. "lib/mustache.sh"',),
                               ('for F in */blueprint-template.d/*.sh',),
                               ('do',),
                               ('\t. "$F"',),
                               ('done',),
                               (f.get('data', '').rstrip(),),
                               (command(*commands,
                                        escape_stdin=True,
                                        stdin=f['template'],
                                        stdout=pathname),),
                               operator='\n',
                               wrapper='()')
                else:
                    if 'base64' == f['encoding']:
                        commands = ('base64 --decode',)
                    else:
                        commands = ('cat',)
                    s.add(*commands, stdin=f['content'], stdout=pathname)
            if 'root' != f['owner']:
                s.add('chown {0} "{1}"', args=(f['owner'], pathname))
            if 'root' != f['group']:
                s.add('chgrp {0} "{1}"', args=(f['group'], pathname))
            if '100644' != f['mode']:
                s.add('chmod {0} "{1}"', args=(f['mode'][-4:], pathname))
        for manager, service in lut['files'][pathname]:
            s.add('[ "$MD5SUM" != "$(md5sum "{0}")" ] && {1}=1',
                  args=(pathname, manager.env_var(service)))

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
            s.add_list((manager.gate(package, version, relaxed),),
                       (command_list((manager.install(package,
                                                      version,
                                                      relaxed),),
                                     *[('{0}=1'.format(m.env_var(service)),)
                                       for m, service in
                                       lut['packages'][manager][package]],
                                     wrapper='{{}}'),),
                       operator='||')
        else:
            s.add(manager(package, version, relaxed))

        if manager not in ('apt', 'rpm', 'yum'):
            return

        # See comments on this section in `blueprint.frontend.puppet`.
        match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
        if match is not None and util.rubygems_update():
            s.add('/usr/bin/gem{0} install --no-rdoc --no-ri rubygems-update',
                  args=(match.group(1),))
            s.add('/usr/bin/ruby{0} $(PATH=$PATH:/var/lib/gems/{0}/bin '
                  'which update_rubygems)',
                  args=(match.group(1),))

        if 'nodejs' == package:
            s.add_list(('which npm',),
                       (command_list(('curl http://npmjs.org/install.sh',),
                                     ('wget -O- http://npmjs.org/install.sh',),
                                     operator='||',
                                     wrapper='{{}}'),
                        'sh'),
                operator='||')

    def service(manager, service):
        s.add(manager(service))

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)

    return s


def command(*commands, **kwargs):
    commands = list(commands)
    if 'stdout' in kwargs:
        commands[-1] += ' >"{0}"'.format(kwargs['stdout'])
    if 'stdin' in kwargs:
        stdin = (kwargs['stdin'].replace(u'\\', u'\\\\').
                                 replace(u'$', u'\\$').
                                 replace(u'`', u'\\`'))
        if kwargs.get('escape_stdin', False):
            stdin = stdin.replace(u'{', u'{{').replace(u'}', u'}}')
        eof = 'EOF'
        while eof in stdin:
            eof += 'EOF'
        commands[0] += ' <<{0}'.format(eof)
        return ''.join([' | '.join(commands).format(*kwargs.get('args', ())),
                        '\n',
                        stdin,
                        '' if '' == stdin or '\n' == stdin[-1] else '\n',
                        eof])
    return ' | '.join(commands).format(*kwargs.get('args', ()))


def command_list(*commands, **kwargs):
    operator = {'&&': u' && ',
                '||': u' || ',
                '\n': u'\n',
                ';': u'; '}[kwargs.get('operator', ';')]
    wrapper = {'()': (u'(\n', u'\n)') if u'\n' == operator else (u'(', u')'),
               '{}': (u'{ ', u'; }'),
               '{{}}': (u'{{ ', u'; }}'), # Prevent double-escaping.
               '': (u'', u'')}[kwargs.get('wrapper', '')]
    return wrapper[0] \
         + operator.join([command(*c, **kwargs) for c in commands]) \
         + wrapper[-1]


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
        self.templates = False

    def add(self, s='', *args, **kwargs):
        self.out.append((unicode(s) + u'\n').format(*args))
        for filename, content in kwargs.get('sources', {}).iteritems():
            self.sources[filename] = content

    def add(self, *args, **kwargs):
        """
        Add a command or pipeline to the `Script`.  Each positional `str`
        is an element in the pipeline.  The keyword argument `args`, if
        present, should contain an iterable of arguments to be substituted
        into the final pipeline by the new-style string formatting library.
        """
        self.out.append(command(*args, **kwargs))

    def add_list(self, *args, **kwargs):
        """
        Add a command or pipeline, or list of commands or pipelines, to
        the `Script`.  Each positional `str` or `tuple` argument is a
        pipeline.  The keyword argument `operator`, if present, must be
        `';'`, `'&&'`, or `'||'` to control how the pipelines are joined.
        The keyword argument `stdin`, if present, should contain a string
        that will be given heredoc-style.  The keyword argument `stdout`,
        if present, should contain a string pathname that will receive
        standard output.  The keyword argument `args`, if present, should
        contain an iterable of arguments to be substituted into the final
        pipeline by the new-style string formatting library.
        """
        self.out.append(command_list(*args, **kwargs))

    def add_source(self, filename, blob):
        """
        Add a reference to a source tarball to the `Script`.  It will be
        placed in the output directory/tarball later via `git-cat-file`(1).
        """
        self.sources[filename] = blob

    def dumps(self):
        """
        Generate a string containing shell code and all file contents.
        """
        return ''.join(self.out)

    def dumpf(self, gzip=False):
        """
        Generate a file containing shell code and all file contents.
        """

        # Open a file by the correct name, possibly with inline gzipping.
        if 0 < len(self.sources) or self.templates:
            os.mkdir(self.name)
            filename = os.path.join(self.name, 'bootstrap.sh')
            f = codecs.open(filename, 'w', encoding='utf-8')
        elif gzip:
            filename = '{0}.sh.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.sh'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')

        # Bring along `mustache.sh`, the default template data files, and
        # any user-provided template data files.
        if self.templates:
            os.mkdir(os.path.join(self.name, 'etc'))
            os.mkdir(os.path.join(self.name, 'etc', 'blueprint-template.d'))
            os.mkdir(os.path.join(self.name, 'lib'))
            os.mkdir(os.path.join(self.name, 'lib', 'blueprint-template.d'))
            copyfile(os.path.join(os.path.dirname(__file__), 'mustache.sh'),
                     os.path.join(self.name, 'lib', 'mustache.sh'))
            for src, dest in [('/etc/blueprint-template.d', 'etc'),
                              (os.path.join(os.path.dirname(__file__),
                                            'blueprint-template.d'),
                               'lib')]:
                try:
                    for filename2 in os.listdir(src):
                        if filename2.endswith('.sh'):
                            copyfile(os.path.join(src, filename2),
                                     os.path.join(self.name,
                                                  dest,
                                                  'blueprint-template.d',
                                                  filename2))
                except OSError:
                    pass

        # Write the actual shell code.
        for out in self.out:
            if isinstance(out, unicode):
                out = unicodedata.normalize('NFKD', out).encode('utf-8', 'ignore')
            f.write('{0}\n'.format(out))
        f.close()

        # Bring source tarballs along.
        for filename2, blob in sorted(self.sources.iteritems()):
            git.cat_file(blob, os.path.join(self.name, filename2))

        # Possibly gzip the result.
        if gzip and (0 < len(self.sources) or self.templates):
            filename = 'sh-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename

        return filename
