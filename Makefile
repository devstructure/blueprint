VERSION=3.0.7
BUILD=1

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
		*.deb \
		setup.py build dist *.egg *.egg-info \
		man/man*/*.html
	find . -name \*.pyc -delete

install: install-bin install-lib install-man install-sysconf

install-bin:
	install -d $(DESTDIR)$(bindir)
	find bin -type f -printf %P\\n | while read PROGNAME \
	; do \
		{ \
			head -n1 bin/$$PROGNAME | sed "s@#!/usr/bin/python@#!$(PYTHON)@"; \
			tail -n+2 bin/$$PROGNAME; \
		} >$(DESTDIR)$(bindir)/$$PROGNAME; \
		chmod 755 $(DESTDIR)$(bindir)/$$PROGNAME; \
	done

install-lib:
	find blueprint -type d -printf %P\\0 | xargs -0r -I__ install -d $(DESTDIR)$(pydir)/blueprint/__
	find blueprint -type f -name \*.py -printf %P\\0 | xargs -0r -I__ install -m644 blueprint/__ $(DESTDIR)$(pydir)/blueprint/__
	PYTHONPATH=$(DESTDIR)$(pydir) $(PYTHON) -mcompileall $(DESTDIR)$(pydir)/blueprint

install-man:
	find man -type d -printf %P\\0 | xargs -0r -I__ install -d $(DESTDIR)$(mandir)/__
	find man -type f -name \*.[12345678] -printf %P\\0 | xargs -0r -I__ install -m644 man/__ $(DESTDIR)$(mandir)/__
	find man -type f -name \*.[12345678] -printf %P\\0 | xargs -0r -I__ gzip $(DESTDIR)$(mandir)/__

install-sysconf:
	find etc -type d -printf %P\\0 | xargs -0r -I__ install -d $(DESTDIR)$(sysconfdir)/__
	find etc -type f -printf %P\\0 | xargs -0r -I__ install -m644 etc/__ $(DESTDIR)$(sysconfdir)/__

uninstall: uninstall-bin uninstall-lib uninstall-man uninstall-sysconf

uninstall-bin:
	find bin -type f -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(bindir)/__
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(bindir) || true

uninstall-lib:
	find blueprint -type f -name \*.py -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(pydir)/blueprint/__ $(DESTDIR)$(pydir)/blueprint/__c
	find blueprint -depth -mindepth 1 -type d -printf %P\\0 | xargs -0r -I__ rmdir $(DESTDIR)$(pydir)/blueprint/__ || true
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(pydir)/blueprint || true

uninstall-man:
	find man -type f -name \*.[12345678] -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(mandir)/__.gz
	find man -depth -mindepth 1 -type d -printf %P\\0 | xargs -0r -I__ rmdir $(DESTDIR)$(mandir)/__ || true
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(mandir) || true

uninstall-sysconf:
	find etc -type f -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(sysconfdir)/__
	find etc -depth -mindepth 1 -type d -printf %P\\0 | xargs -0r -I__ rmdir $(DESTDIR)$(sysconfdir)/__ || true
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(sysconfdir) || true

build:
	sudo make build-deb
	make build-pypi

build-deb:
	make install prefix=/usr sysconfdir=/etc DESTDIR=debian
	FPM_EDITOR="echo 'Replaces: blueprint-io' >>" fpm -s dir -t deb -C debian \
		-n blueprint -v $(VERSION)-$(BUILD)py$(PYTHON_VERSION) -a all \
		-d git-core \
		-d python$(PYTHON_VERSION) \
		-m "Richard Crowley <richard@devstructure.com>" \
		--url "https://github.com/devstructure/blueprint" \
		--description "Reverse-engineer server configuration." \
		--edit
	make uninstall prefix=/usr sysconfdir=/etc DESTDIR=debian

build-pypi:
	m4 -D__VERSION__=$(VERSION) setup.py.m4 >setup.py
	$(PYTHON) setup.py bdist_egg

deploy: deploy-deb deploy-pypi

deploy-deb:
	scp -i ~/production.pem blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb ubuntu@packages.devstructure.com:
	make deploy-deb-$(PYTHON_VERSION)
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "rm blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"

deploy-deb-2.6:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight add blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb apt/lenny apt/squeeze apt/lucid apt/maverick"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight cache apt/lenny apt/squeeze apt/lucid apt/maverick"

deploy-deb-2.7:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight add blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb apt/natty"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight cache apt/natty"

deploy-pypi:
	$(PYTHON) setup.py sdist upload

man:
	find man -name \*.ronn | PATH="$(HOME)/work/ronn/bin:$(PATH)" RUBYLIB="$(HOME)/work/ronn/lib" xargs -n1 ronn --manual=Blueprint --organization=DevStructure --style=toc

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

.PHONY: all clean install install-bin install-lib install-man install-sysconf uninstall uninstall-bin uninstall-lib uninstall-man uninstall-sysconf build build-deb build-pypi deploy deploy-deb deploy-deb-2.6 deploy-deb-2.7 deploy-pypi man gh-pages
