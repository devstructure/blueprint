"""
Managers are callable strings that can generate the commands needed by
resources.  They're mostly useful in the context of generated shell code.
"""

import re


class PackageManager(unicode):
    """
    Package managers each have their own syntax.  All supported package
    managers are encapsulated in this manager class.
    """

    def gate(self, package, version, relaxed=False):
        """
        Return a shell command that checks for the given version of the
        given package via this package manager.  It should exit non-zero
        if the package is not in the desired state.
        """
        if version is None:
            relaxed = True

        if 'apt' == self:
            if relaxed:
                return 'dpkg-query -W {0} >/dev/null'.format(package)
            else:
                return ('[ "$(dpkg-query -f\'${{{{Version}}}}\\n\' -W {0})" '
                        '= "{1}" ]').format(package, version)

        if 'rpm' == self:
            return 'rpm -q {0} >/dev/null'.format(package)
        if 'yum' == self:
            if relaxed:
                arg = package
            else:
                match = re.match(r'^\d+:(.+)$', version)
                if match is None:
                    arg = '{0}-{1}'.format(package, version)
                else:
                    arg = '{0}-{1}'.format(package, match.group(1))
            return 'rpm -q {0} >/dev/null'.format(arg)

        if 'rubygems' == self:
            if relaxed:
                return 'gem list -i {0} >/dev/null'.format(package)
            else:
                return 'gem -i -v{1} {0} >/dev/null'.format(package, version)
        match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)', self)
        if match is not None:
            if relaxed:
                return ('gem{0} list -i {1} >/dev/null'.
                        format(match.group(1), package))
            else:
                return ('gem{0} list -i -v{2} {1} >/dev/null'.
                        format(match.group(1), package, version))

        return None

    def install(self, package, version, relaxed=False):
        """
        Return a shell command that installs the given version of the given
        package via this package manager.
        """
        if version is None:
            relaxed = True

        if 'apt' == self:
            arg = package if relaxed else '{0}={1}'.format(package, version)
            return ('apt-get -y -q -o DPkg::Options::=--force-confold '
                    'install {0}').format(arg)

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        if 'rpm' == self:
            return 'rpm -U {0}'.format(version)

        if 'yum' == self:
            arg = package if relaxed else '{0}-{1}'.format(package, version)
            return 'yum -y install {0}'.format(arg)

        if 'rubygems' == self:
            if relaxed:
                return 'gem install --no-rdoc --no-ri {0}'.format(package)
            else:
                return ('gem install --no-rdoc --no-ri -v{1} {0}'.
                        format(package, version))
        match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)', self)
        if match is not None:
            if relaxed:
                return ('gem{0} install --no-rdoc --no-ri {1}'.
                        format(match.group(1), package))
            else:
                return ('gem{0} install --no-rdoc --no-ri -v{2} {1}'.
                        format(match.group(1), package, version))

        if 'python' == self:
            return 'easy_install {0}'.format(package)
        match = re.match(r'^python(\d+\.\d+)', self)
        if match is not None:
            return 'easy_install-{0} {1}'.format(match.group(1), package)
        if 'pip' == self or 'python-pip' == self:
            arg = package if relaxed else '{0}=={1}'.format(package, version)
            return 'pip install {0}'.format(arg)

        if 'php-pear' == self:
            arg = package if relaxed else '{0}-{1}'.format(package, version)
            return 'pear install {0}'.format(arg)
        if self in ('php5-dev', 'php-devel'):
            arg = package if relaxed else '{0}-{1}'.format(package, version)
            return 'pecl install {0}'.format(arg)

        if 'nodejs' == self:
            arg = package if relaxed else '{0}@{1}'.format(package, version)
            return 'npm install -g {0}'.format(arg)

        if relaxed:
            return ': unknown manager {0} for {1}'.format(self, package)
        else:
            return ': unknown manager {0} for {1} {2}'.format(self,
                                                              package,
                                                              version)

    def __call__(self, package, version, relaxed=False):
        """
        Return a shell command that checks for and possibly installs
        the given version of the given package.
        """
        gate = self.gate(package, version, relaxed)
        install = self.install(package, version, relaxed)
        if gate is None:
            return install
        return gate + ' || ' + install


class ServiceManager(unicode):
    """
    Service managers each have their own syntax.  All supported service
    managers are encapsulated in this manager class.
    """

    _env_pattern = re.compile(r'[^0-9A-Za-z]')

    def env_var(self, service):
        """
        Return the name of the environment variable being used to track the
        state of the given service.
        """
        return 'SERVICE_{0}_{1}'.format(self._env_pattern.sub('', self),
                                        self._env_pattern.sub('', service))

    def __call__(self, service):
        """
        Return a shell command that restarts the given service via this
        service manager.
        """

        if 'upstart' == self:
            return ('[ -n "${0}" ] && {{{{ restart {1} || start {1}; }}}}'.
                format(self.env_var(service), service))

        return '[ -n "${0}" ] && /etc/init.d/{1} restart'.format(
            self.env_var(service), service)
