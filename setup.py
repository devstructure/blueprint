from setuptools import setup, find_packages
import re

#pattern = re.compile(r'^VERSION=(.+)$')
#version = None
#for line in open('Makefile'):
#    match = pattern.match(line)
#    if match is None:
#        continue
#    version = match.group(1)
#    break
#if version is None:
#    raise EnvironmentError, '/^VERSION=/ not matched in Makefile.'
version = "3.0.2"

setup(name='blueprint',
      version=version,
      description='reverse engineer server configuration',
      author='Richard Crowley',
      author_email='richard@devstructure.com',
      url='http://devstructure.com/',
      packages=find_packages(),
      scripts=['bin/blueprint',
               'bin/blueprint-apply',
               'bin/blueprint-create',
               'bin/blueprint-destroy',
               'bin/blueprint-list',
               'bin/blueprint-show'],
      license='BSD',
      zip_safe=True)
