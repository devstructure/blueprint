VERSION=3.0.4
BUILD=3

PYTHON=$(shell which python2.7 || which python27 || which python2.6 || which python26 || which python)
PYTHON_VERSION=$(shell ${PYTHON} -c "from distutils.sysconfig import get_python_version; print(get_python_version())")

prefix=/usr/local
bindir=${prefix}/bin
libdir=${prefix}/lib
pydir=$(shell ${PYTHON} pydir.py ${libdir})
mandir=${prefix}/share/man
sysconfdir=${prefix}/etc

all:

clean:
	rm -rf \
		control *.deb \
		setup.py build dist *.egg *.egg-info \
		blueprint/**.pyc \
		man/man*/*.htm

install: install-bin install-lib install-man install-sysconf

install-bin:
	install -d $(DESTDIR)$(bindir)
	install bin/blueprint $(DESTDIR)$(bindir)/
	for PROGNAME in \
		blueprint-apply \
		blueprint-create \
		blueprint-destroy \
		blueprint-list \
		blueprint-show \
	; do \
		{ \
			echo "#!$(PYTHON)"; \
			tail -n+2 bin/$$PROGNAME; \
		} >$(DESTDIR)$(bindir)/$$PROGNAME; \
		chmod 755 $(DESTDIR)$(bindir)/$$PROGNAME; \
	done

install-lib:
	install -d $(DESTDIR)$(pydir)/blueprint/
	install -m644 \
		blueprint/chef.py \
		blueprint/context_managers.py \
		blueprint/deps.py \
		blueprint/git.py \
		blueprint/ignore.py \
		blueprint/__init__.py \
		blueprint/manager.py \
		blueprint/puppet.py \
		blueprint/sh.py \
		blueprint/util.py \
		$(DESTDIR)$(pydir)/blueprint/
	install -d $(DESTDIR)$(pydir)/blueprint/backend/
	install -m644 \
		blueprint/backend/apt.py \
		blueprint/backend/files.py \
		blueprint/backend/gem.py \
		blueprint/backend/__init__.py \
		blueprint/backend/php.py \
		blueprint/backend/pypi.py \
		blueprint/backend/sources.py \
		blueprint/backend/yum.py \
		$(DESTDIR)$(pydir)/blueprint/backend/
	PYTHONPATH=$(DESTDIR)$(pydir) $(PYTHON) -mcompileall \
		$(DESTDIR)$(pydir)/blueprint

install-man:
	install -d $(DESTDIR)$(mandir)/man1
	install -m644 \
		man/man1/blueprint.1 \
		man/man1/blueprint-apply.1 \
		man/man1/blueprint-create.1 \
		man/man1/blueprint-destroy.1 \
		man/man1/blueprint-list.1 \
		man/man1/blueprint-show.1 \
		$(DESTDIR)$(mandir)/man1/
	install -d $(DESTDIR)$(mandir)/man5
	install -m644 \
		man/man5/blueprint.5 \
		man/man5/blueprintignore.5 \
		$(DESTDIR)$(mandir)/man5/
	install -d $(DESTDIR)$(mandir)/man7
	install -m644 man/man7/blueprint.7 $(DESTDIR)$(mandir)/man7/

install-sysconf:
	install -d $(DESTDIR)$(sysconfdir)/bash_completion.d
	install -m644 etc/bash_completion.d/blueprint \
		$(DESTDIR)$(sysconfdir)/bash_completion.d/

uninstall: uninstall-bin uninstall-lib uninstall-man uninstall-sysconf

uninstall-bin:
	rm -f \
		$(DESTDIR)$(bindir)/blueprint \
		$(DESTDIR)$(bindir)/blueprint-apply \
		$(DESTDIR)$(bindir)/blueprint-create \
		$(DESTDIR)$(bindir)/blueprint-destroy \
		$(DESTDIR)$(bindir)/blueprint-list \
		$(DESTDIR)$(bindir)/blueprint-show
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(bindir)

