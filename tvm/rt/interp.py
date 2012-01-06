from pypy.rlib.jit import hint, unroll_safe
from tvm.rt.baseframe import Frame, W_ExecutionError
from tvm.rt.code import codemap, W_BytecodeFunction
from tvm.rt.native import W_NativeFunction
from tvm.lang.model import W_Root, W_Error

class Trampoline(Exception):
    def __init__(self, w_func, args_w):
        self.w_func = w_func
        self.args_w = args_w

    def unpack_w(self):
        return self.w_func, self.args_w

class LeaveFrame(Exception):
    pass

class __extend__(Frame):
    _virtualizable2_ = [
        'pc',
        'stacktop',
        'stackbase',
        'w_func',
        'stack_w[*]',
    ]

    _immutable_fields_ = [
        'stackbase',
        'w_func',
    ]

    @unroll_safe
    def __init__(self, w_func, args_w):
        self = hint(self, access_directly=True,
                          fresh_virtualizable=True)
        self.stack_w = [None] * w_func.stacksize
        self.stackbase = w_func.nb_locals
        self.stacktop = self.stackbase
        self.w_func = w_func
        self.pc = 0
        for i in xrange(len(args_w)):
            w_arg = args_w[i]
            self.stack_w[i] = w_arg

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
            #w_retval = Frame(w_func, args_w).execute()
            w_retval = execute_function(w_func, args_w)
        else:
            assert isinstance(w_func, W_NativeFunction)
            w_retval = w_func.call(args_w)
        #
        self.push(w_retval)

    @unroll_safe
    def TAILCALL(self, oparg):
        w_func = self.pop()
        args_w = self.popmany(oparg)
        if isinstance(w_func, W_BytecodeFunction):
            nb_args = w_func.nb_args
            if oparg != nb_args:
                raise W_ExecutionError('argcount').wrap()
            raise Trampoline(w_func, args_w)
        else:
            assert isinstance(w_func, W_NativeFunction)
            w_retval = w_func.call(args_w)
            self.push(w_retval)
            raise LeaveFrame

    def RET(self, oparg):
        raise LeaveFrame

    def J(self, oparg):
        self.jump_to(oparg)

    def JIF(self, oparg):
        w_val = self.pop()
        if w_val.to_bool():
            self.jump_to(oparg)

    def JIFZ(self, oparg):
        w_val = self.pop()
        if not w_val.to_bool():
            self.jump_to(oparg)

