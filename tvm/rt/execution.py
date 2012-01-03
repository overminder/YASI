from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.jit import hint, unroll_safe
from tvm.rt.code import codemap, argwidth
from tvm.rt.interp import Frame, LeaveFrame
from tvm.rt.jit import jitdriver

unrolled_dispatchers = unrolling_iterable([(i, getattr(Frame, name))
        for (name, i) in codemap.iteritems()])

class __extend__(Frame):
    @unroll_safe
    def dispatch(self, code):
        opcode = self.nextbyte(code)
        if argwidth(opcode) == 2:
            oparg = self.nextshort(code)
        elif argwidth(opcode) == 1:
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
        #self = hint(self, access_directly=True)
        try:
            while True:
                jitdriver.jit_merge_point(pc=self.pc, w_func=self.w_func,
                                          frame=self)
                self.dispatch(self.w_func.code)
        except LeaveFrame as leave:
            return leave.w_retval

