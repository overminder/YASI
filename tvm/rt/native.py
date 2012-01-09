from pypy.rlib.jit import unroll_safe
from tvm.lang.model import W_Root

class W_NativeClosure(W_Root):
    _symbol_ = '?'

    @unroll_safe
    def call(self, args_w):
        raise NotImplementedError

    def to_string(self):
        return '#<native-closure %s>' % self.__class__._symbol_

class W_NativeClosureX(W_Root):
    _symbol_ = '?'

    @unroll_safe
    def call_with_frame(self, args_w, frame, tailp):
        raise NotImplementedError

    def to_string(self):
        return '#<native-closure %s>' % self.__class__._symbol_