uninstall-lib:
	rm -f \
		$(DESTDIR)$(pydir)/blueprint/chef.py \
		$(DESTDIR)$(pydir)/blueprint/chef.pyc \
		$(DESTDIR)$(pydir)/blueprint/context_managers.py \
		$(DESTDIR)$(pydir)/blueprint/context_managers.pyc \
		$(DESTDIR)$(pydir)/blueprint/deps.py \
		$(DESTDIR)$(pydir)/blueprint/deps.pyc \
		$(DESTDIR)$(pydir)/blueprint/git.py \
		$(DESTDIR)$(pydir)/blueprint/git.pyc \
		$(DESTDIR)$(pydir)/blueprint/ignore.py \
		$(DESTDIR)$(pydir)/blueprint/ignore.pyc \
		$(DESTDIR)$(pydir)/blueprint/__init__.py \
		$(DESTDIR)$(pydir)/blueprint/__init__.pyc \
		$(DESTDIR)$(pydir)/blueprint/manager.py \
		$(DESTDIR)$(pydir)/blueprint/manager.pyc \
		$(DESTDIR)$(pydir)/blueprint/puppet.py \
		$(DESTDIR)$(pydir)/blueprint/puppet.pyc \
		$(DESTDIR)$(pydir)/blueprint/sh.py \
		$(DESTDIR)$(pydir)/blueprint/sh.pyc \
		$(DESTDIR)$(pydir)/blueprint/util.py \
		$(DESTDIR)$(pydir)/blueprint/util.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/apt.py \
		$(DESTDIR)$(pydir)/blueprint/backend/apt.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/files.py \
		$(DESTDIR)$(pydir)/blueprint/backend/files.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/gem.py \
		$(DESTDIR)$(pydir)/blueprint/backend/gem.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/__init__.py \
		$(DESTDIR)$(pydir)/blueprint/backend/__init__.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/php.py \
		$(DESTDIR)$(pydir)/blueprint/backend/php.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/pypi.py \
		$(DESTDIR)$(pydir)/blueprint/backend/pypi.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/sources.py \
		$(DESTDIR)$(pydir)/blueprint/backend/sources.pyc \
		$(DESTDIR)$(pydir)/blueprint/backend/yum.py \
		$(DESTDIR)$(pydir)/blueprint/backend/yum.pyc
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(pydir)/blueprint/backend

uninstall-man:
	rm -f \
		$(DESTDIR)$(mandir)/man1/blueprint.1 \
		$(DESTDIR)$(mandir)/man1/blueprint-apply.1 \
		$(DESTDIR)$(mandir)/man1/blueprint-create.1 \
		$(DESTDIR)$(mandir)/man1/blueprint-destroy.1 \
		$(DESTDIR)$(mandir)/man1/blueprint-list.1 \
		$(DESTDIR)$(mandir)/man1/blueprint-show.1 \
		$(DESTDIR)$(mandir)/man5/blueprint.5 \
		$(DESTDIR)$(mandir)/man5/blueprintignore.5 \
		$(DESTDIR)$(mandir)/man7/blueprint.7
	rmdir -p --ignore-fail-on-non-empty \
		$(DESTDIR)$(mandir)/man1 \
		$(DESTDIR)$(mandir)/man5 \
		$(DESTDIR)$(mandir)/man7

uninstall-sysconf:
	rm -f $(DESTDIR)$(sysconfdir)/bash_completion.d/blueprint
	rmdir -p --ignore-fail-on-non-empty \
		$(DESTDIR)$(sysconfdir)/bash_completion.d

build:
	sudo make deb
	make pypi

deb:
	[ "$$(whoami)" = "root" ] || false
	m4 \
		-D__PYTHON__=python$(PYTHON_VERSION) \
		-D__VERSION__=$(VERSION)-$(BUILD)py$(PYTHON_VERSION) \
		$< >$@
	debra create debian control
	make install prefix=/usr sysconfdir=/etc DESTDIR=debian
	chown -R root:root debian
	debra build debian blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb
	debra destroy debian

pypi:
	m4 -D__VERSION__=$(VERSION) $< >$@
	$(PYTHON) setup.py bdist_egg

deploy: deploy-deb deploy-pypi

deploy-deb:
	scp -i ~/production.pem blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb ubuntu@packages.devstructure.com:
	make deploy-deb-$(PYTHON_VERSION)
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "rm blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"

deploy-deb-2.6:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "reprepro-includedeb debian lenny blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "reprepro-includedeb debian squeeze blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "reprepro-includedeb ubuntu lucid blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "reprepro-includedeb ubuntu maverick blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"

deploy-deb-2.7:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "reprepro-includedeb ubuntu natty blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"

deploy-pypi:
	$(PYTHON) setup.py sdist upload

man:
	find man -name \*.ronn | xargs -n1 ronn \
		--manual=Blueprint --organization=DevStructure --style=toc

gh-pages: man
	mkdir -p gh-pages
	find man -name \*.html | xargs -I__ mv __ gh-pages/
	git checkout -q gh-pages
	cp -R gh-pages/* ./
	rm -rf gh-pages
	git add .
	git commit -m "Rebuilt manual."
	git push origin gh-pages
	git checkout -q master

.PHONY: all build clean install install-bin install-lib install-man install-sysconf uninstall uninstall-bin uninstall-lib uninstall-man uninstall-sysconf deb deploy deploy-deb deploy-deb-2.6 deploy-deb-2.7 deploy-pypi man gh-pages
