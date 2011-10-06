"""
Every backend provider defines a function named as the module that contains
it, which will be called when a blueprint is created.  This module gathers
those functions together.
"""

import glob
import os.path
import sys


__all__ = [os.path.basename(filename)[:-3]
           for filename in glob.glob(os.path.join(os.path.dirname(__file__),
                                                  '[!_]*.py'))]
for name in __all__:
    module = __import__(name, globals(), locals(), [], 1)
    setattr(sys.modules[__name__], name, getattr(module, name))
