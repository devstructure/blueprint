"""
Search for `yum` packages to include in the blueprint.
"""

import logging

CACHE = '/tmp/blueprint-yum-exclusions'

def yum(b):
    logging.info('searching for yum packages')
