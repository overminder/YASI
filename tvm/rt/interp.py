from pypy.rlib.jit import hint, unroll_safe
from tvm import config
from tvm.rt.baseframe import Frame, W_ExecutionError
from tvm.rt.code import codemap, W_BytecodeClosure, W_BytecodeFunction, W_UpVal
from tvm.rt.native import W_NativeClosure, W_NativeClosureX
from tvm.lang.model import W_Root, W_Error, list_to_pair_unroll

class ReturnFromTopLevel(Exception):
    _immutable_ = True
    def __init__(self, w_retval):
        self.w_retval = w_retval

class Dump(object):
    _immutable_ = True
    _immutable_fields_ = ['stack_w[*]']

    @unroll_safe
    def __init__(self, frame):
        self.pc = frame.pc
        self.w_func = frame.w_func
        self.stack_w = [None] * frame.stacktop
        self.dump = frame.dump
        #
        i = 0
        stacktop = frame.stacktop
        while i < stacktop:
            self.stack_w[i] = frame.stack_w[i]
            i += 1

    @unroll_safe
    def restore(self, frame):
        oldtop = frame.stacktop
        frame.pc = self.pc
        frame.w_func = self.w_func
        frame.stackbase = self.w_func.nb_locals
        frame.stacktop = len(self.stack_w)
        frame.dump = self.dump
        # restore virtual stack items
        stacktop = frame.stacktop
        i = 0
        while i < stacktop:
            frame.stack_w[i] = self.stack_w[i]
            i += 1
        # and delete garbage on vstack
        while i < oldtop:
            frame.stack_w[i] = None
            i += 1


