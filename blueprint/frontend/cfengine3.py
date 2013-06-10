"""
CFEngine 3 code generator.
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
import time
import copy

import json
from pprint import pprint

from blueprint import util
from blueprint import walk

def cfengine3(b, relaxed=False):
    """
    Generate CFEngine 3 code.
    """

    s = Sketch(b.name, policy="main.cf", comment=b.DISCLAIMER)
    # print json.dumps(b, skipkeys=True, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))

    # # Set the default `PATH` for exec resources.
    # m.add(Exec.defaults(path=os.environ['PATH']))

    def source(dirname, filename, gen_content, url):
        """
        Create file and exec resources to fetch and extract a source tarball.
        """
        s.add(Source(dirname, filename, gen_content, url));

    def file(pathname, f):
        """
        Create a file promise.
        """
        s.add(File(pathname, f))

    def package(manager, package, version):
        """
        Create a package resource.
        """
        s.add(Package(package, manager, version))

    def service(manager, service):
        """
        Create a service resource and subscribe to its dependencies.
        """
        s.add(Service(service, manager))

    b.walk(source=source,
           file=file,
           # before_packages=before_packages,
           package=package,
           service=service)

    return s

class Sketch(object):
    """
    A CFEngine 3 sketch contains any deliverables in file format.
    """

    def __init__(self, name, policy="main.cf", comment=None):
        """
        Each sketch has a name.
        """
        if name is None:
            self.name = "unknown_blueprint"
        else:
            self.name = name

        self.sketch_name = time.strftime('Blueprint::Sketch::%%s::%Y-%m-%d') % (self.name)
        self.comment = comment
        self.namespace = "blueprint_%s" % (self.name)
        self.policy = Policy(self, name=policy)
        self.dependencies = { "CFEngine::stdlib": { "version": 105 }, "CFEngine::dclib": {}, "CFEngine::Blueprint": {}, "cfengine": { "version": "3.5.0" } }
        self.contents = [ self.policy ]

    def add(self, p):
        if isinstance(p, File):
            self.contents.append(p)

        self.policy.add(p)

    def allfiles(self):
        """
        Generate the pathname and content of every file.
        """
        for item in self.contents:
            yield item.pathname, item.dirname if hasattr(item, "dirname") else "", item.content if hasattr(item, "content") else "", item.meta if hasattr(item, "meta") else {}

    def make_manifest(self):
        """
        Generate the sketch manifest.
        """
        ret = {}
        for pathname, dirname, content, meta in self.allfiles():
           ret[os.path.join(dirname, pathname[1:])] = meta

        return ret

    def make_metadata(self):
        """
        Generate the sketch manifest.
        """
        ret = { "name": self.name,
                "description": "Auto-generated sketch from Blueprint",
                "version": 1,
                "license": "unspecified",
                "tags": [ "blueprint" ],
                "depends": self.dependencies,
                "authors": [ "Your Name Here" ],
        }

        return ret

    def make_api(self):
        """
        Generate the sketch API.
        """
        return { "install": [ { "name": "runenv", "type": "environment" },
                              { "name" : "metadata", "type" : "metadata" },
                          ],
        }

    def _dump(self, w, inline=False, tab=''):
        """
        Generate the sketch index, `sketch.json`.  This will call the callable
        `w` with each line of output.  `dumps` and `dumpf` use this to
        append to a list and write to a file with the same code.

        If present, a comment is written first.  This is followed by the JSON data.

        """

        if self.comment is not None:
            comment, count = re.subn(r'#', '//', unicode(self.comment))
            w(comment)
        w(json.dumps({ "manifest": self.make_manifest(),
                       "metadata": self.make_metadata(),
                       "namespace": self.namespace,
                       "interface": [ self.policy.interface ],
                       "api": self.make_api(),
                   },
                     skipkeys=True, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': ')))

    def dumps(self):
        """
        Generate a string containing `sketch.json` only.
        """
        out = []
        self._dump(out.append, inline=True)
        return u''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing CFEngine 3 code and templates.  The directory
        structure generated is a sketch (sketch.json plus all the rest).
        """
        os.mkdir(self.name)
        filename = os.path.join(self.name, 'sketch.json')
        f = codecs.open(filename, 'w', encoding='utf-8')
        self._dump(f.write, inline=False)
        f.close()

        self.policy.make_content()

        for pathname, dirname, content, meta in self.allfiles():
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
            filename = 'cfengine3-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename

        return filename

