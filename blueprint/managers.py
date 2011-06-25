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

    def __call__(self, package, version):
        """
        Return a shell command that installs the given version of the given
        package via this package manager.
        """

        if 'apt' == self:
            return ('[ "$(dpkg-query -f\'${{{{Version}}}}\\n\' -W {0})" '
                    '!= "{1}" ] && apt-get -y -q '
                    '-o DPkg::Options::=--force-confold install {0}={1}'
                   ).format(package, version)

        if 'yum' == self:
            match = re.match(r'^(\d+):(.+)$', version)
            if match is None:
                return ('rpm -q {0}-{1} >/dev/null '
                        '|| yum -y install {0}-{1}').format(package, version)
            else:
                return ('rpm -q {0}:{1}-{2} >/dev/null '
                        '|| yum -y install {1}-{3}').format(match.group(1),
                                                            package,
                                                            match.group(2),
                                                            version)

        if 'rubygems' == self:
            return 'gem install {0} -v{1}'.format(package, version)
        match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)', self)
        if match is not None:
            # FIXME PATH might have a thing to say about this.
            return 'gem{0} install {1} -v{2}'.format(match.group(1),
                                                     package,
                                                     version)

        if 'python' == self:
            return 'easy_install {0}'.format(package)
        match = re.match(r'^python(\d+\.\d+)', self)
        if match is not None:
            return 'easy_install-{0} {1}'.format(match.group(1), package)
        if 'pip' == self or 'python-pip' == self:
            return 'pip install {0}=={1}'.format(package, version)

        if 'php-pear' == self:
            return 'pear install {0}-{1}'.format(package, version)
        if self in ('php5-dev', 'php-devel'):
            return 'pecl install {0}-{1}'.format(package, version)

        return ': unknown manager {0} for {1} {2}'.format(self,
                                                          package,
                                                          version)


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
            return '[ -n "${0}" ] && restart {1}'.format(self.env_var(service),
                                                         service)

        return '[ -n "${0}" ] && /etc/init.d/{1} restart'.format(
            self.env_var(service), service)
