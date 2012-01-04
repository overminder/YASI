from pypy.tool.pairtype import extendabletype
from pypy.rlib.jit import unroll_safe
from tvm.error import OperationError
from tvm.lang.model import W_Root, W_Error

class W_ExecutionError(W_Error):
    def __init__(self, msg, where='?'):
        self.msg = msg
        self.where = where

    def to_string(self):
        return '<ExecutionError: %s at %s>' % (self.msg, self.where)

class Frame(object):
    __metaclass__ = extendabletype
    
    @unroll_safe
    def dropmany(self, n):
        i = self.stacktop - n
        assert i >= self.stackbase, 'stack underflow'
        while i < self.stacktop:
            self.stack_w[i] = None
            i += 1
        self.stacktop -= n

    def pop(self):
        t = self.stacktop - 1
        assert t >= self.stackbase, 'stack underflow'
        self.stacktop = t
        w_pop = self.stack_w[t]
        self.stack_w[t] = None
        return w_pop

    @unroll_safe
    def popmany(self, n):
        lst = [None] * n
        i = n - 1
        while i >= 0:
            lst[i] = self.pop()
            i -= 1
        return lst

    def push(self, w_push):
        t = self.stacktop
        assert t >= self.stackbase, 'stack underflow'
        self.stack_w[t] = w_push
        self.stacktop = t + 1

    @unroll_safe
    def pushmany(self, items_w):
        for w_item in items_w:
            self.push(w_item)

    def settop(self, w_top):
        t = self.stacktop - 1
        assert t >= self.stackbase, 'stack underflow'
        self.stack_w[t] = w_top

    def peek(self):
        t = self.stacktop - 1
        assert t >= self.stackbase, 'stack underflow'
        w_top = self.stack_w[t]
        return w_top

    def stackref(self, index):
        assert index >= 0
        w_ref = self.stack_w[index]
        return w_ref

    def stackset(self, index, w_val):
        assert w_val is not None
        assert index >= 0
        self.stack_w[index] = w_val

    def stackclear(self, index):
        assert index >= 0
        self.stack_w[index] = None

