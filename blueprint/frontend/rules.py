"""
Blueprint rules generator
"""

import codecs
import gzip as gziplib


def rules(b, relaxed=False):
    """
    Generated Blueprint rules.
    """
    r = Rules(b.name, comment=b.DISCLAIMER)

    def source(dirname, filename, gen_content, url):
        r.append(':source:{0}'.format(dirname))

    def file(pathname, f):
        r.append(':file:{0}'.format(pathname))

    def package(manager, package, version):
        r.append(':package:{0}/{1}'.format(manager, package))

    def service(manager, service):
        r.append(':service:{0}/{1}'.format(manager, service))

    b.walk(source=source, file=file, package=package, service=service)

    return r


class Rules(list):

    def __init__(self, name, comment=None):
        if name is None:
            self.name = 'blueprint-generated-rules'
        else:
            self.name = name
        super(Rules, self).__init__()
        if comment is not None:
            self.append(comment)

    def dumpf(self, gzip=False):
        """
        Serialize the blueprint to a rules file.
        """
        if gzip:
            filename = '{0}.blueprint-rules.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.blueprint-rules'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')
        f.write(self.dumps())
        f.close()
        return filename

    def dumps(self):
        """
        Serialize the blueprint to rules.
        """
        return ''.join(['{0}\n'.format(item) for item in self])
