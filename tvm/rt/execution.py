from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.jit import hint, unroll_safe, dont_look_inside
from pypy.rlib.objectmodel import we_are_translated
from tvm.rt.code import codemap, argwidth
from tvm.rt.interp import Frame, ReturnFromTopLevel
from tvm.rt.jit import jitdriver

unrolled_dispatchers = unrolling_iterable([(i, getattr(Frame, name))
        for (name, i) in codemap.iteritems()])

def execute_function(w_func, args_w):
    frame = Frame()
    frame.enter_with_args(w_func, args_w) # plain function has no upvals
    if not we_are_translated():
        try:
            return frame.execute()
        except AssertionError as e:
            print '### AssertionError at %s' % frame.w_func.to_string()
            print '### Reason: %s' % e
            print '### Frame: %r' % frame
            raise
    else:
        return frame.execute()

class __extend__(Frame):
    @unroll_safe
    def dispatch(self, code):
        # bytecode dispatch is folded into noop.
        opcode = self.nextbyte(code)
        width = argwidth(opcode)
        if width == 2:
            oparg = self.nextshort(code)
        elif width == 1:
            oparg = self.nextbyte(code)
        else:
            oparg = 0
        assert oparg >= 0
        #
        for someop, somedispatcher in unrolled_dispatchers:
            if someop == opcode:
                somedispatcher(self, oparg)
                break

    @unroll_safe
    def execute(self):
        self = hint(self, access_directly=True)
        try:
            while True:
                jitdriver.jit_merge_point(pc=self.pc, w_func=self.w_func,
                                          frame=self)
                self.dispatch(self.w_func.code)
        except ReturnFromTopLevel as ret:
            return ret.w_retval

    def jump_to(self, dest):
        self.pc = dest

