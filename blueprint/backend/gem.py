"""
Search for Ruby gems to include in the blueprint.
"""

import glob
import logging
import os
import re
import subprocess

import blueprint

def gem(b):
    logging.info('searching for Ruby gems')

    # Precompile a pattern for extracting the version of Ruby that was used
    # to install the gem.
    pattern = re.compile(r'gems/([^/]+)/gems')

    # Look for gems in all the typical places.  This is easier than looking
    # for `gem` commands, which may or may not be on `PATH`.
    for globname in ('/usr/lib/ruby/gems/*/gems',
                     '/usr/local/lib/ruby/gems/*/gems',
                     '/var/lib/gems/*/gems'):
        for dirname in glob.glob(globname):

            # The `ruby1.9.1` (really 1.9.2) package on Maverick begins
            # including RubyGems in the `ruby1.9.1` package and marks the
            # `rubygems1.9.1` package as virtual.  So for Maverick and
            # newer, the manager is actually `ruby1.9.1`.
            match = pattern.search(dirname)
            if '1.9.1' == match.group(1) and blueprint.rubygems_virtual():
                manager = 'ruby{0}'.format(match.group(1))
            else:
                manager = 'rubygems{0}'.format(match.group(1))

            for entry in os.listdir(dirname):
                package, version = entry.rsplit('-', 1)
                b.packages[manager][package].append(version)
