# Blueprint

### Blueprint reverse-engineers servers

* Easy configuration management.
* Detect relevant packages, files, and source installs.
* Generate reusable server configs.
* Convert blueprints to Puppet or Chef.
* No DSLs, no extra servers, no workflow changes.

Blueprint looks inside popular package managers, finds changes you made to configuration files, and archives software you built from source.  It runs on Debian- and RPM-based Linux distros with Python >= 2.6 and Git >= 1.7. Comprehensive documentation and examples in the [Blueprint book](http://devstructure.github.com/blueprint/).

### Blueprint I/O moves blueprints around

* Centralized configuration management.
* Export and backup server configurations.
* Push and pull blueprints anywhere.
* Bootstrap servers painlessly.

Blueprint I/O pushes and pulls blueprints to and from a Blueprint I/O Server, making it easy to use blueprints anywhere. DevStructure provides a free Blueprint I/O Server at <https://devstructure.com>, which stores blueprints in Amazon S3. Alternatively, you can build your own backend server implementing the Blueprint I/O API.

## Usage

### Create a blueprint

    blueprint create my-first-blueprint

Blueprint inspects your server and stores the results in its local repository.  `blueprint list` shows all the blueprints you've created on this server.

### Apply a blueprint

    blueprint apply my-first-blueprint

Blueprint generates shell code from my-first-blueprint and executes it on the server. 

### Generate POSIX shell code from a blueprint

	blueprint show -S my-first-blueprint

`my-first-blueprint.sh` is written to your working directory.  Try out `-P` or `-C` to generate a Puppet module or a Chef cookbook.

### Diff a blueprint

	blueprint diff foo bar baz

Blueprint subtracts bar from foo. Files, packages and source that appears in foo but not bar will be carried over to baz and everything else will be dropped.

### Push a blueprint

    blueprint push my-first-blueprint

The blueprint and its files are stored remotely.  You get a secret URL for accessing it.

### Pull a blueprint

    blueprint pull https://devstructure.com/MY-SECRET-KEY/my-first-blueprint

The blueprint is stored locally and ready for use.

## Installation

Prerequisites:

* A Debian- or RPM-based Linux distribution
* Python >= 2.6
* Git >= 1.7

### From source on Debian, Ubuntu, Fedora, CentOS 6, and RHEL 6

	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	git submodule update --init
	make && sudo make install

### From source on CentOS and RHEL 5

	rpm -Uvh http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
	yum install python26
	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	git submodule update --init
	make && sudo make install PYTHON=/usr/bin/python26

This installs Python 2.6 from EPEL side-by-side with Python 2.4 and so won't break yum.

### With a package manager

DevStructure maintains Debian packages and Python eggs for Blueprint.  See [Installing with a package manager](https://github.com/devstructure/blueprint/wiki/Installing-with-a-package-manager) on the wiki.

## Documentation

The [Blueprint book](http://devstructure.github.com/blueprint/) is a comprehensive overview of the tool including philosophy, installation and detailed examples.

The [Blueprint tutorial](https://devstructure.com/docs/tutorial.html) works through creating and deploying a simple web application via Blueprint.

The HTTP [endpoints](https://devstructure.com/docs/endpoints.html) and [protocols](https://devstructure.com/docs/protocols.html) used by `blueprint-push`(1) and `blueprint-pull`(1) are documented so that others may run compatible servers.

## Manuals

* [`blueprint-list`(1)](http://devstructure.github.com/blueprint/blueprint-list.1.html): list all blueprints.
* [`blueprint-create`(1)](http://devstructure.github.com/blueprint/blueprint-create.1.html): create a blueprint.
* [`blueprint-rules`(1)](http://devstructure.github.com/blueprint/blueprint-rules.1.html): create a blueprint from a blueprint-rules file.
* [`blueprint-show`(1)](http://devstructure.github.com/blueprint/blueprint-show.1.html): generate code from a blueprint.
* [`blueprint-diff`(1)](http://devstructure.github.com/blueprint/blueprint-diff.1.html): save the difference between two blueprints.
* [`blueprint-split`(1)](http://devstructure.github.com/blueprint/blueprint-split.1.html): split one blueprint into two others interactively.
* [`blueprint-prune`(1)](http://devstructure.github.com/blueprint/blueprint-prune.1.html): select a subset of resources interactively.
* [`blueprint-template`(1)](http://devstructure.github.com/blueprint/blueprint-template.1.html): render mustache.sh templates locally.
* [`blueprint-apply`(1)](http://devstructure.github.com/blueprint/blueprint-apply.1.html): run a blueprint's generated shell code.
* [`blueprint-push`(1)](http://devstructure.github.com/blueprint/blueprint-push.1.html): push a blueprint to the Internet.
* [`blueprint-pull`(1)](http://devstructure.github.com/blueprint/blueprint-pull.1.html): pull a blueprint from the Internet.
* [`blueprint-destroy`(1)](http://devstructure.github.com/blueprint/blueprint-destroy.1.html): destroy a blueprint.
* [`blueprint`(5)](http://devstructure.github.com/blueprint/blueprint.5.html): Blueprint JSON format.
* [`blueprintignore`(5)](http://devstructure.github.com/blueprint/blueprintignore.5.html): ignore specific files when creating blueprints.
* [`blueprint-rules`(5)](http://devstructure.github.com/blueprint/blueprint-rules.5.html): enumerate resources in blueprints.
* [`blueprint.cfg`(5)](http://devstructure.github.com/blueprint/blueprint.cfg.5.html): centralized blueprint service configuration.
* [`blueprint-template`(5)](http://devstructure.github.com/blueprint/blueprint-template.5.html): `mustache.sh` template language syntax.
* [`blueprint-template`(7)](http://devstructure.github.com/blueprint/blueprint-template.7.html): built-in template data.
* [`blueprint`(7)](http://devstructure.github.com/blueprint/blueprint.7.html): Blueprint Python library.

### Plumbing

* [`blueprint-git`(1)](http://devstructure.github.com/blueprint/blueprint-git.1.html)
* [`blueprint-show-files`(1)](http://devstructure.github.com/blueprint/blueprint-show-files.1.html)
* [`blueprint-show-ignore`(1)](http://devstructure.github.com/blueprint/blueprint-show-ignore.1.html)
* [`blueprint-show-packages`(1)](http://devstructure.github.com/blueprint/blueprint-show-packages.1.html)
* [`blueprint-show-services`(1)](http://devstructure.github.com/blueprint/blueprint-show-services.1.html)
* [`blueprint-show-sources`(1)](http://devstructure.github.com/blueprint/blueprint-show-sources.1.html)

## Contribute

Blueprint is [BSD-licensed](https://github.com/devstructure/blueprint/blob/master/LICENSE).

* Source code: <https://github.com/devstructure/blueprint>
* Issue tracker: <https://github.com/devstructure/blueprint/issues>
* Documentation: <http://devstructure.github.com/blueprint/>
* Wiki: <https://github.com/devstructure/blueprint/wiki>
* Mailing list: <https://groups.google.com/forum/#!forum/blueprint-users>
* IRC: `#devstructure` on Freenode
