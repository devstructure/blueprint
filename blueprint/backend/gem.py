import glob
import os
import re

def gem(b):
    pattern = re.compile(r'gems/([^/]+)/gems')
    for globname in ('/usr/lib/ruby/gems/*/gems',
                     '/usr/local/lib/ruby/gems/*/gems',
                     '/var/lib/gems/*/gems'):
        for dirname in glob.glob(globname):
            manager = 'rubygems{0}'.format(pattern.search(dirname).group(1))
            for entry in os.listdir(dirname):
                package, version = entry.rsplit('-', 1)
                b.packages[manager][package].append(version)
