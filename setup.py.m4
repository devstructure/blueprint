from setuptools import setup, find_packages
import re

setup(name='blueprint',
      version='__VERSION__',
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
      zip_safe=False)
