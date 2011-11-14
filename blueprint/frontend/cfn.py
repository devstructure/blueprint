"""
AWS CloudFormation template generator.
"""

import codecs
import copy
import gzip as gziplib
import json
import logging
import os.path
import tarfile

from blueprint import util


def cfn(b, relaxed=False):
    b2 = copy.deepcopy(b)
    def file(pathname, f):
        if 'template' in f:
            logging.warning('file template {0} won\'t appear in generated '
                            'CloudFormation templates'.format(pathname))
            del b2.files[pathname]
    if relaxed:
        def package(manager, package, version):
            b2.packages[manager][package] = []
        b.walk(file=file, package=package)
    else:
        b.walk(file=file)
    return Template(b2)


class Template(dict):
    """
    An AWS CloudFormation template that contains a blueprint.
    """

    def __init__(self, b):
        self.b = b
        if b.name is None:
            self.name = 'blueprint-generated-cfn-template'
        else:
            self.name = b.name
        super(Template, self).__init__(json.load(open(
            os.path.join(os.path.dirname(__file__), 'cfn.json'))))
        b.normalize()
        self['Resources']['EC2Instance']['Metadata']\
            ['AWS::CloudFormation::Init']['config'] = b

    def dumps(self):
        """
        Serialize this AWS CloudFormation template to JSON in a string.
        """
        return util.json_dumps(self)

    def dumpf(self, gzip=False):
        """
        Serialize this AWS CloudFormation template to JSON in a file.
        """
        if 0 != len(self.b.sources):
            logging.warning('this blueprint contains source tarballs - '
                            'to use them with AWS CloudFormation, you must '
                            'store them online and edit the template to '
                            'reference their URLs')
        if gzip:
            filename = '{0}.json.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.json'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')
        f.write(self.dumps())
        f.close()
        return filename
