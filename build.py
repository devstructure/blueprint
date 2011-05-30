from django import template
from django.conf import settings
from django.template import Context, Template
from django.template import defaultfilters
from django.template import loader
import os.path

settings.configure(DEBUG=True,
                   TEMPLATE_DEBUG=True,
                   TEMPLATE_LOADERS=(
                       'django.template.loaders.filesystem.Loader',
                   ),
                   TEMPLATE_DIRS=(
                       os.path.join(os.path.dirname(__file__), 'templates'),
                   ))

def page(source):
    t = Template('\n'.join(['{% extends "page.html" %}', source]))
    return t.render(Context())

if '__main__' == __name__:
    import sys
    import __main__
    if 2 == len(sys.argv) and hasattr(__main__, sys.argv[1]):
        print(getattr(__main__, sys.argv[1])(sys.stdin.read()))
    else:
        sys.stderr.write('Usage: {0} [feed|page|title]\n')
        sys.exit(1)
