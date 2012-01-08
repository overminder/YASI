from pypy.rlib.jit import hint, unroll_safe
from tvm.rt.baseframe import Frame, W_ExecutionError
from tvm.rt.code import codemap, W_BytecodeFunction
from tvm.rt.native import W_NativeFunction
from tvm.lang.model import W_Root, W_Error

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

    pc = 0
    stacktop = 0
    stackbase = 0
    w_func = None
    dump = None

    # stacksize will impose an constant factor on speed.
    def __init__(self, stacksize=32):
        self = hint(self, access_directly=True,
                          fresh_virtualizable=True)
        self.stack_w = [None] * stacksize

    def enter(self, w_func):
        self.stackbase = w_func.nb_locals
        self.stacktop = self.stackbase
        self.w_func = w_func
        self.pc = 0

    @unroll_safe
    def enter_with_args(self, w_func, args_w):
        oldtop = self.stacktop
        self.enter(w_func)
        nb_args = len(args_w)
        i = 0
        # set arguments
        while i < nb_args:
            self.stack_w[i] = args_w[i]
            i += 1
        # and delete garbage
        while i < oldtop:
            self.stack_w[i] = None
            i += 1

    def leave_with_retval(self, w_retval):
        if self.dump:
            self.dump.restore(self)
            self.push(w_retval)
        else:
            raise ReturnFromTopLevel(w_retval)

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

    def LOAD(self, oparg):
        w_val = self.stackref(oparg)
        if w_val is None:
            raise W_ExecutionError('unbound local variable', 'LOAD()').wrap()
        self.push(w_val)

    def STORE(self, oparg):
        self.stackset(oparg, self.pop())

    def LOADGLOBAL(self, oparg):
        w_key = self.w_func.consts_w[oparg]
        w_val = self.w_func.module_w.getitem(w_key)
        if w_val is None:
            raise W_ExecutionError('unbound global variable %s' %
                                   w_key.to_string(), 'LOADGLOBAL()').wrap()
        self.push(w_val)

    def STOREGLOBAL(self, oparg):
        w_key = self.w_func.consts_w[oparg]
        w_val = self.pop()
        self.w_func.module_w.setitem(w_key, w_val)

    def LOADCONST(self, oparg):
        self.push(self.w_func.consts_w[oparg])

    @unroll_safe
    def CALL(self, oparg):
        from tvm.rt.execution import execute_function
        w_func = self.pop()
        args_w = self.popmany(oparg)
        if isinstance(w_func, W_BytecodeFunction):
            nb_args = w_func.nb_args
            if oparg != nb_args:
                raise W_ExecutionError('argcount').wrap()
            self.dump = Dump(self)
            self.enter_with_args(w_func, args_w)
        else:
            assert isinstance(w_func, W_NativeFunction)
            w_retval = w_func.call(args_w)
            self.push(w_retval)

    @unroll_safe
    def TAILCALL(self, oparg):
        w_func = self.pop()
        args_w = self.popmany(oparg)
        if isinstance(w_func, W_BytecodeFunction):
            nb_args = w_func.nb_args
            if oparg != nb_args:
                raise W_ExecutionError('argcount').wrap()
            self.enter_with_args(w_func, args_w)
        else:
            assert isinstance(w_func, W_NativeFunction)
            w_retval = w_func.call(args_w)
            self.leave_with_retval(w_retval)

    def RET(self, oparg):
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

