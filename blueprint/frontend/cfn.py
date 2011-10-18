"""
AWS CloudFormation template generator.
"""

import copy
import json
import os.path

from blueprint import util


def cfn(b, relaxed=False):
    if relaxed:
        b_relaxed = copy.deepcopy(b)
        def package(manager, package, version):
            b_relaxed.packages[manager][package] = []
        b.walk(package=package)
        return Template(b_relaxed)
    return Template(b)


class Template(dict):
    """
    An AWS CloudFormation template that contains a blueprint.
    """

    def __init__(self, b):
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
        return util.json_dumps(self)

    def dumpf(self, gzip=False):
        pass
