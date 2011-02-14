"""
"""

import re

class Manager(dict):
    """
    """

    def __init__(self, name, *args, **kwargs):
        super(Manager, self).__init__(*args, **kwargs)
        self.name = name

    def __call__(self, package, version):
        """
        """

        if 'apt' == self.name:
            return 'apt-get -y install {0}={1}'.format(package, version)

        match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)', self.name)
        if match is not None:
            # FIXME PATH might have a thing to say about this.
            return 'gem{0} install {1} -v{2}'.format(match.group(1),
                                                     package,
                                                     version)

        match = re.match(r'^python(\d+\.\d+)', self.name)
        if match is not None:
            return 'easy_install-{0} {1}'.format(match.group(1), package)
        if 'pip' == self.name or 'python-pip' == self.name:
            return 'pip install {0}'.format(package)

        if 'php-pear' == self.name:
            return 'pear install {0}-{1}'.format(package, version)
        if 'php5-dev' == self.name:
            return 'pecl install {0}-{1}'.format(package, version)

        return ': unknown manager {0} for {1} {2}'.format(self.name,
                                                          package,
                                                          version)

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