class Policy(object):
    """
    CFEngine 3 policy: a container for promises.
    """
    def __init__(self, sketch, name="main.cf"):
        """
        The policy name is its filename.
        """
        self.interface = name
        self.pathname = "/" + name
        self.promises = [ ]
        self.sketch = sketch

    def add(self, promise):
        self.promises.append(promise)

    def make_vars(self):
        """
        Generate the variables as CFEngine code.

        """
        v = { "files": {}, "sources": [], "package_manager": [], "service_manager": [] }
        for promise in self.promises:
            if isinstance(promise, File):
                v['files'][promise.pathname] = copy.deepcopy(promise.meta)
                # we do not support URL sources
                v['files'][promise.pathname]['source'] = promise.dirname + promise.pathname
                # TODO: source
            elif isinstance(promise, Source):
                logging.warning('TODO: CFEngine handler for Source promise {0}, {1}'.format(promise.filename, promise.dirname))
            #     v['sources'].append(promise.filename)
            #     v['sources'].append(promise.dirname)
            #     # v['sources'].append(promise.content)
            #     v['sources'].append(promise.url)
            elif isinstance(promise, Package):
                if not promise.manager in v['package_manager']:
                    v['package_manager'].append(promise.manager)
                v.setdefault('packages_' + promise.manager, {})[promise.name] = promise.version
            elif isinstance(promise, Service):
                logging.warning('TODO: CFEngine handler for Service promise {0}, {1}'.format(promise.manager, promise.name))
                # if not promise.manager in v['service_manager']:
                #     v['service_manager'].append(promise.manager)
                # v.setdefault('services_' + promise.manager, []).append(promise.name)

        # return json.dumps(v, skipkeys=True, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
        return cfe_recurse_print(v, "      "), v

    def make_content(self):
        """
        Generate the policy as CFEngine code and put it in 'content'.

        """
        myvars, v = self.make_vars()

        ns = self.sketch.namespace
        packages = "\n".join(map(lambda x: '      "packages %s" inherit => "true", usebundle => cfdc_blueprint:packages($(runenv), "%s", $(%s_packages), "$(blueprint_packages_%s[$(%s_packages)])");' % (x, x, x, x, x),
                                 v['package_manager']))

        packvars = "\n".join(map(lambda x: '      "%s_packages" slist => getindices("blueprint_packages_%s");' % (x, x),
                                 v['package_manager']))

        self.content = """
body file control
{
      namespace => "%s";
}

bundle agent install(runenv, metadata)
{
  classes:
      "$(vars)" expression => "default:runenv_$(runenv)_$(vars)";
      "not_$(vars)" expression => "!default:runenv_$(runenv)_$(vars)";

  vars:
      "vars" slist => { "@(default:$(runenv).env_vars)" };
      "$(vars)" string => "$(default:$(runenv).$(vars))";

      "all_files" slist => getindices("blueprint_files");

%s
%s

  methods:
      "utils" usebundle => default:eu($(runenv));

    activated::
     "files" inherit => "true", usebundle => cfdc_blueprint:files($(runenv), concat(dirname($(this.promise_filename)), "/files"), $(default:eu.path_prefix), $(all_files), "%s:install.blueprint_files[$(all_files)]");
%s  
      # "sources" inherit => "true", usebundle => cfdc_blueprint:sources($(runenv), dirname($(this.promise_filename)), $(blueprint_sources));

    verbose::
      "metadata" usebundle => default:report_metadata($(this.bundle), $(metadata)),
      inherit => "true";
}
""" % (ns, myvars, packvars, ns, packages)

class Promise(object):
    """
    CFEngine 3 base promise.
    """
    pass

class Package(Promise):
    """
    CFEngine 3 packages promise.  Only one version is supported.
    """
    def __init__(self, name, manager, version):
        """
        The policy name is a filename.
        """
        self.name = name
        manager, count = re.subn(r'\W', '_', unicode(manager))
        self.manager = manager
        self.version = version


class Service(Promise):
    """
    CFEngine 3 services promise.  Not implemented.
    """
    def __init__(self, service, manager):
        """
        The service name is a unique identifier.
        """
        self.name = service
        manager, count = re.subn(r'\W', '_', unicode(manager))
        self.manager = manager

class Source(Promise):
    """
    CFEngine 3 services promise.
    """
    def __init__(self, dirname, filename, content, url):
        """
        A source->destination mapping
        """
        self.dirname = dirname
        self.filename = filename
        self.content = content
        self.url = url

class File(Promise):
    """
    CFEngine 3 files promise.
    """
    def __init__(self, filename, f):
        """
        A file spec
        """
        self.pathname = filename
        self.dirname = "files"
        self.data = f

        self.meta = { "owner": f['owner'], "group": f['group'], "perms": "" + f['mode'][-4:] }

        self.content = f['content']
        if 'base64' == f['encoding']:
            self.content = base64.b64decode(self.content)

        if 'template' in f:
            logging.warning('TODO: CFEngine file template {0}'.format(pathname))
            return

def cfe_recurse_print(d, indent):
    """
    CFEngine 3 data dump (to arrays and slists).

    Currently only supports simple lists and one or two level dicts.
    """

    quoter = lambda x: x if re.match("concat\(", x) else "'%s'" % (x)
    lines = []

    for varname, value in d.iteritems():
        if isinstance(value, dict):
            for k, v in value.iteritems():
                if isinstance(v, dict):
                    for k2, v2 in v.iteritems():
                        lines.append("%s'blueprint_%s[%s][%s]' string => %s;" % (indent, varname, k, k2, quoter(v2)))
                else:
                    lines.append("%s'blueprint_%s[%s]' string => %s;" % (indent, varname, k, quoter(v)))
        elif isinstance(value, list):
            p = map(quoter, value)
            lines.append("%s'blueprint_%s' slist => { %s };" % (indent, varname, ", ".join(p)))
        else:
            logging.warning('Unsupported data in variable %s' % (varname))

    return "\n".join(lines)
