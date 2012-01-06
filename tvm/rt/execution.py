from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.jit import hint, unroll_safe, dont_look_inside
from tvm.rt.code import codemap, argwidth
from tvm.rt.interp import Frame, LeaveFrame, Trampoline
from tvm.rt.jit import jitdriver

unrolled_dispatchers = unrolling_iterable([(i, getattr(Frame, name))
        for (name, i) in codemap.iteritems()])

# XXX trampolining is not trace-safe!
@unroll_safe
def execute_function(w_func, args_w):
    while True:
        try:
            return Frame(w_func, args_w).execute()
        except Trampoline as tr:
            w_func, args_w = tr.unpack_w()

class __extend__(Frame):
    @unroll_safe
    def dispatch(self, code):
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
                self.stacktop = hint(self.stacktop, promote=True) # ?
                self.dispatch(self.w_func.code)
        except LeaveFrame:
            return self.pop()

    def jump_to(self, dest):
        self.pc = dest