class __extend__(Frame):
    _virtualizable2_ = [
        'pc',
        'stacktop',
        'stackbase',
        'w_func',
        'dump',
        'stack_w[*]',
    ]

    _immutable_fields_ = ['stack_w']

    pc = 0
    stacktop = 0
    stackbase = 0
    w_func = None
    dump = None

    # stacksize will impose an constant factor impact on speed.
    def __init__(self):
        self = hint(self, access_directly=True,
                          fresh_virtualizable=True)
        self.stack_w = [None] * config.default.vm_stacksize

    def __repr__(self):
        from pprint import pprint
        from cStringIO import StringIO
        buf = StringIO()
        pprint(self.__dict__, buf)
        return buf.getvalue()

    def enter(self, w_func):
        self.stackbase = w_func.nb_locals
        self.stacktop = self.stackbase
        self.w_func = w_func
        self.pc = 0

    @unroll_safe
    def enter_with_args(self, w_func, args_w, upvals_w=None):
        oldtop = self.stacktop
        self.enter(w_func)
        nb_args = len(args_w)
        nb_locals = w_func.nb_locals
        i = 0
        # set arguments
        while i < nb_args:
            self.stackset(i, args_w[i])
            i += 1
        # and delete prev frame's garbage
        while i < oldtop:
            self.stackclear(i)
            i += 1
        if upvals_w:
            # set upvals, since upvals are interleaved with normal locals,
            # we need to apply some complex transformations...
            i = 0
            upval_descrs = w_func.upval_descrs
            nb_upvals = len(upvals_w)
            while i < nb_upvals:
                to_index = ord(upval_descrs[(i << 1) | 1])
                self.stackset(to_index, upvals_w[i])
                i += 1

    def leave_with_retval(self, w_retval):
        if self.dump:
            self.dump.restore(self)
            self.push(w_retval)
        else:
            raise ReturnFromTopLevel(w_retval)

    @unroll_safe
    def call_closure(self, w_closure, args_w, tailp):
        nb_args_supplied = len(args_w)
        if isinstance(w_closure, W_BytecodeClosure):
            w_func = w_closure.w_func
            nb_args = w_func.nb_args
            if not w_func.has_vararg:
                # fast path.
                if nb_args_supplied != nb_args:
                    raise W_ExecutionError('%s require exactly %d '
                    'argument, but got %s (%s)' %
                    (w_func.name, nb_args, nb_args_supplied,
                     [w_x.to_string() for w_x in args_w]),
                    '%s' % self.w_func.to_string()).wrap()
                if not tailp:
                    self.dump = Dump(self) # save current state
                self.enter_with_args(w_func, args_w, w_closure.upvals_w)
            else:
                if nb_args_supplied < nb_args - 1:
                    raise W_ExecutionError('%s require at least %d '
                    'argument, but got %s (%s)' %
                    (w_func.name, nb_args - 1, nb_args_supplied,
                     [w_x.to_string() for w_x in args_w]),
                    '%s' % self.w_func.to_string()).wrap()
                if not tailp:
                    self.dump = Dump(self)
                slice_start = nb_args - 1
                assert slice_start >= 0
                w_vararg = list_to_pair_unroll(args_w[slice_start:])
                truncated_args_w = args_w[:nb_args]
                truncated_args_w[nb_args - 1] = w_vararg
                self.enter_with_args(w_func, truncated_args_w,
                                     w_closure.upvals_w)
        elif isinstance(w_closure, W_NativeClosure):
            w_retval = w_closure.call(args_w)
            if not tailp:
                self.push(w_retval)
            else:
                self.leave_with_retval(w_retval)
        else:
            assert isinstance(w_closure, W_NativeClosureX)
            w_closure.call_with_frame(args_w, self, tailp=tailp)

    def nextbyte(self, code):
        pc = self.pc
        assert pc >= 0
        ch = code[pc]
        self.pc = pc + 1
        return ord(ch)

    def nextshort(self, code):
        byte0 = self.nextbyte(code)
        byte1 = self.nextbyte(code)
        return (byte1 << 8) | byte0

    # bytecode dispatchers

    def POP(self, _):
        self.pop()

    def LOAD(self, oparg):
        w_val = self.stackref(oparg)
        if w_val is None:
            raise W_ExecutionError('unbound local variable', 'LOAD()').wrap()
        self.push(w_val)

    def STORE(self, oparg):
        self.stackset(oparg, self.pop())

    # turn the local var into an upval inplace.
    def BUILDUPVAL(self, oparg):
        w_val = self.stackref(oparg)
        assert not isinstance(w_val, W_UpVal)
        self.stackset(oparg, W_UpVal(w_val))

    def LOADUPVAL(self, oparg):
        w_val = self.stackref(oparg)
        assert isinstance(w_val, W_UpVal)
        self.push(w_val.w_value)

    def STOREUPVAL(self, oparg):
        w_val = self.stackref(oparg)
        assert isinstance(w_val, W_UpVal)
        w_val.w_value = self.pop()

    def LOADGLOBAL(self, oparg):
        w_key = self.w_func.names_w[oparg]
        w_val = self.w_func.module_w.getitem(w_key)
        if w_val is None:
            raise W_ExecutionError('unbound global variable %s' %
                                   w_key.to_string(), 'LOADGLOBAL()').wrap()
        self.push(w_val)

    def STOREGLOBAL(self, oparg):
        w_key = self.w_func.names_w[oparg]
        w_val = self.pop()
        self.w_func.module_w.setitem(w_key, w_val)

    def LOADCONST(self, oparg):
        self.push(self.w_func.consts_w[oparg])

    @unroll_safe
    def BUILDCLOSURE(self, oparg):
        w_func = self.w_func.functions_w[oparg]
        assert isinstance(w_func, W_BytecodeFunction)
        upval_descrs = w_func.upval_descrs
        nb_upvals = len(upval_descrs) >> 1
        upvals_w = [None] * nb_upvals
        i = 0
        while i < nb_upvals:
            upvals_w[i] = self.stackref(ord(upval_descrs[i << 1]))
            i += 1
        w_closure = w_func.build_closure(upvals_w)
        self.push(w_closure)

    @unroll_safe
    def CALL(self, oparg):
        w_closure = self.pop()
        args_w = self.popmany(oparg)
        self.call_closure(w_closure, args_w, tailp=False)

    @unroll_safe
    def TAILCALL(self, oparg):
        w_closure = self.pop()
        args_w = self.popmany(oparg)
        self.call_closure(w_closure, args_w, tailp=True)

    def RET(self, _):
        self.leave_with_retval(self.pop())

    def J(self, oparg):
        self.jump_to(oparg)

    def JIF(self, oparg):
        w_val = self.pop()
        if w_val.to_bool():
            self.jump_to(oparg)

    def JIFNOT(self, oparg):
        w_val = self.pop()
        if not w_val.to_bool():
            self.jump_to(oparg)

