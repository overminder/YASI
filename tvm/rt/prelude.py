from pypy.rlib.jit import hint, unroll_safe
from tvm.rt.native import W_NativeFunction
from tvm.lang.model import W_Root, w_boolean, W_Integer, symbol

prelude_registry = []

def populate_module(module_w):
    for w_key, w_val in prelude_registry:
        module_w.setitem(w_key, w_val)

class W_Lt(W_NativeFunction):
    _symbol_ = '<'
    @unroll_safe
    def call(self, args_w):
        assert len(args_w) == 2
        w_lhs, w_rhs = args_w
        return w_boolean(w_lhs.to_int() < w_rhs.to_int())

class W_Add(W_NativeFunction):
    _symbol_ = '+'
    @unroll_safe
    def call(self, args_w):
        lhs = 0
        for w_arg in args_w:
            lhs += w_arg.to_int()
        return W_Integer(lhs)

class W_Sub(W_NativeFunction):
    _symbol_ = '-'
    @unroll_safe
    def call(self, args_w):
        assert len(args_w) >= 1
        if len(args_w) == 1:
            return W_Integer(-args_w[0].to_int())
        else:
            lhs = args_w[0].to_int()
            for i in xrange(1, len(args_w)):
                w_arg = args_w[i]
                lhs -= w_arg.to_int()
            return W_Integer(lhs)

class W_Exit(W_NativeFunction):
    _symbol_ = 'exit'
    @unroll_safe
    def call(self, args_w):
        raise SystemExit(0)

for val in globals().values():
    if (isinstance(val, type) and issubclass(val, W_NativeFunction) and
            hasattr(val, '_symbol_')):
        prelude_registry.append((symbol(val._symbol_), val()))
del val

