"""
Shell code generator.
"""

import codecs
import gzip as gziplib
import os
import os.path
import re
import tarfile


from blueprint import git
from blueprint import util


def sh(b, server='https://devstructure.com', secret=None):
    """
    Generate shell code.
    """
    s = Script(b.name, comment=b.DISCLAIMER)

    # Extract source tarballs.
    if secret is not None:
        for dirname, filename in sorted(b.sources.iteritems()):
            s.add('wget "{0}/{1}/{2}/{3}"', server, secret, b.name, filename)
            s.add('tar xf "{0}" -C "{1}"', filename, dirname)
    else:
        tree = git.tree(b._commit)
        for dirname, filename in sorted(b.sources.iteritems()):
            blob = git.blob(tree, filename)
            content = git.content(blob)
            s.add('tar xf "{0}" -C "{1}"',
                  filename,
                  dirname,
                  sources={filename: content})

    # Place files.
    for pathname, f in sorted(b.files.iteritems()):
        s.add('mkdir -p "{0}"', os.path.dirname(pathname))
        if '120000' == f['mode'] or '120777' == f['mode']:
            s.add('ln -s "{0}" "{1}"', f['content'], pathname)
            continue
        command = 'base64 --decode' if 'base64' == f['encoding'] else 'cat'
        eof = 'EOF'
        while re.search(r'{0}'.format(eof), f['content']):
            eof += 'EOF'
        s.add('{0} >"{1}" <<{2}', command, pathname, eof)
        s.add(raw=f['content'])
        if 0 < len(f['content']) and '\n' != f['content'][-1]:
            eof = '\n{0}'.format(eof)
        s.add(eof)
        if 'root' != f['owner']:
            s.add('chown {0} "{1}"', f['owner'], pathname)
        if 'root' != f['group']:
            s.add('chgrp {0} "{1}"', f['group'], pathname)
        if '000644' != f['mode']:
            s.add('chmod {0} "{1}"', f['mode'][-4:], pathname)

    # Install packages.
    def before(manager):
        if 0 == len(manager):
            return
        if 'apt' == manager.name:
            s.add('export APT_LISTBUGS_FRONTEND="none"')
            s.add('export APT_LISTCHANGES_FRONTEND="none"')
            s.add('export DEBIAN_FRONTEND="noninteractive"')
            s.add('apt-get -q update')
        elif 'yum' == manager.name:
            s.add('yum makecache')

    def package(manager, package, version):
        if manager.name == package:
            return
        s.add(manager(package, version))
        if manager.name not in ('apt', 'yum'):
            return

        # See comments on this section in `puppet` above.
        match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
        if match is not None and util.rubygems_update():
            s.add('/usr/bin/gem{0} install --no-rdoc --no-ri ' # No ,
                  'rubygems-update', match.group(1))
            s.add('/usr/bin/ruby{0} $(PATH=$PATH:/var/lib/gems/{0}/bin ' # No ,
                  'which update_rubygems)', match.group(1))

    b.walk(before=before, package=package)

    return s


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
            self.out.append(kwargs['raw'].
                replace(u'$', u'\\$').
                replace(u'`', u'\\`'))
        else:
            self.out.append(u'{0}\n'.format(s).format(*args))
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
