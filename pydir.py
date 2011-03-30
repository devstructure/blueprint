from distutils.sysconfig import get_python_version, get_python_lib
import os.path
import sys
for s in ('dist', 'site'):
    pydir = os.path.join(sys.argv[1],
                         'python%s' % get_python_version(),
                         '%s-packages' % s)
    if pydir in sys.path:
        print(pydir)
        sys.exit(0)
print(get_python_lib())
