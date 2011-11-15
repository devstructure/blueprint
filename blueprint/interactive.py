"""
Interactively walk blueprints.
"""

import git
import walk as walklib


def walk(b, choose):
    """
    Given a function for choosing a `Blueprint` object (based typically on
    the result of a `raw_input` call within the `choose` function), populate
    one or more `Blueprint`s closed into `choose`.
    """

    def file(pathname, f):
        print(pathname)
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_file(pathname, **f)

    def package(manager, package, version):
        print('{0} {1} {2}'.format(manager, package, version))
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_package(manager, package, version)

    def service(manager, service):
        print('{0} {1}'.format(manager, service))
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_service(manager, service)

        def service_file(manager, service, pathname):
            b_chosen.add_service_file(manager, service, pathname)
        walklib.walk_service_files(b_chosen,
                                   manager,
                                   service,
                                   service_file=service_file)

        def service_package(manager, service, package_manager, package):
            b_chosen.add_service_package(manager,
                                         service,
                                         package_manager,
                                         package)
        walklib.walk_service_packages(b_chosen,
                                      manager,
                                      service,
                                      service_package=service_package) 
        def service_source(manager, service, dirname):
            b_chosen.add_service_source(manager, service, dirname)
        walklib.walk_service_sources(b_chosen,
                                     manager,
                                     service,
                                     service_source=service_source)

    commit = git.rev_parse(b.name)
    tree = git.tree(commit)
    def source(dirname, filename, gen_content, url):
        if url is not None:
            print('{0} {1}'.format(dirname, url))
        elif gen_content is not None:
            blob = git.blob(tree, filename)
            git.cat_file(blob, filename)
            print('{0} {1}'.format(dirname, filename))
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_source(dirname, filename)

    b.walk(file=file, package=package, service=service, source=source)
