from pypy.rlib.streamio import fdopen_as_stream

class Config(object):
    def __init__(self):
        self.vm_stacksize = 64
        self.stdin = fdopen_as_stream(0, 'r')
        self.stdout = fdopen_as_stream(1, 'a+')
        self.stderr = fdopen_as_stream(2, 'a+')

class ConfigPool(object):
    default = None

    def make_default(self):
        self.default = Config()

configpool = ConfigPool()


