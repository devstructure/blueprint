# Legacy: needed by `blueprint-show -I <name>`.
class Rules(object):

    def __init__(self, content):
        self.content = content

    def dumps(self):
        return self.content

    def dumpf(self, gzip=False):
        raise NotImplementedError()
