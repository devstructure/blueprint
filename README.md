# `blueprint` reverse engineers servers for you:

* See what's been installed.
* Standardize development environments.
* Share stacks with your team.
* Generate configurations for Puppet or Chef.
* Audit your infrastructure.

`blueprint` is DevStructure's workhorse tool that looks inside popular package managers, finds changes you made to configuration files, and archives software you built from source to generate Puppet, Chef, or shell code.  Everything blueprint sees is stored in Git to be diffed and pushed.  It runs on Debian and RPM based distros with Python >= 2.6.

## Try it now!

	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	make && sudo make install

Not sure what to do next?  Take a peek at our [install documentation](http://devstructure.github.com/blueprint/) or try this [tutorial](http://devstructure.github.com/blueprint/tutorial.html) that takes you from setup to production with a simple web application.

## Contribute

`blueprint` is BSD-licensed.  We love bug reports and pull requests!

* [Source code](https://github.com/devstructure/blueprint)
* [Issue tracker](https://github.com/devstructure/blueprint/issues)
* [Documentation](http://devstructure.github.com/blueprint/)
* [Discuss](https://groups.google.com/forum/#!forum/blueprint-users) or `#devstructure` on Freenode
