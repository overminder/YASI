from pypy.rlib.jit import unroll_safe
from tvm.lang.model import W_Root

class W_NativeFunction(W_Root):
    @unroll_safe
    def call(self, args_w):
        raise NotImplementedError

