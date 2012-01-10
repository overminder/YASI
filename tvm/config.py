from pypy.rlib.streamio import fdopen_as_stream

class Config(object):
    vm_stacksize = 64
    stdin = None
    stdout = None
    stderr = None

    def open_file_handle(self):
        self.stdin = fdopen_as_stream(0, 'r')
        self.stdout = fdopen_as_stream(1, 'a+')
        self.stderr = fdopen_as_stream(2, 'a+')

default = Config()


