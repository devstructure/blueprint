"""
Implementation of the blueprint walking algorithm from `blueprint`(5).

It's critical that this implementation function over a naive
`dict`-of-`dict`s-of-`list`s (as constructed by `json.load` and `json.loads`)
as well as the true `defaultdict`- and `set`-based structure used by
`Blueprint` objects.  This is because the walk algorithm is used to both walk
actual `Blueprint` objects and to construct Blueprint objects.
"""

import os.path
import re

import git
import managers
import util


def walk(b, **kwargs):
    """
    Walk an entire blueprint in the appropriate order, executing callbacks
    along the way.  See blueprint(5) for details on the algorithm.  The
    callbacks are passed directly from this method to the resource
    type-specific methods and are documented there.
    """
    walk_sources(b, **kwargs)
    walk_files(b, **kwargs)
    walk_packages(b, **kwargs)
    walk_services(b, **kwargs)


def walk_sources(b, **kwargs):
    """
    Walk a blueprint's source tarballs and execute callbacks.

    * `before_sources():`
      Executed before source tarballs are enumerated.
    * `source(dirname, filename, gen_content, url):`
      Executed when a source tarball is enumerated.  Either `gen_content` or
      `url` will be `None`.  `gen_content`, when not `None`, is a callable
      that will return the file's contents.
    * `after_sources():`
      Executed after source tarballs are enumerated.
    """

    kwargs.get('before_sources', lambda *args: None)()

    pattern = re.compile(r'^(?:file|ftp|https?)://', re.I)
    callable = kwargs.get('source', lambda *args: None)
    for dirname, filename in sorted(b.get('sources', {}).iteritems()):
        if pattern.match(filename) is None:
            def gen_content():

                # It's a good thing `gen_content` is never called by the
                # `Blueprint.__init__` callbacks, since this would always
                # raise `AttributeError` on the fake blueprint structure
                # used to initialize a real `Blueprint` object.
                tree = git.tree(b._commit)

                blob = git.blob(tree, filename)
                return git.content(blob)
            callable(dirname, filename, gen_content, None)
        else:
            url = filename
            filename = os.path.basename(url)
            if '' == filename:
                filename = 'blueprint-downloaded-tarball.tar.gz'
            callable(dirname, filename, None, url)

    kwargs.get('before_sources', lambda *args: None)()


def walk_files(b, **kwargs):
    """
    Walk a blueprint's files and execute callbacks.

    * `before_files():`
      Executed before files are enumerated.
    * `file(pathname, f):`
      Executed when a file is enumerated.
    * `after_files():`
      Executed after files are enumerated.
    """

    kwargs.get('before_files', lambda *args: None)()

    callable = kwargs.get('file', lambda *args: None)
    for pathname, f in sorted(b.get('files', {}).iteritems()):

        # AWS cfn-init templates may specify file content as JSON, which
        # must be converted to a string here, lest each frontend have to
        # do so.
        if 'content' in f and not isinstance(f['content'], basestring):
            f['content'] = util.json_dumps(f['content'])

        callable(pathname, f)

    kwargs.get('after_files', lambda *args: None)()


def walk_packages(b, managername=None, **kwargs):
    """
    Walk a package tree and execute callbacks along the way.  This is a bit
    like iteration but can't match the iterator protocol due to the varying
    argument lists given to each type of callback.  The available callbacks
    are:

    * `before_packages(manager):`
      Executed before a package manager's dependencies are enumerated.
    * `package(manager, package, version):`
      Executed when a package version is enumerated.
    * `after_packages(manager):`
      Executed after a package manager's dependencies are enumerated.
    """

    # Walking begins with the system package managers, `apt`, `rpm`,
    # and `yum`.
    if managername is None:
        walk_packages(b, 'apt', **kwargs)
        walk_packages(b, 'rpm', **kwargs)
        walk_packages(b, 'yum', **kwargs)
        return

    # Get the full manager from its name.
    manager = managers.PackageManager(managername)

    # Give the manager a chance to setup for its dependencies.
    kwargs.get('before_packages', lambda *args: None)(manager)

    # Each package gets its chance to take action.  Note which packages
    # are themselves managers so they may be visited recursively later.
    next_managers = []
    callable = kwargs.get('package', lambda *args: None)
    for package, versions in sorted(b.get('packages',
                                          {}).get(manager,
                                                  {}).iteritems()):
        if 0 == len(versions):
            callable(manager, package, None)
        elif isinstance(versions, basestring):
            callable(manager, package, versions)
        else:
            for version in versions:
                callable(manager, package, version)
        if managername != package and package in b.get('packages', {}):
            next_managers.append(package)

    # Give the manager a change to cleanup after itself.
    kwargs.get('after_packages', lambda *args: None)(manager)

    # Now recurse into each manager that was just installed.  Recursing
    # here is safer because there may be secondary dependencies that are
    # not expressed in the hierarchy (for example the `mysql2` gem
    # depends on `libmysqlclient-dev` in addition to its manager).
    for managername in next_managers:
        walk_packages(b, managername, **kwargs)


def walk_services(b, managername=None, **kwargs):
    """
    Walk a blueprint's services and execute callbacks.

    * `before_services(manager):`
      Executed before a service manager's dependencies are enumerated.
    * `service(manager, service):`
      Executed when a service is enumerated.
    * `after_services(manager):`
      Executed after a service manager's dependencies are enumerated.
    """

    # Unless otherwise specified, walk all service managers.
    if managername is None:
        for managername in sorted(b.get('services', {}).iterkeys()):
            walk_services(b, managername, **kwargs)
        return

    manager = managers.ServiceManager(managername)

    kwargs.get('before_services', lambda *args: None)(manager)

    callable = kwargs.get('service', lambda *args: None)
    for service, deps in sorted(b.get('services',
                                      {}).get(manager,
                                              {}).iteritems()):
        callable(manager, service)
        walk_service_files(b, manager, service, **kwargs)
        walk_service_packages(b, manager, service, **kwargs)
        walk_service_sources(b, manager, service, **kwargs)

    kwargs.get('after_services', lambda *args: None)(manager)


def walk_service_files(b, manager, servicename, **kwargs):
    """
    Walk a service's file dependencies and execute callbacks.

    * `service_file(manager, servicename, pathname):`
      Executed when a file service dependency is enumerated.
    """
    deps = b.get('services', {}).get(manager, {}).get(servicename, {})
    if 'files' not in deps:
        return
    callable = kwargs.get('service_file', lambda *args: None)
    for pathname in list(deps['files']):
        callable(manager, servicename, pathname)


def walk_service_packages(b, manager, servicename, **kwargs):
    """
    Walk a service's package dependencies and execute callbacks.

    * `service_package(manager,
                       servicename,
                       package_managername,
                       package):`
      Executed when a file service dependency is enumerated.
    """
    deps = b.get('services', {}).get(manager, {}).get(servicename, {})
    if 'packages' not in deps:
        return
    callable = kwargs.get('service_package', lambda *args: None)
    for package_managername, packages in deps['packages'].iteritems():
        for package in packages:
            callable(manager, servicename, package_managername, package)


def walk_service_sources(b, manager, servicename, **kwargs):
    """
    Walk a service's source tarball dependencies and execute callbacks.

    * `service_source(manager, servicename, dirname):`
      Executed when a source tarball service dependency is enumerated.
    """
    deps = b.get('services', {}).get(manager, {}).get(servicename, {})
    if 'sources' not in deps:
        return
    callable = kwargs.get('service_source', lambda *args: None)
    for dirname in list(deps['sources']):
        callable(manager, servicename, dirname)
