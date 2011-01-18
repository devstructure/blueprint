import os
import os.path
import pwd

def login():
    """
    Return the user's login as found in the filesystem.  This will be the
    default blueprint author.
    """
    if hasattr(login, '_cache'):
        return login._cache
    pw = pwd.getpwuid(os.geteuid())
    try:
        f = open(os.path.join(pw.pw_dir, '.login'), 'r')
        login._cache = f.read().rstrip()
        f.close()
    except IOError:
        login._cache = pw.pw_name
    return login._cache

def token():
    """
    Return the user's token as found in the filesystem.
    """
    if hasattr(token, '_cache'):
        return token._cache
    pw = pwd.getpwuid(os.geteuid())
    f = open(os.path.join(pw.pw_dir, '.token'), 'r')
    token._cache = f.read().rstrip()
    f.close()
    return token._cache
