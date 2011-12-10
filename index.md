---
layout: default
---

Blueprint
=========

Table of contents
-----------------

1.  [Introduction](#introduction)
2.  [Philosophy](#philosophy)
3.  [Installation](#installation)
4.  [Reverse-engineering systems with blueprint-create](#create)
5.  [Inspecting blueprints](#inspect)
6.  [Ignoring particular resources](#ignore)
7.  [Rules files and blueprint-rules](#rules)
8.  [Diffing, splitting and pruning existing blueprints](#diff-split-prune)
9.  [Rendering templates of configuration files](#templates)
10. [Controlling service restart conditions](#services)
11. [Generating POSIX shell scripts](#sh)
12. [Sharing and distributing blueprints](#push-pull)
13. [Generating Puppet modules and Chef cookbooks](#puppet-chef)
14. [Integrating with AWS CloudFormation](#cloudformation)
15. [Deploying your application with Blueprint](#deploy)
16. [Local Git repository](#git)
17. [Contributing to Blueprint](#contributing)
18. [Alternatives to Blueprint](#alternatives)

Manuals
-------

* [`blueprint-list`(1)](https://devstructure.github.com/blueprint/blueprint-list.1.html): list all blueprints.
* [`blueprint-create`(1)](https://devstructure.github.com/blueprint/blueprint-create.1.html): create a blueprint.
* [`blueprint-rules`(1)](https://devstructure.github.com/blueprint/blueprint-rules.1.html): create a blueprint from a blueprint-rules file.
* [`blueprint-show`(1)](https://devstructure.github.com/blueprint/blueprint-show.1.html): generate code from a blueprint.
* [`blueprint-diff`(1)](https://devstructure.github.com/blueprint/blueprint-diff.1.html): save the difference between two blueprints.
* [`blueprint-split`(1)](https://devstructure.github.com/blueprint/blueprint-split.1.html): split one blueprint into two others interactively.
* [`blueprint-prune`(1)](https://devstructure.github.com/blueprint/blueprint-prune.1.html): select a subset of resources interactively.
* [`blueprint-template`(1)](https://devstructure.github.com/blueprint/blueprint-template.1.html): render mustache.sh templates locally.
* [`blueprint-apply`(1)](https://devstructure.github.com/blueprint/blueprint-apply.1.html): run a blueprint's generated shell code.
* [`blueprint-push`(1)](https://devstructure.github.com/blueprint/blueprint-push.1.html): push a blueprint to the Internet.
* [`blueprint-pull`(1)](https://devstructure.github.com/blueprint/blueprint-pull.1.html): pull a blueprint from the Internet.
* [`blueprint-destroy`(1)](https://devstructure.github.com/blueprint/blueprint-destroy.1.html): destroy a blueprint.
* [`blueprint`(5)](https://devstructure.github.com/blueprint/blueprint.5.html): Blueprint JSON format.
* [`blueprintignore`(5)](https://devstructure.github.com/blueprint/blueprintignore.5.html): ignore specific files when creating blueprints.
* [`blueprint-rules`(5)](https://devstructure.github.com/blueprint/blueprint-rules.5.html): enumerate resources in blueprints.
* [`blueprint.cfg`(5)](https://devstructure.github.com/blueprint/blueprint.cfg.5.html): centralized blueprint service configuration.
* [`blueprint-template`(5)](https://devstructure.github.com/blueprint/blueprint-template.5.html): `mustache.sh` template language syntax.
* [`blueprint-template`(7)](https://devstructure.github.com/blueprint/blueprint-template.7.html): built-in template data.
* [`blueprint`(7)](https://devstructure.github.com/blueprint/blueprint.7.html): Blueprint Python library.

### Plumbing

* [`blueprint-git`(1)](https://devstructure.github.com/blueprint/blueprint-git.1.html): low-level access to blueprints.
* [`blueprint-show-files`(1)](https://devstructure.github.com/blueprint/blueprint-show-files.1.html): show files in a blueprint.
* [`blueprint-show-ignore`(1)](https://devstructure.github.com/blueprint/blueprintshow-ignore-.1.html): show `blueprintignore`(5) rules from a blueprint.
* [`blueprint-show-packages`(1)](https://devstructure.github.com/blueprint/blueprint-show-packages.1.html): show packages in a blueprint.
* [`blueprint-show-services`(1)](https://devstructure.github.com/blueprint/blueprint-show-services.1.html): show services in a blueprint.
* [`blueprint-show-sources`(1)](https://devstructure.github.com/blueprint/blueprint-show-sources.1.html): show source tarballs in a blueprint.

----

<h1 id="introduction">Introduction</h1>

Blueprint is a simple configuration management tool that reverse-engineers servers.  It figures out what you've done manually, stores it locally in a Git repository, generates code that's able to do the same things you've done manually, and helps you deploy those changes to production.

----

<h1 id="philosophy">Philosophy</h1>

Blueprint was born out of frustration with development environments, deployment processes, and the complexity of configuration management systems.

Blueprint insists development environments realistically model production and that starts with using Linux.  Blueprint only works on Debian- or Red Hat-based Linux systems.  We recommend VirtualBox, Vagrant, Rackspace Cloud, or AWS EC2 for development systems that use the same operating system (and version) as is used in production.

On top of the operating system, we recommend using the same web servers, databases, message queue brokers, and other software in development and production.  This brings development visibility to entire classes of bugs that only occur due to interactions between production components.

When development and production share the same operating system and software stack, they also share the same interactive management tools, meaning developers and operators alike don't need to maintain two vocabularies.  Well-understood tools like `apt-get`/`dpkg`, `yum`/`rpm`, and the whole collection of Linux system tools are available everywhere.  Blueprint is unique relative to other configuration management in encouraging use of these tools.

What's common to all configuration management tools is the desire to manage the whole stack: from the operating system packages and services through language-specific packages, all the way to your applications.  We need to span all of these across all our systems.  To pick on RubyGems arbitrarily: RubyGems is purposely ignorant of its relationship to the underlying system, favoring compatibility with Windows and a wide variety of UNIX-like operating systems.  Blueprint understands the macro-dependencies between RubyGems itself and the underlying system and is able to predictably reinstall a selection of gems on top of a properly configured operating system.

When constructing this predictable order-of-operations used to reinstall files, packages, services, and source installations, Blueprint, along with other configuration management tools, takes great care in performing idempotent actions.  Thus Blueprint prefers to manage the entire contents of a file rather than a diff or a line to append.  Idempotency means you can apply a blueprint over and over again with confidence that nothing will change if nothing needs to change.

Because Blueprint can reverse-engineer systems, it is of particular use migrating legacy systems into configuration management.  It doesn't matter when you install Blueprint: changes made to the system even before Blueprint is installed will be taken into account.

----

<h1 id="installation">Installation</h1>

Prerequisites:

* Debian- or RPM-based Linux
* Python >= 2.6
* Git >= 1.7 (not just for installation from source)

From DevStructure's Debian archive
----------------------------------

	echo "deb http://packages.devstructure.com $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/devstructure.list
	sudo wget -O /etc/apt/trusted.gpg.d/devstructure.gpg http://packages.devstructure.com/keyring.gpg
	sudo apt-get update
	sudo apt-get -y install blueprint

From PyPI
---------

	pip install blueprint

Make sure `pip` is using Python >= 2.6, otherwise the installation will succeed but Blueprint will not run.

From source on Debian, Ubuntu, Fedora, CentOS 6, and RHEL 6
-----------------------------------------------------------

	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	git submodule update --init
	make && sudo make install

From source on CentOS 5 and RHEL 5
----------------------------------

	rpm -Uvh http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
	yum install python26
	git clone git://github.com/devstructure/blueprint.git
	cd blueprint
	git submodule update --init
	make && sudo make install PYTHON=/usr/bin/python26

This installs Python 2.6 from EPEL side-by-side with Python 2.4 and so won't break Yum.

----

<h1 id="create">Reverse-engineering systems with blueprint-create</h1>

By now you've hopefully created a development environment running the same operating system (and version) that you use in production and installed your production stack.  If this is your first time configuring production databases and web servers, don't be shy about copying-and-pasting from the guy at the next desk or a staging or production system (perhaps even multiple systems).

Once Blueprint itself is installed you can reverse-engineer your development system with a single command.

<pre><code>blueprint create <em>name</em></code></pre>

Blueprint will list packages managed by APT, Yum, RubyGems, Python's `easy_install` and `pip`, PHP's PEAR and PECL, and Node.js' NPM.  It will also determine which configuration files in `/etc` have been added or modified from their packaged versions and collect files in `/usr/local` that are part of any software packages installed from source (typically via GNU `make`(1)).  Finally, it will build a list of conditions under which System V init or Upstart services should be restarted, including package upgrades and configuration changes.

All of this information is encoded in a `blueprint`(5) JSON document and zero or more `tar`(5) archives and stored in a branch called _name_ in the local Git repository `~/.blueprints.git`.

Any blueprint in the local Git repository may be applied to the system with `blueprint-apply`(1):

<pre><code>blueprint apply <em>name</em></code></pre>

Example
-------

Suppose you want to install a basic Ruby stack for running a Sinatra application called `example` proxied by Nginx on Debian-based Linux.  Install the prerequisite packages:

	sudo apt-get install build-essential nginx-light ruby ruby-dev rubygems
	sudo gem install sinatra unicorn

Configure Nginx in `/etc/nginx/sites-available/example`:

	server {
		listen 80 default;
		location /static { root /usr/local/share/rack/example/static; }
		location / { proxy_pass http://127.0.0.1:8080; }
	}

Enable the Nginx configuration:

	ln -s /etc/nginx/sites-{available,enabled}/example

Create the application itself.  `/usr/local/share/rack/example/app.rb`:

	require 'sinatra'
	get '/hi' do
	  "Hello, world!\n"
	end

`/usr/local/share/rack/example/config.ru`:

	require 'app'
	run Sinatra::Application

Configure Unicorn in `/etc/unicorn.conf.rb`:

	worker_processes 4

Configure Upstart to run the application:

	description "Example"
	start on runlevel [2345]
	stop on runlevel [!2345]
	respawn
	chdir /usr/local/share/rack/example
	exec unicorn -c /etc/unicorn.conf.rb

Now create a blueprint and call it _example_.

	sudo blueprint create example

We'll pick this example up in the next chapter.

----

<h1 id="inspect">Inspecting blueprints</h1>

Once a blueprint has been created and stored in the local Git repository, it's easy to inspect what's been included both in its raw JSON form and in more friendly formats.

First, print the entire `blueprint`(5) JSON document:

<pre><code>blueprint show <em>name</em> | less</code></pre>

The output of `blueprint-show`(1) can be a bit overwhelming, which is one of the reasons the following four commands were created.

`blueprint-show-files`(1) lists the pathname of each file included in the blueprint on its own line.

<pre><code><em>pathname</em></code></pre>

`blueprint-show-packages`(1) lists the manager ("`apt`", "`yum`", "`rubygems1.8`", etc.), name, and version number for each package included in the blueprint on its own line.  If two versions of the same package are included (as is possibly with RubyGems and some other package managers), each will be printed on its own line.

<pre><code><em>manager</em> <em>package</em> <em>version</em></code></pre>

`blueprint-show-services`(1) lists the manager ("`sysvinit`" or "`upstart`") and name of each service included in the blueprint on its own line.

<pre><code><em>manager</em> <em>service</em></code></pre>

`blueprint-show-sources`(1) lists the source installations included in the blueprint.  The root directory (for example, "`/usr/local`") and tarball filename are printed to standard error and the contents of the tarball are printed to standard output via `tar`(1)'s `tv` options.

<pre><code><em>dirname</em> <em>filename</em><br /><em>`tar tv` output</em></code></pre>

Example
-------

`blueprint show-files example`

	/etc/apt/sources.list
	/etc/hosts
	/etc/init/example.conf
	/etc/mysql/debian.cnf
	/etc/nginx/sites-available/example
	/etc/nginx/sites-enabled/default
	/etc/nginx/sites-enabled/example
	/etc/unicorn.conf.rb

`blueprint show-packages example`

	apt binutils 2.21.53.20110810-0ubuntu3
	apt blueprint 3.4.0-1py2.7
	apt build-essential 11.5ubuntu1
	apt ca-certificates 20110502+nmu1ubuntu5
	apt cpp 4:4.6.1-2ubuntu5
	apt cpp-4.6 4.6.1-9ubuntu3
	apt curl 7.21.6-3ubuntu3
	apt dpkg-dev 1.16.0.3ubuntu5
	apt fakeroot 1.17-1
	apt g++ 4:4.6.1-2ubuntu5
	apt g++-4.6 4.6.1-9ubuntu3
	apt gcc 4:4.6.1-2ubuntu5
	apt gcc-4.6 4.6.1-9ubuntu3
	apt git 1:1.7.5.4-1
	apt git-core 1:1.7.5.4-1
	apt git-man 1:1.7.5.4-1
	apt libalgorithm-diff-perl 1.19.02-2
	apt libalgorithm-diff-xs-perl 0.04-1build1
	apt libalgorithm-merge-perl 0.08-2
	apt libc-dev-bin 2.13-20ubuntu5
	apt libc6-dev 2.13-20ubuntu5
	apt libcurl3 7.21.6-3ubuntu3
	apt libcurl3-gnutls 7.21.6-3ubuntu3
	apt libdbd-mysql-perl 4.019-1
	apt libdbi-perl 1.616-1build1
	apt libdpkg-perl 1.16.0.3ubuntu5
	apt liberror-perl 0.17-1
	apt libgmp10 2:5.0.1+dfsg-7ubuntu2
	apt libgomp1 4.6.1-9ubuntu3
	apt libhtml-template-perl 2.10-1
	apt libmpc2 0.9-3
	apt libmpfr4 3.0.1-5
	apt libmysqlclient16 5.1.58-1ubuntu1
	apt libnet-daemon-perl 0.48-1
	apt libplrpc-perl 0.2020-2
	apt libquadmath0 4.6.1-9ubuntu3
	apt libreadline5 5.2-9ubuntu1
	apt librtmp0 2.3-2ubuntu1
	apt libruby1.8 1.8.7.352-2
	apt libstdc++6-4.6-dev 4.6.1-9ubuntu3
	apt libtimedate-perl 1.2000-1
	apt libwrap0 7.6.q-21
	apt linux-libc-dev 3.0.0-12.20
	apt manpages-dev 3.27-1ubuntu2
	apt mysql-client-5.1 5.1.58-1ubuntu1
	apt mysql-client-core-5.1 5.1.58-1ubuntu1
	apt mysql-common 5.1.58-1ubuntu1
	apt mysql-server 5.1.58-1ubuntu1
	apt mysql-server-5.1 5.1.58-1ubuntu1
	apt mysql-server-core-5.1 5.1.58-1ubuntu1
	apt nginx-common 1.0.5-1
	apt nginx-light 1.0.5-1
	apt openssh-server 1:5.8p1-7ubuntu1
	apt openssl 1.0.0e-2ubuntu4
	apt python-pip 1.0-1
	apt python-pkg-resources 0.6.16-1
	apt python-setuptools 0.6.16-1
	apt rsync 3.0.8-1ubuntu1
	apt ruby 4.8
	apt ruby-dev 4.8
	apt ruby1.8 1.8.7.352-2
	apt ruby1.8-dev 1.8.7.352-2
	apt rubygems 1.7.2-1
	apt tmux 1.5-1
	python-pip Django 1.3.1
	rubygems fpm 0.3.11
	rubygems hpricot 0.8.5
	rubygems json 1.6.3
	rubygems kgio 2.6.0
	rubygems mustache 0.99.4
	rubygems rack 1.3.5
	rubygems rack-protection 1.1.4
	rubygems raindrops 0.8.0
	rubygems rdiscount 1.6.8
	rubygems sinatra 1.3.1
	rubygems tilt 1.3.3
	rubygems unicorn 4.1.1

`blueprint show-services example`

	sysvinit nginx
	sysvinit ssh
	upstart example
	upstart mysql

`blueprint show-sources example`

	/usr/local 82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar
	drwxr-xr-x root/root         0 2011-11-29 21:42 ./
	drwxr-xr-x root/root         0 2011-11-29 20:50 ./share/
	drwxr-xr-x root/root         0 2011-11-29 21:55 ./share/rack/
	drwxr-xr-x rcrowley/rcrowley 0 2011-12-09 15:12 ./share/rack/example/
	-rw-rw-r-- rcrowley/rcrowley 55 2011-11-29 21:02 ./share/rack/example/app.rb
	-rw-rw-r-- rcrowley/rcrowley 39 2011-11-29 20:54 ./share/rack/example/config.ru

We're off to a great start but there are some extraneous files and packages here that need cleaning up.

----

<h1 id="ignore">Ignoring particular resources</h1>

Rather than requiring you enumerate every detail of your infrastructure in code, Blueprint reverse-engineers most of these details from running systems.  There are times, though, when it's a bit too verbose.

Inspired by similar features in version control software, Blueprint allows you to enumerate files, packages, services, and sources that should be ignored in a file format inspired by `gitignore`(5).  See `blueprintignore`(5) for details.

Blueprint looks for these rules in `/etc/blueprintignore` and `~/.blueprintignore`.  Rules in `/etc/blueprintignore` will be included in the blueprint itself, thereby propagating to other users of the blueprint.  Rules in `~/.blueprintignore` will remain local though each revision of a blueprint will store the full set of rules used to create it.

Files may be specified by fully-qualified or relative pathnames, possibly including glob syntax:

	/etc/foo
	foo/*
	*.foo
	[abc]/[xyz]

Packages must be specified by their manager and name, prefixed with `:package:`:

	:package:apt/build-essential

When a package is ignored, packages on which it depends are also ignored.

Services must be specified by their manager and name, prefixed with `:service:`:

	:service:sysvinit/ssh

Sources must be specified by fully-qualified pathnames:

	:sources:/usr/local

You can ignore and unignore particular files within a source directory to fine-tune what's included in the tarball.

Any rule may be negated by prefixing it with a `!`, which overrides defaults and well as previous matching rules - the last matching rule wins.

Example
-------

`/etc/apt/sources.list` and `/etc/hosts` really don't belong in the blueprint since they're part of the operating system and we haven't customized them.  Add their pathnames to `/etc/blueprintignore`:

	/etc/apt/sources.list
	/etc/hosts

`/etc/mysql/debian.cnf` is generated by the MySQL server package in its `postinst` maintainer script.  Add its pathname to `/etc/blueprintignore`:

	/etc/mysql/debian.cnf

`/etc/nginx/sites-enabled/default` is part of the basic Nginx installation and again we don't particularly care about it.  Add its pathname to `/etc/blueprintignore`:

	/etc/nginx/sites-enabled/default

`build-essential` brought a lot of friends along that are clouding what's really important in this blueprint.  Recall that ignoring a package also ignores its dependencies.  The opposite is not true: unignoring a package leaves its dependencies alone.  Ignoring and immediately unignoring `build-essential`, `ruby`, and `ruby-dev` will slim down the blueprint without any loss in completeness.

	:package:apt/build-essential
	!:package:apt/build-essential
	:package:apt/ruby
	!:package:apt/ruby
	:package:apt/ruby-dev
	!:package:apt/ruby-dev

Running `sudo blueprint create example` again will commit a new blueprint that takes these rules into account.

----

<h1 id="rules">Rules files and blueprint-rules</h1>

As complexity grows, you're likely to pass an inflection point when it becomes easier to enumerate the resources you care about, not the resources that should be ignored.  When the time comes, Blueprint is ready.  The rules syntax used to ignore particular resources can be turned around and used to enumerate the resources to include in the blueprint.  See `blueprint-rules`(5) for details.

The `blueprint-rules`(1) command reverse-engineers the system just like `blueprint-create` but limits the resources included in the blueprint to those in the rules file.

<pre><code>blueprint rules <em>pathname</em></code></pre>

The rules files are a bit of a hybrid between the traditional Blueprint approach of reverse-engineering and the typical configuration-as-code approach of other configuration management tools.

Example
-------

Add these rules to `example.blueprint-rules`:

	:source:/usr/local
	/etc/init/example.conf
	/etc/nginx/sites-*/example
	:package:apt/libmysqlclient-dev
	:package:apt/mysql-client-5.1
	:package:apt/nginx-common
	:package:apt/nginx-light
	:package:apt/ruby-dev
	:package:apt/rubygems
	:package:rubygems/*
	:service:sysvinit/nginx
	:service:upstart/example

Now create the blueprint `example`:

	blueprint rules example.blueprint-rules

As usual, the blueprint is stored locally in Git, ready for action.

A good exercise for the reader is creation of a separate blueprint for the MySQL server and its configuration.  It's installed alongside the web stack in development but that's unlikely to be the case in production, so having two blueprints could be advantageous.  The next chapter introduces another way to create two blueprints from one system.

----

<h1 id="diff-split-prune">Diffing, splitting and pruning existing blueprints</h1>

Refactoring is a major part of software development practice and configuration management shouldn't be left out in the cold.  Blueprint provides several tools that can be used to refactor your blueprints into more modular, maintainable, focused artifacts.

`blueprint-diff`(1) takes direct advantage of the subtraction operator available on `Blueprint` objects in the underlying library.

<pre><code>blueprint diff <em>minuend</em> <em>subtrahend</em> <em>difference</em></code></pre>

Resources that appear in _minuend_ but not _subtrahend_ will be included in _difference_ and committed to the local Git repository under that name.

`blueprint-split`(1) and `blueprint-prune`(1) are interactive refactoring tools.

`blueprint-split` prints each resource in _src_ and prompts you for a choice of _dest-a_ or _dest-b_.  The resulting _dest-a_ and _dest-b_ blueprints are committed to the local Git repository.

<pre><code>blueprint split <em>src</em> <em>dest-a</em> <em>dest-b</em></code></pre>

`blueprint-prune` instead prompts you to include or ignore each resource in _src_ in _dest_.

<pre><code>blueprint prune <em>src</em> <em>dest</em></code></pre>

There are some limitations in both of these tools, however.  You can't currently split the files within a source tarball.  The best workaround is to use rules files to create blueprints that contain only the files you want.

Example
-------

`blueprint prune example example-nginx`

	/usr/local 6326b42413443bc2d94e13747d05f650b873a53e.tar
	Include in blueprint example-nginx? [y/n] n
	/etc/init/example.conf
	Include in blueprint example-nginx? [y/n] n
	/etc/nginx/sites-available/example
	Include in blueprint example-nginx? [y/n] y
	/etc/nginx/sites-enabled/example
	Include in blueprint example-nginx? [y/n] y
	apt nginx-common 1.0.5-1
	Include in blueprint example-nginx? [y/n] y
	apt nginx-light 1.0.5-1
	Include in blueprint example-nginx? [y/n] y
	apt ruby-dev 4.8
	Include in blueprint example-nginx? [y/n] n
	apt rubygems 1.7.2-1
	Include in blueprint example-nginx? [y/n] n
	rubygems fpm 0.3.11
	Include in blueprint example-nginx? [y/n] n
	rubygems hpricot 0.8.5
	Include in blueprint example-nginx? [y/n] n
	rubygems json 1.6.3
	Include in blueprint example-nginx? [y/n] n
	rubygems kgio 2.6.0
	Include in blueprint example-nginx? [y/n] n
	rubygems mustache 0.99.4
	Include in blueprint example-nginx? [y/n] n
	rubygems rack 1.3.5
	Include in blueprint example-nginx? [y/n] n
	rubygems rack-protection 1.1.4
	Include in blueprint example-nginx? [y/n] n
	rubygems raindrops 0.8.0
	Include in blueprint example-nginx? [y/n] n
	rubygems rdiscount 1.6.8
	Include in blueprint example-nginx? [y/n] n
	rubygems sinatra 1.3.1
	Include in blueprint example-nginx? [y/n] n
	rubygems tilt 1.3.3
	Include in blueprint example-nginx? [y/n] n
	rubygems unicorn 4.1.1
	Include in blueprint example-nginx? [y/n] n
	sysvinit nginx
	Include in blueprint example-nginx? [y/n] y
	upstart example
	Include in blueprint example-nginx? [y/n] n

The same could have been done with `blueprint-split` to create `example-nginx` and `example-mysql` or `base` and `custom` &mdash; any distinction you desire.

----

<h1 id="templates">Rendering templates of configuration files</h1>

Not all systems are created equal.  Certainly your `m2.4xlarge` AWS EC2 instance packs a bit more CPU than a virtual machine running in a corner of your laptop and your configurations should be able to cope with these operational extremes.

Blueprint allows configuration files (found in `/etc`) to be specified as templates and (optionally) data rather than static content.  These templates are rendered by a special portable dialect of the `mustache`(5) template language called `mustache.sh`.  See `blueprint-template`(5) for details.

In their simplest form, these templates allow substitution of system parameters.

<pre><code>{ {<em>FOO</em>} }</code></pre>

You can also substitute the output of a shell command.

<pre><code>{{`<em>echo foo</em>`}}</code></pre>

More complex uses can iterate over the lines of output from a shell command.

<pre><code>{{#`<em>echo foo; echo bar; echo baz</em>`}}<br />{{_M_LINE}}<br />{{/`<em>echo foo; echo bar; echo baz</em>`}}</code></pre>

Blueprint ships with a small helping of common system parameters:

* `CORES`: the number of CPU cores in the system.
* `MEM`: the total amount of memory in the system in bytes.
* `FQDN`: the fully-qualified domain name according to `hostname`(1)'s `--fqdn` option.
* `PRIVATE_IP`: the first private IPv4 address assigned to any interface.
* `PUBLIC_IP`: the first public IPv4 address assigned to any interface.

There are several more, documented in `blueprint-template`(7).  You can provide your own global data by adding `source`-able shell scripts with the `.sh` suffix to `/etc/blueprint-template.d`.

Any _pathname_ may have an associated template, <code><em>pathname</em>.blueprint-template.mustache</code>.  An additional `source`-able shell script private to just this template may be placed in <code><em>pathname</em>.blueprint-template.sh</code>.

To render a template locally (likely during development), use `blueprint-template(1)`.

<pre><code>blueprint template <em>pathname</em></code></pre>

Example
-------

Our Unicorn configuration statically assumes four workers is the best configuration.  In reality, Unicorn workers are a function of the number of CPU cores available.

Configure Unicorn to use one worker per CPU in `/etc/unicorn.conf.rb.blueprint-template.mustache`:

	worker_processes {{CORES}}

Configure Unicorn to use four workers per CPU in `/etc/unicorn.conf.rb.blueprint-template.mustache`:

	worker_processes {{`expr 4 \* $CORES`}}

Or, you can extract computation out of the template and into `/etc/unicorn.conf.rb.blueprint-template.sh`:

	export WORKER_PROCESSES="$(expr 4 \* $CORES)"

`/etc/unicorn.conf.rb.blueprint-template.mustache` becomes:

	worker_processes {{WORKER_PROCESSES}}

Now Blueprint can scale this Unicorn configuration up and down as the system allows or requires.

----

<h1 id="services">Controlling service restart conditions</h1>

The last step in applying a blueprint is to restart all the services whose configuration changed.  Most configuration management tools require you to connect the dots explicitly but Blueprint finds many of those relationships automatically.

System V init and Upstart services are included in blueprints when their init script or configuration file, or the package that contains the init script or configuration file, are included in the blueprint.  From there, Blueprint searches for resources that, when changed, should cause the service to restart.

* When the package that contains the service init script or configuration file is upgraded, the service should be restarted.
* When other files in the package that contains the service change, the service should be restarted.
* When files in directories in the package that contains the service change, the service should be restarted.
* When fully-qualified pathnames (be they files or directories) mentioned in the service init script or configuration file are changed, the service should be restarted.  This accounts for both changes to individual files and changes in source tarballs.

Other files may be added to the list to watch by naming them in a comment in the service init script or configuration file.

Example
-------

Suppose our `example` application reads `/etc/database.yml` for database connection credentials.  The Unicorn application server must be restarted to read changes to this file.  Mention `/etc/database.yml` in the Upstart configuration:

	description "Example"
	start on runlevel [2345]
	stop on runlevel [!2345]
	respawn
	chdir /usr/local/share/rack/example
	exec unicorn -c /etc/unicorn.conf.rb
	# Dear Blueprint, restart me when /etc/database.yml changes.

----

<h1 id="sh">Generating POSIX shell scripts</h1>

Beneath the `blueprint-apply`(1) command briefly introduced before there is the `-S` option to `blueprint-show`(1) which generates a POSIX shell script that can apply a blueprint to any system.

Dependencies are especially painful when bootstrapping new systems so Blueprint takes great pains to generate dependency-free shell scripts.  They extract source tarballs, place file contents and adjust owners/groups/modes, install packages, and restart services as necessary according to the algorithm described in `blueprint`(5).  Even template rendering is handled without any dependencies.

The generated shell script for the blueprint _name_ is written to a file in your working directory as <code><em>name</em>.sh</code> or <code><em>name</em>/bootstrap.sh</code> if the blueprint contains templates or source tarballs.

<pre><code>blueprint show -S <em>name</em></code></pre>

This shell script and its associated files can drive deployment, provisioning, or other development environments without even having to install Blueprint first.

Example
-------

Running `blueprint show -S example` creates `example/bootstrap.sh` as follows and bundles `mustache.sh` and the source tarball containing our example application.  `example/bootstrap.sh`:

	#
	# Automatically generated by blueprint(7).  Edit at your own risk.
	#

	set -x

	cd "$(dirname "$0")"

	mkdir -p "/etc/init"
	cat >"/etc/init/example.conf" <<EOF
	description "Example"
	start on runlevel [2345]
	stop on runlevel [!2345]
	respawn
	chdir /usr/local/share/rack/example
	exec unicorn -c /etc/unicorn.conf.rb
	# Dear Blueprint, restart me when /etc/database.yml changes.
	EOF
	MD5SUM="$(md5sum "/etc/nginx/sites-available/example" 2>/dev/null)"
	mkdir -p "/etc/nginx/sites-available"
	cat >"/etc/nginx/sites-available/example" <<EOF
	server {
	    listen 80 default;    location /static { root /usr/local/share/rack/example/static; }
	    location / { proxy_pass http://127.0.0.1:8080; }}
	EOF
	[ "$MD5SUM" != "$(md5sum "/etc/nginx/sites-available/example")" ] && SERVICE_sysvinit_nginx=1
	MD5SUM="$(md5sum "/etc/nginx/sites-enabled/example" 2>/dev/null)"
	mkdir -p "/etc/nginx/sites-enabled"
	ln -s "/etc/nginx/sites-available/example" "/etc/nginx/sites-enabled/example"
	[ "$MD5SUM" != "$(md5sum "/etc/nginx/sites-enabled/example")" ] && SERVICE_sysvinit_nginx=1
	MD5SUM="$(md5sum "/etc/unicorn.conf.rb" 2>/dev/null)"
	mkdir -p "/etc"
	(
	set +x
	. "lib/mustache.sh"
	for F in */blueprint-template.d/*.sh
	do
	    . "$F"
	done
	export WORKER_PROCESSES="$(expr 4 \* $CORES)"
	mustache >"/etc/unicorn.conf.rb" <<EOF
	worker_processes {{WORKER_PROCESSES}}
	EOF
	)
	[ "$MD5SUM" != "$(md5sum "/etc/unicorn.conf.rb")" ] && SERVICE_upstart_example=1
	export APT_LISTBUGS_FRONTEND="none"
	export APT_LISTCHANGES_FRONTEND="none"
	export DEBIAN_FRONTEND="noninteractive"
	apt-get -q update
	[ "$(dpkg-query -f'${Version}\n' -W mysql-client-5.1)" = "5.1.58-1ubuntu1" ] || apt-get -y -q -o DPkg::Options::=--force-confold install mysql-client-5.1=5.1.58-1ubuntu1
	[ "$(dpkg-query -f'${Version}\n' -W nginx-common)" = "1.0.5-1" ] || { apt-get -y -q -o DPkg::Options::=--force-confold install nginx-common=1.0.5-1; SERVICE_sysvinit_nginx=1; }
	[ "$(dpkg-query -f'${Version}\n' -W nginx-light)" = "1.0.5-1" ] || apt-get -y -q -o DPkg::Options::=--force-confold install nginx-light=1.0.5-1
	[ "$(dpkg-query -f'${Version}\n' -W ruby-dev)" = "4.8" ] || apt-get -y -q -o DPkg::Options::=--force-confold install ruby-dev=4.8
	[ "$(dpkg-query -f'${Version}\n' -W rubygems)" = "1.7.2-1" ] || apt-get -y -q -o DPkg::Options::=--force-confold install rubygems=1.7.2-1
	gem -i -v0.3.11 fpm >/dev/null || gem install --no-rdoc --no-ri -v0.3.11 fpm
	gem -i -v0.8.5 hpricot >/dev/null || gem install --no-rdoc --no-ri -v0.8.5 hpricot
	gem -i -v1.6.3 json >/dev/null || gem install --no-rdoc --no-ri -v1.6.3 json
	gem -i -v2.6.0 kgio >/dev/null || gem install --no-rdoc --no-ri -v2.6.0 kgio
	gem -i -v0.99.4 mustache >/dev/null || gem install --no-rdoc --no-ri -v0.99.4 mustache
	gem -i -v1.3.5 rack >/dev/null || gem install --no-rdoc --no-ri -v1.3.5 rack
	gem -i -v1.1.4 rack-protection >/dev/null || gem install --no-rdoc --no-ri -v1.1.4 rack-protection
	gem -i -v0.8.0 raindrops >/dev/null || gem install --no-rdoc --no-ri -v0.8.0 raindrops
	gem -i -v1.6.8 rdiscount >/dev/null || gem install --no-rdoc --no-ri -v1.6.8 rdiscount
	gem -i -v1.3.1 sinatra >/dev/null || gem install --no-rdoc --no-ri -v1.3.1 sinatra
	gem -i -v1.3.3 tilt >/dev/null || gem install --no-rdoc --no-ri -v1.3.3 tilt
	gem -i -v4.1.1 unicorn >/dev/null || gem install --no-rdoc --no-ri -v4.1.1 unicorn
	[ -n "$SERVICE_sysvinit_nginx" ] && /etc/init.d/nginx restart
	[ -n "$SERVICE_upstart_example" ] && { restart example || start example; }

----

<h1 id="push-pull">Sharing and distributing blueprints</h1>

We at DevStructure saw the workflow unfolding around these generated shell scripts and in them an opportunity for a macro don't-repeat-yourself optimization.  Thus were born `blueprint-push`(1) and `blueprint-pull`(1).

`blueprint-push` uploads the JSON document and all source tarballs referenced by a blueprint to `devstructure.com`, which stores them behind a long secret key in AWS S3.  The URL that may be used to pull the blueprint later is printed to standard output.

<pre><code>blueprint push <em>name</em></code></pre>

The first time you run this command it will prompt you with the contents of `/etc/blueprint.cfg` which you can optionally put in place.  If you do, Blueprint will reuse the same secret the next time `blueprint-push` is called.  Configuring a secret this way allows you to push revisions to your blueprints which can then be pulled from a known location.

`blueprint-pull` downloads the JSON document and all source tarballs referenced by a blueprint that has been pushed and stores them in the local Git repository.  Typically, it accepts the URL printed by `blueprint-push` but if you configure a default secret in `/etc/blueprint.cfg`, you can pull blueprints by only their name.

<pre><code>blueprint pull <em>url</em></code></pre>

<pre><code>blueprint pull <em>name</em></code></pre>

Just as `blueprint-show`'s `-S` option helps bootstrap systems with zero dependencies, `devstructure.com` can generate shell scripts remotely so Blueprint doesn't have to be installed ahead of time.  You can bootstrap a new system from a pushed blueprint in one command:

<pre><code>curl https://devstructure.com/<em>secret</em>/<em>name</em>/<em>name</em>.sh | sh</code></pre>

An open-source edition of the server is in the works.

Example
-------

Push the _example_ blueprint to `devstructure.com`:

	blueprint push example

Now configure a production system to apply the latest revision to _example_ every half hour (this behavior should be familiar to Puppet and Chef users).  In `root`'s crontab:

	*/30 * * * * curl https://devstructure.com/0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-/example/example.sh | sh

----

<h1 id="puppet-chef">Generating Puppet modules and Chef cookbooks</h1>

Blueprint can also streamline the development workflow in Puppet- or Chef-managed environments by generating complete Puppet modules or Chef cookbooks.

Generate a Puppet module in <code><em>name</em>/manifests/init.pp</code>:

<pre><code>blueprint show -P <em>name</em></code></pre>

Generate a Chef cookbook in <code><em>name</em>/recipes/default.rb</code>:

<pre><code>blueprint show -C <em>name</em></code></pre>

These modules and cookbooks may be included directly in any Puppet or Chef environment or be used as the starting point for further development &mdash; the code is formatted according to the style guidelines of the respective communities.

Note, however, that the file templates used by Blueprint are incompatible with Puppet and Chef and so can't be included in the generated modules and cookbooks.

Example
-------

Running `blueprint show -P example` creates `example/manifests/init.pp` as follows and bundles the source tarball containing our example application.  `example/manifests/init.pp`:

	#
	# Automatically generated by blueprint(7).  Edit at your own risk.
	#
	class example {
		Exec {
			path => '/home/rcrowley/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games',
		}
		Class['sources'] -> Class['files'] -> Class['packages']
		class files {
			file {
				'/etc':
					ensure => directory;
				'/etc/init':
					ensure => directory;
				'/etc/init/example.conf':
					content => template('example/etc/init/example.conf'),
					ensure  => file,
					group   => root,
					mode    => 0644,
					owner   => root;
				'/etc/nginx':
					ensure => directory;
				'/etc/nginx/sites-available':
					ensure => directory;
				'/etc/nginx/sites-available/example':
					content => template('example/etc/nginx/sites-available/example'),
					ensure  => file,
					group   => root,
					mode    => 0644,
					owner   => root;
				'/etc/nginx/sites-enabled':
					ensure => directory;
				'/etc/nginx/sites-enabled/example':
					ensure => '/etc/nginx/sites-available/example',
					group  => root,
					owner  => root;
				'/etc/unicorn.conf.rb':
					content => template('example/etc/unicorn.conf.rb'),
					ensure  => file,
					group   => root,
					mode    => 0644,
					owner   => root;
			}
		}
		include files
		class packages {
			Class['apt'] -> Class['rubygems']
			exec { 'apt-get -q update':
				before => Class['apt'],
			}
			class apt {
				package {
					'mysql-client-5.1':
						ensure => '5.1.58-1ubuntu1';
					'nginx-common':
						ensure => '1.0.5-1';
					'nginx-light':
						ensure => '1.0.5-1';
					'ruby-dev':
						ensure => '4.8';
					'rubygems':
						ensure => '1.7.2-1';
				}
			}
			include apt
			class rubygems {
				package {
					'fpm':
						ensure   => '0.3.11',
						provider => gem;
					'hpricot':
						ensure   => '0.8.5',
						provider => gem;
					'json':
						ensure   => '1.6.3',
						provider => gem;
					'kgio':
						ensure   => '2.6.0',
						provider => gem;
					'mustache':
						ensure   => '0.99.4',
						provider => gem;
					'rack':
						ensure   => '1.3.5',
						provider => gem;
					'rack-protection':
						ensure   => '1.1.4',
						provider => gem;
					'raindrops':
						ensure   => '0.8.0',
						provider => gem;
					'rdiscount':
						ensure   => '1.6.8',
						provider => gem;
					'sinatra':
						ensure   => '1.3.1',
						provider => gem;
					'tilt':
						ensure   => '1.3.3',
						provider => gem;
					'unicorn':
						ensure   => '4.1.1',
						provider => gem;
				}
			}
			include rubygems
		}
		include packages
		class services {
			class sysvinit {
				service { 'nginx':
					enable    => true,
					ensure    => running,
					subscribe => [File['/etc/nginx/sites-available/example'], File['/etc/nginx/sites-enabled/example'], Package['nginx-common'], Exec['82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar']],
				}
			}
			include sysvinit
			class upstart {
				service { 'example':
					enable    => true,
					ensure    => running,
					provider  => upstart,
					subscribe => [File['/etc/unicorn.conf.rb'], Exec['82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar']],
				}
			}
			include upstart
		}
		include services
		class sources {
			exec { 'tar xf /tmp/82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar':
				alias => '/usr/local',
				cwd   => '/usr/local',
			}
			file { '/tmp/82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar':
				before => Exec['/usr/local'],
				group  => root,
				mode   => 0644,
				owner  => root,
				source => 'puppet:///modules/example/tmp/82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar',
			}
		}
		include sources
	}

Running `blueprint show -C example` creates `example/recipes/default.rb` as follows and bundles the source tarball containing our example application.  `example/recipes/default.rb`:

	#
	# Automatically generated by blueprint(7).  Edit at your own risk.
	#
	cookbook_file('/tmp/82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar') do
	  backup false
	  group 'root'
	  mode '0644'
	  owner 'root'
	  source 'tmp/82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar'
	end
	execute('tar xf "/tmp/82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar"') { cwd '/usr/local' }
	directory('/etc/init') do
	  group 'root'
	  mode '0755'
	  owner 'root'
	  recursive true
	end
	cookbook_file('/etc/init/example.conf') do
	  backup false
	  group 'root'
	  mode '0644'
	  owner 'root'
	  source 'etc/init/example.conf'
	end
	directory('/etc/nginx/sites-available') do
	  group 'root'
	  mode '0755'
	  owner 'root'
	  recursive true
	end
	cookbook_file('/etc/nginx/sites-available/example') do
	  backup false
	  group 'root'
	  mode '0644'
	  owner 'root'
	  source 'etc/nginx/sites-available/example'
	end
	directory('/etc/nginx/sites-enabled') do
	  group 'root'
	  mode '0755'
	  owner 'root'
	  recursive true
	end
	link('/etc/nginx/sites-enabled/example') do
	  group 'root'
	  owner 'root'
	  to '/etc/nginx/sites-available/example'
	end
	directory('/etc') do
	  group 'root'
	  mode '0755'
	  owner 'root'
	  recursive true
	end
	cookbook_file('/etc/unicorn.conf.rb') do
	  backup false
	  group 'root'
	  mode '0644'
	  owner 'root'
	  source 'etc/unicorn.conf.rb'
	end
	execute('apt-get -q update')
	package('mysql-client-5.1') { version '5.1.58-1ubuntu1' }
	package('nginx-common') { version '1.0.5-1' }
	package('nginx-light') { version '1.0.5-1' }
	package('ruby-dev') { version '4.8' }
	package('rubygems') { version '1.7.2-1' }
	gem_package('fpm') { version '0.3.11' }
	gem_package('hpricot') { version '0.8.5' }
	gem_package('json') { version '1.6.3' }
	gem_package('kgio') { version '2.6.0' }
	gem_package('mustache') { version '0.99.4' }
	gem_package('rack') { version '1.3.5' }
	gem_package('rack-protection') { version '1.1.4' }
	gem_package('raindrops') { version '0.8.0' }
	gem_package('rdiscount') { version '1.6.8' }
	gem_package('sinatra') { version '1.3.1' }
	gem_package('tilt') { version '1.3.3' }
	gem_package('unicorn') { version '4.1.1' }
	service('nginx') do
	  action [:enable, :start]
	  subscribes :restart, resources('cookbook_file[/etc/nginx/sites-available/example]', 'cookbook_file[/etc/nginx/sites-enabled/example]', 'package[nginx-common]', 'execute[82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar]')
	end
	service('example') do
	  action [:enable, :start]
	  provider Chef::Provider::Service::Upstart
	  subscribes :restart, resources('cookbook_file[/etc/unicorn.conf.rb]', 'execute[82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar]')
	end

----

<h1 id="cloudformation">Integrating with AWS CloudFormation</h1>

Production environments are much more than a rack of servers these days and nowhere is that more apparent than AWS.  Blueprint integrates with AWS CloudFormation to provision and bootstrap entire infrastructures declaratively.

The `--cfn` option to `blueprint-show`(1) generates the skeleton of a CloudFormation template that provisions a single EC2 instance running Amazon Linux (an RPM-based distribution supported by Amazon) which will apply the blueprint during its first boot.

File templates and source tarballs aren't supported seamlessly, however.  File templates can be recreated using CloudFormation's primitive string functions or an executable user-data.  Source tarballs may reference fully-qualified URLs.

Example
-------

Running `blueprint show --cfn example` creates `example.json`:

	{
	  "AWSTemplateFormatVersion": "2010-09-09", 
	  "Description": "Create an Amazon EC2 instance and bootstrap it as instructed by a blueprint.  This is intended to be a starting point for building larger architectures with AWS CloudFormation.  **WARNING** This template creates an Amazon EC2 instance.  You will be billed for the AWS resources used if you create a stack from this template.", 
	  "Mappings": {
	    "AWSInstanceType2Arch": {
	      "c1.medium": {
	        "Arch": "32"
	      }, 
	      "c1.xlarge": {
	        "Arch": "64"
	      }, 
	      "cc1.4xlarge": {
	        "Arch": "64"
	      }, 
	      "m1.large": {
	        "Arch": "64"
	      }, 
	      "m1.small": {
	        "Arch": "32"
	      }, 
	      "m1.xlarge": {
	        "Arch": "64"
	      }, 
	      "m2.2xlarge": {
	        "Arch": "64"
	      }, 
	      "m2.4xlarge": {
	        "Arch": "64"
	      }, 
	      "m2.xlarge": {
	        "Arch": "64"
	      }, 
	      "t1.micro": {
	        "Arch": "32"
	      }
	    }, 
	    "AWSRegionArch2AMI": {
	      "ap-northeast-1": {
	        "32": "ami-dcfa4edd", 
	        "64": "ami-e8fa4ee9"
	      }, 
	      "ap-southeast-1": {
	        "32": "ami-74dda626", 
	        "64": "ami-7edda62c"
	      }, 
	      "eu-west-1": {
	        "32": "ami-24506250", 
	        "64": "ami-20506254"
	      }, 
	      "us-east-1": {
	        "32": "ami-7f418316", 
	        "64": "ami-7341831a"
	      }, 
	      "us-west-1": {
	        "32": "ami-951945d0", 
	        "64": "ami-971945d2"
	      }
	    }
	  }, 
	  "Outputs": {
	    "PublicDnsName": {
	      "Description": "Public DNS name of the EC2 instance.", 
	      "Value": {
	        "Fn::GetAtt": [
	          "EC2Instance", 
	          "PublicDnsName"
	        ]
	      }
	    }
	  }, 
	  "Parameters": {
	    "InstanceType": {
	      "AllowedValues": [
	        "t1.micro", 
	        "m1.small", 
	        "m1.large", 
	        "m1.xlarge", 
	        "m2.xlarge", 
	        "m2.2xlarge", 
	        "m2.4xlarge", 
	        "c1.medium", 
	        "c1.xlarge", 
	        "cc1.4xlarge"
	      ], 
	      "ConstraintDescription": "must be a valid EC2 instance type.", 
	      "Default": "m1.small", 
	      "Description": "EC2 instance type.", 
	      "Type": "String"
	    }, 
	    "KeyName": {
	      "Description": "Name of an existing EC2 KeyPair to enable SSH access to the instances", 
	      "Type": "String"
	    }
	  }, 
	  "Resources": {
	    "CfnUser": {
	      "Properties": {
	        "Path": "/", 
	        "Policies": [
	          {
	            "PolicyDocument": {
	              "Statement": [
	                {
	                  "Action": "cloudformation:DescribeStackResource", 
	                  "Effect": "Allow", 
	                  "Resource": "*"
	                }
	              ]
	            }, 
	            "PolicyName": "root"
	          }
	        ]
	      }, 
	      "Type": "AWS::IAM::User"
	    }, 
	    "EC2Instance": {
	      "Metadata": {
	        "AWS::CloudFormation::Init": {
	          "config": {
	            "files": {
	              "/etc/init/example.conf": {
	                "content": "description \"Example\"\nstart on runlevel [2345]\nstop on runlevel [!2345]\nrespawn\nchdir /usr/local/share/rack/example\nexec unicorn -c /etc/unicorn.conf.rb\n# Dear Blueprint, restart me when /etc/database.yml changes.\n", 
	                "encoding": "plain", 
	                "group": "root", 
	                "mode": "100644", 
	                "owner": "root"
	              }, 
	              "/etc/nginx/sites-available/example": {
	                "content": "server {\n\tlisten 80 default;\n\tlocation /static { root /usr/local/share/rack/example/static; }\n\tlocation / { proxy_pass http://127.0.0.1:8080; }\n}\n", 
	                "encoding": "plain", 
	                "group": "root", 
	                "mode": "100644", 
	                "owner": "root"
	              }, 
	              "/etc/nginx/sites-enabled/example": {
	                "content": "/etc/nginx/sites-available/example", 
	                "encoding": "plain", 
	                "group": "root", 
	                "mode": "120777", 
	                "owner": "root"
	              }, 
	              "/etc/unicorn.conf.rb": {
	                "content": "worker_processes 4\n", 
	                "encoding": "plain", 
	                "group": "root", 
	                "mode": "100644", 
	                "owner": "root"
	              }
	            }, 
	            "packages": {
	              "apt": {
	                "mysql-client-5.1": [
	                  "5.1.58-1ubuntu1"
	                ], 
	                "nginx-common": [
	                  "1.0.5-1"
	                ], 
	                "nginx-light": [
	                  "1.0.5-1"
	                ], 
	                "ruby-dev": [
	                  "4.8"
	                ], 
	                "rubygems": [
	                  "1.7.2-1"
	                ]
	              }, 
	              "rubygems": {
	                "fpm": [
	                  "0.3.11"
	                ], 
	                "hpricot": [
	                  "0.8.5"
	                ], 
	                "json": [
	                  "1.6.3"
	                ], 
	                "kgio": [
	                  "2.6.0"
	                ], 
	                "mustache": [
	                  "0.99.4"
	                ], 
	                "rack": [
	                  "1.3.5"
	                ], 
	                "rack-protection": [
	                  "1.1.4"
	                ], 
	                "raindrops": [
	                  "0.8.0"
	                ], 
	                "rdiscount": [
	                  "1.6.8"
	                ], 
	                "sinatra": [
	                  "1.3.1"
	                ], 
	                "tilt": [
	                  "1.3.3"
	                ], 
	                "unicorn": [
	                  "4.1.1"
	                ]
	              }
	            }, 
	            "services": {
	              "sysvinit": {
	                "nginx": {
	                  "enable": true, 
	                  "ensureRunning": true, 
	                  "files": [
	                    "/etc/nginx/sites-enabled/example", 
	                    "/etc/nginx/sites-available/example"
	                  ], 
	                  "packages": {
	                    "apt": [
	                      "nginx-common"
	                    ]
	                  }, 
	                  "sources": [
	                    "/usr/local"
	                  ]
	                }
	              }, 
	              "upstart": {
	                "example": {
	                  "enable": true, 
	                  "ensureRunning": true, 
	                  "files": [
	                    "/etc/unicorn.conf.rb"
	                  ], 
	                  "sources": [
	                    "/usr/local"
	                  ]
	                }
	              }
	            }, 
	            "sources": {
	              "/usr/local": "82789250f3ad94d4cfeacc0a8cabae2d26b0270e.tar"
	            }
	          }
	        }
	      }, 
	      "Properties": {
	        "ImageId": {
	          "Fn::FindInMap": [
	            "AWSRegionArch2AMI", 
	            {
	              "Ref": "AWS::Region"
	            }, 
	            {
	              "Fn::FindInMap": [
	                "AWSInstanceType2Arch", 
	                {
	                  "Ref": "InstanceType"
	                }, 
	                "Arch"
	              ]
	            }
	          ]
	        }, 
	        "InstanceType": {
	          "Ref": "InstanceType"
	        }, 
	        "KeyName": {
	          "Ref": "KeyName"
	        }, 
	        "SecurityGroups": [
	          {
	            "Ref": "SecurityGroup"
	          }
	        ], 
	        "UserData": {
	          "Fn::Base64": {
	            "Fn::Join": [
	              "", 
	              [
	                "#!/bin/bash\n", 
	                "/opt/aws/bin/cfn-init -s ", 
	                {
	                  "Ref": "AWS::StackName"
	                }, 
	                " -r EC2Instance ", 
	                " --access-key ", 
	                {
	                  "Ref": "HostKeys"
	                }, 
	                " --secret-key ", 
	                {
	                  "Fn::GetAtt": [
	                    "HostKeys", 
	                    "SecretAccessKey"
	                  ]
	                }, 
	                " --region ", 
	                {
	                  "Ref": "AWS::Region"
	                }, 
	                "\n", 
	                "/opt/aws/bin/cfn-signal -e $? '", 
	                {
	                  "Ref": "WaitHandle"
	                }, 
	                "'\n"
	              ]
	            ]
	          }
	        }
	      }, 
	      "Type": "AWS::EC2::Instance"
	    }, 
	    "HostKeys": {
	      "Properties": {
	        "UserName": {
	          "Ref": "CfnUser"
	        }
	      }, 
	      "Type": "AWS::IAM::AccessKey"
	    }, 
	    "SecurityGroup": {
	      "Properties": {
	        "GroupDescription": "SSH access only.", 
	        "SecurityGroupIngress": [
	          {
	            "CidrIp": "0.0.0.0/0", 
	            "FromPort": "22", 
	            "IpProtocol": "tcp", 
	            "ToPort": "22"
	          }
	        ]
	      }, 
	      "Type": "AWS::EC2::SecurityGroup"
	    }, 
	    "WaitCondition": {
	      "DependsOn": "EC2Instance", 
	      "Properties": {
	        "Handle": {
	          "Ref": "WaitHandle"
	        }, 
	        "Timeout": "600"
	      }, 
	      "Type": "AWS::CloudFormation::WaitCondition"
	    }, 
	    "WaitHandle": {
	      "Type": "AWS::CloudFormation::WaitConditionHandle"
	    }
	  }
	}

----

<h1 id="deploy">Deploying your application with Blueprint</h1>

The example running throughout this tutorial takes advantage of Blueprint's default handling of `/usr/local` to package up an example web application.  As an application grows, this can become muddled by other packages you install from source.

Blueprint doesn't dictate how you deploy your applications but here are a few options play very nicely with Blueprint.

* Build Debian packages or RPMs for your application.  These packages can include service init scripts or configuration files which Blueprint will take into account when restarting services after a deploy.
* Use Blueprint to scaffold your application deployment and some other method (possibly via SSH tools like Capistrano or Fabric) to actually deploy.

And remember to use templates to render configuration files appropriately in development, staging, and production.

----

<h1 id="git">Local Git repository</h1>

Blueprints are stored in the local Git repository `~/.blueprints.git`.  Direct access isn't typically needed but Blueprint comes with the `blueprint-git`(1) tool that simplifies the parameters to `git`(1) needed to use this repository.

Example
-------

Clone the entire local Git repository into `blueprints` in the working directory:

	blueprint git clone

Show the diff, from Git's point-of-view, between the previous two revisions of the _example_ blueprint:

	blueprint git show example

The JSON document is pretty-printed for storage so Git's diffs will actually be meaningful.

----

<h1 id="contributing">Contributing to Blueprint</h1>

Blueprint is open-source, BSD-licensed software.  Contributions are welcome via pull requests on GitHub.

* Source code: <https://github.com/devstructure/blueprint>
* Issue tracker: <https://github.com/devstructure/blueprint/issues>
* Mailing list: <https://groups.google.com/forum/#!forum/blueprint-users>
* IRC: [`irc.freenode.net#devstructure`](irc://freenode.net/devstructure)

----

<h1 id="alternatives">Alternatives to Blueprint</h1>

If Blueprint's not your cup of tea, check out the following tools.  It's much better to have some form of configuration management than none at all.

* [Puppet](http://docs.puppetlabs.com)
* [Chef](http://wiki.opscode.com/display/chef/Home)
* [Bcfg2](http://trac.mcs.anl.gov/projects/bcfg2/)
* [CFEngine](http://cfengine.com/)
* [Juju](http://juju.ubuntu.com/)
