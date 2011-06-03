# Blueprint

## `blueprint` reverse engineers servers:

* Easy configuration management.
* Detect relevant packages, files, and source installs.
* Generate reusable server configs.
* Convert blueprints to Puppet or Chef.
* No DSLs, no extra servers, no workflow changes.

`blueprint` looks inside popular package managers, finds changes you made to configuration files, and archives software you built from source.  It runs on Debian and RPM based distros with Python >= 2.6.

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

## Installation

Prerequisites:

* A Debian- or RPM-based Linux distribution
* Python >= 2.6
* Git >= 1.7

### From source on Debian, Ubuntu, and Fedora

	git clone git://github.com/devstructure/blueprint.git
	(cd blueprint && make && sudo make install)

### From source on CentOS and RHEL

	rpm -Uvh http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
	yum install python26
	git clone git://github.com/devstructure/blueprint.git
	cd blueprint && make && sudo make install PYTHON=/usr/bin/python26

This installs Python 2.6 from EPEL side-by-side with Python 2.4 and so won't break yum.

### From source on CentOS and RHEL

	rpm -Uvh http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
	yum install python26
	git clone git://github.com/devstructure/blueprint.git
	cd blueprint && make && sudo make install PYTHON=/usr/bin/python26

This installs Python 2.6 from EPEL side-by-side with Python 2.4 and so won't break yum.

### With a package manager

DevStructure maintains Debian packages and Python eggs for Blueprint.  See [Installing with a package manager](https://github.com/devstructure/blueprint/wiki/Installing-with-a-package-manager) on the wiki.

## Documentation

The [Blueprint tutorial](https://devstructure.com/docs/tutorial.html) works through creating and deploying a simple web application via Blueprint.

## Manuals

* [`blueprint`(1)](http://devstructure.github.com/blueprint/blueprint.1.html)
* [`blueprint-list`(1)](http://devstructure.github.com/blueprint/blueprint-list.1.html)
* [`blueprint-create`(1)](http://devstructure.github.com/blueprint/blueprint-create.1.html)
* [`blueprint-show`(1)](http://devstructure.github.com/blueprint/blueprint-show.1.html)
* [`blueprint-apply`(1)](http://devstructure.github.com/blueprint/blueprint-apply.1.html)
* [`blueprint-destroy`(1)](http://devstructure.github.com/blueprint/blueprint-destroy.1.html)
* [`blueprint`(5)](http://devstructure.github.com/blueprint/blueprint.5.html)
* [`blueprintignore`(5)](http://devstructure.github.com/blueprint/blueprintignore.5.html)
* [`blueprint`(7)](http://devstructure.github.com/blueprint/blueprint.7.html)

## Contribute

Blueprint is [BSD-licensed](https://github.com/devstructure/blueprint/blob/master/LICENSE).

* Source code: <https://github.com/devstructure/blueprint>
* Issue tracker: <https://github.com/devstructure/blueprint/issues>
* Documentation: <https://devstructure.com/docs/>
* Wiki: <https://github.com/devstructure/blueprint/wiki>
* Mailing list: <https://groups.google.com/forum/#!forum/blueprint-users>
* IRC: `#devstructure` on Freenode
