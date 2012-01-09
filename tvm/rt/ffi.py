from pypy.rlib.jit import hint, unroll_safe, elidable
from pypy.rlib.libffi import CDLL, ArgChain, types
from pypy.rpython.lltypesystem import rffi, lltype
from tvm.rt.native import W_NativeClosure
from tvm.lang.model import (W_Root, w_boolean, W_Integer, symbol, W_Symbol,
                            w_unspec, W_Unspecified, W_Boolean, W_String)

@elidable
def wtype_to_ffitype(w_type):
    for w_sometype, w_ffitype in [(W_Integer, types.slong),
                                  (W_Boolean, types.sint),
                                  (W_Symbol, types.pointer),
                                  (W_String, types.pointer),
                                  (W_Unspecified, types.slong)]:
        if w_type is w_sometype:
            return w_ffitype
    assert 0

class W_CDLL(W_Root):
    def __init__(self, libpath):
        self.libpath = libpath
        self.handle = CDLL(libpath)

    @unroll_safe # XXX necessary?
    def getpointer(self, name, argtypes_w, w_restype):
        argtypes = [wtype_to_ffitype(w_type) for w_type in argtypes_w]
        restype = wtype_to_ffitype(w_restype)
        funcptr = self.handle.getpointer(name, argtypes, restype)
        return W_ForeignClosure(funcptr, name, argtypes_w, w_restype)

    def to_string(self):
        return '#<library-handle %s>' % self.libpath

class W_ForeignClosure(W_NativeClosure):
    _immutable_ = True
    _immutable_fields_ = ['argtypes_w[*]']

    def __init__(self, funcptr, name, argtypes_w, w_restype):
        self.funcptr = funcptr
        self.name = name
        self.argtypes_w = argtypes_w
        self.w_restype = w_restype

    def to_string(self):
        return '#<foreign-closure %s>' % self.name

    @unroll_safe
    def call(self, args_w):
        assert len(args_w) == len(self.argtypes_w)
        argchain = ArgChain()
        buffers = []
        for i in xrange(len(args_w)):
            w_arg = args_w[i]
            assert isinstance(w_arg, self.argtypes_w[i])
            if isinstance(w_arg, W_Integer):
                argchain.arg(w_arg.ival)
            elif isinstance(w_arg, W_Symbol):
                sval = w_arg.sval
                assert sval is not None
                charp = rffi.str2charp(sval)
                buffers.append(charp)
                argchain.arg(charp)
            elif isinstance(w_arg, W_String):
                sval = w_arg.content()
                assert sval is not None
                charp = rffi.str2charp(sval)
                buffers.append(charp)
                argchain.arg(charp)
            elif isinstance(w_arg, W_Boolean):
                argchain.arg(w_arg.to_bool())
            else:
                assert 0, 'unsupported argument type'
        res = self.funcptr.call(argchain, rffi.LONG) # annotate type to LONG
        for charp in buffers:
            rffi.free_charp(charp)
        #
        if self.w_restype is W_Integer:
            w_retval = W_Integer(rffi.cast(rffi.LONG, res))
        elif self.w_restype is W_Boolean:
            w_retval = w_boolean(rffi.cast(rffi.LONG, res))
        elif self.w_restype is W_Symbol:
            # XXX who delete the returned pointer?
            w_retval = symbol(rffi.charp2str(rffi.cast(rffi.CCHARP, res)))
        elif self.w_restype is W_String:
            w_retval = W_String(rffi.charp2str(rffi.cast(rffi.CCHARP, res)))
        elif self.w_restype is W_Unspecified:
            w_retval = w_unspec
        else:
            assert 0, 'unsupported result type'
        return w_retval

