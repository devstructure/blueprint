# Blueprint

Blueprint reverse-engineers servers.

* Easy configuration management.
* Detect relevant packages, files, and source installs.
* Generate reusable server configs.
* Convert blueprints to Puppet or Chef or CFEngine 3.
* No DSLs, no extra servers, no workflow changes.

Blueprint looks inside popular package managers, finds changes you made to configuration files, and archives software you built from source.  It runs on Debian- and RPM-based Linux distros with Python >= 2.6 and Git >= 1.7.  See <http://devstructure.github.com/blueprint/> for comprehensive documentation and examples.

## Usage

### Create a blueprint

    blueprint create my-first-blueprint

Blueprint inspects your server and stores the results in its local repository.  `blueprint list` shows all the blueprints you've created on this server.

### Apply a blueprint

    blueprint apply my-first-blueprint

Blueprint generates shell code from my-first-blueprint and executes it on the server. 

### Generate POSIX shell code from a blueprint

	blueprint show -S my-first-blueprint

`my-first-blueprint.sh` is written to your working directory.  Try out `-P` or `-C` or `--cfengine3` to generate a Puppet module or a Chef cookbook or a CFEngine 3 sketch.

### Diff a blueprint

	blueprint diff foo bar baz

Blueprint subtracts `bar` from `foo`.  Files, packages and sources that appears in `foo` but not `bar` will be carried over to `baz` and everything else will be dropped.

### Push a blueprint

    blueprint push my-first-blueprint

The blueprint and its files are stored remotely.  You get a secret URL for accessing it.

### Pull a blueprint

    blueprint pull https://devstructure.com/MY-SECRET-KEY/my-first-blueprint

The blueprint is stored locally and ready for use.

## Installation

Prerequisites:

* Debian- or RPM-based Linux
* Python >= 2.6
* Git >= 1.7 (not just for installation from source)

You may need to add `Defaults !always_set_home` to `/etc/sudoers` to run `blueprint` as `root`, which is required in order to capture source tarballs.

### From DevStructure’s Debian archive

	echo "deb http://packages.devstructure.com $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/devstructure.list
	sudo wget -O /etc/apt/trusted.gpg.d/devstructure.gpg http://packages.devstructure.com/keyring.gpg
	sudo apt-get update
	sudo apt-get -y install blueprint

### From PyPI

	pip install blueprint

Make sure `pip` is using Python >= 2.6, otherwise the installation will succeed but Blueprint will not run.

### From source on Debian, Ubuntu, Fedora, CentOS 6, and RHEL 6

	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	git submodule update --init
	make && sudo make install

### From source on CentOS 5 and RHEL 5

	rpm -Uvh http://dl.fedoraproject.org/pub/epel/5/i386/epel-release-5-4.noarch.rpm
	yum install python26
	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	git submodule update --init
	make && sudo make install PYTHON=/usr/bin/python26

This installs Python 2.6 from EPEL side-by-side with Python 2.4 and so won’t break Yum.

## Documentation

The prose [documentation](http://devstructure.github.com/blueprint/) provides a comprehensive overview of the tool including philosophy, installation, and detailed examples.

The HTTP [protocols](https://devstructure.github.com/blueprint/#protocols) and [endpoints](https://devstructure.github.com/blueprint/#endpoints) used by `blueprint-push`(1) and `blueprint-pull`(1) are documented so that others may run compatible servers.

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

* [`blueprint-git`(1)](http://devstructure.github.com/blueprint/blueprint-git.1.html): low-level access to blueprints.
* [`blueprint-show-files`(1)](http://devstructure.github.com/blueprint/blueprint-show-files.1.html): show files in a blueprint.
* [`blueprint-show-ignore`(1)](http://devstructure.github.com/blueprint/blueprint-show-ignore.1.html): show `blueprintignore`(5) rules from a blueprint.
* [`blueprint-show-packages`(1)](http://devstructure.github.com/blueprint/blueprint-show-packages.1.html): show packages in a blueprint.
* [`blueprint-show-services`(1)](http://devstructure.github.com/blueprint/blueprint-show-services.1.html): show services in a blueprint.
* [`blueprint-show-sources`(1)](http://devstructure.github.com/blueprint/blueprint-show-sources.1.html): show source tarballs in a blueprint.

## Contribute

Blueprint is [BSD-licensed](https://github.com/devstructure/blueprint/blob/master/LICENSE).

* Source code: <https://github.com/devstructure/blueprint>
* Issue tracker: <https://github.com/devstructure/blueprint/issues>
* Documentation: <http://devstructure.github.com/blueprint/>
* Wiki: <https://github.com/devstructure/blueprint/wiki>
* Mailing list: <https://groups.google.com/forum/#!forum/blueprint-users>
* IRC: `#devstructure` on Freenode
