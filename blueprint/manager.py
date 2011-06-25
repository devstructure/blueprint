"""
"""

import re


class Manager(unicode):
    """
    """

    def __call__(self, package, version):
        """
        """

        if 'apt' == self:
            return ('apt-get -y -q -o DPkg::Options::=--force-confold ' +
                    'install {0}={1}').format(package, version)
        if 'yum' == self:
            return 'yum -y install {0}-{1}'.format(package, version)

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
