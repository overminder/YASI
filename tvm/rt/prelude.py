from pypy.rlib.jit import hint, unroll_safe
from tvm.rt.native import W_NativeClosure
from tvm.lang.reader import read_string
from tvm.lang.model import (W_Pair, W_Root, w_boolean, W_Integer,
                            W_Boolean, W_Symbol, symbol,
                            W_Unspecified, w_unspec, W_String,
                            W_File, gensym)

prelude_registry = []

def populate_module(module_w):
    for w_key, w_val in prelude_registry:
        module_w.setitem(w_key, w_val)

class W_NumEq(W_NativeClosure):
    _symbol_ = '='

    @unroll_safe
    def call(self, args_w):
        if len(args_w) <= 1:
            return w_boolean(True)
        w_lhs = args_w[0]
        for i in xrange(1, len(args_w)):
            w_rhs = args_w[i]
            if w_lhs.to_int() == w_rhs.to_int():
                w_lhs = w_rhs
            else:
                return w_boolean(False)
        return w_boolean(True)

class W_Lt(W_NativeClosure):
    _symbol_ = '<'

    @unroll_safe
    def call(self, args_w):
        if len(args_w) <= 1:
            return w_boolean(True)
        w_lhs = args_w[0]
        for i in xrange(1, len(args_w)):
            w_rhs = args_w[i]
            if w_lhs.to_int() < w_rhs.to_int():
                w_lhs = w_rhs
            else:
                return w_boolean(False)
        return w_boolean(True)

class W_Gt(W_NativeClosure):
    _symbol_ = '>'

    @unroll_safe
    def call(self, args_w):
        if len(args_w) <= 1:
            return w_boolean(True)
        w_lhs = args_w[0]
        for i in xrange(1, len(args_w)):
            w_rhs = args_w[i]
            if w_lhs.to_int() > w_rhs.to_int():
                w_lhs = w_rhs
            else:
                return w_boolean(False)
        return w_boolean(True)

class W_Add(W_NativeClosure):
    _symbol_ = '+'

    @unroll_safe
    def call(self, args_w):
        lhs = 0
        for w_arg in args_w:
            lhs += w_arg.to_int()
        return W_Integer(lhs)

class W_Sub(W_NativeClosure):
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

class W_Display(W_NativeClosure):
    _symbol_ = 'display'

    def call(self, args_w):
        from pypy.rlib.streamio import fdopen_as_stream
        assert len(args_w) == 1
        w_arg, = args_w
        stdin = fdopen_as_stream(0, 'r')
        stdin.write(w_arg.to_string())
        return w_unspec

class W_Newline(W_NativeClosure):
    _symbol_ = 'newline'

    def call(self, args_w):
        from pypy.rlib.streamio import fdopen_as_stream
        assert len(args_w) == 0
        stdin = fdopen_as_stream(0, 'r')
        stdin.write('\n')
        return w_unspec

class W_Eqp(W_NativeClosure):
    _symbol_ = 'eq?'

    def call(self, args_w):
        assert len(args_w) == 2
        w_lhs, w_rhs, = args_w
        return w_lhs.is_w(w_rhs)

class W_Integerp(W_NativeClosure):
    _symbol_ = 'integer?'

    def call(self, args_w):
        assert len(args_w) == 1
        w_arg, = args_w
        return w_boolean(isinstance(w_arg, W_Integer))

class W_Symbolp(W_NativeClosure):
    _symbol_ = 'symbol?'

    def call(self, args_w):
        assert len(args_w) == 1
        w_arg, = args_w
        return w_boolean(isinstance(w_arg, W_Symbol))

class W_Stringp(W_NativeClosure):
    _symbol_ = 'string?'

    def call(self, args_w):
        assert len(args_w) == 1
        w_arg, = args_w
        return w_boolean(isinstance(w_arg, W_String))

class W_Pairp(W_NativeClosure):
    _symbol_ = 'pair?'

    def call(self, args_w):
        assert len(args_w) == 1
        w_arg, = args_w
        return w_boolean(isinstance(w_arg, W_Pair))

class W_Nullp(W_NativeClosure):
    _symbol_ = 'null?'

    def call(self, args_w):
        assert len(args_w) == 1
        w_arg, = args_w
        return w_boolean(w_arg.is_null())

class W_Booleanp(W_NativeClosure):
    _symbol_ = 'boolean?'

    def call(self, args_w):
        assert len(args_w) == 1
        w_arg, = args_w
        return w_boolean(isinstance(w_arg, W_Boolean))

class W_Car(W_NativeClosure):
    _symbol_ = 'car'

    def call(self, args_w):
        assert len(args_w) == 1
        w_pair, = args_w
        return w_pair.car_w()

class W_Cdr(W_NativeClosure):
    _symbol_ = 'cdr'

    def call(self, args_w):
        assert len(args_w) == 1
        w_pair, = args_w
        return w_pair.cdr_w()

class W_Cons(W_NativeClosure):
    _symbol_ = 'cons'

    def call(self, args_w):
        assert len(args_w) == 2
        w_car, w_cdr = args_w
        return W_Pair(w_car, w_cdr)

class W_SetCar(W_NativeClosure):
    _symbol_ = 'set-car!'

    def call(self, args_w):
        assert len(args_w) == 2
        w_pair, w_car = args_w
        w_pair.set_car(w_car)
        return w_unspec

class W_SetCdr(W_NativeClosure):
    _symbol_ = 'set-cdr!'

    def call(self, args_w):
        assert len(args_w) == 2
        w_pair, w_cdr = args_w
        w_pair.set_cdr(w_cdr)
        return w_unspec

class W_Exit(W_NativeClosure):
    _symbol_ = 'exit'

    def call(self, args_w):
        raise SystemExit(0)

class W_OpenInputFile(W_NativeClosure):
    _symbol_ = 'open-input-file'

    def call(self, args_w):
        from pypy.rlib.streamio import open_file_as_stream
        assert len(args_w) == 1
        w_name, = args_w
        assert isinstance(w_name, W_String)
        return W_File(open_file_as_stream(w_name.content(), 'r'))

class W_Read(W_NativeClosure):
    _symbol_ = 'read'

    def call(self, args_w):
        from pypy.rlib.streamio import fdopen_as_stream
        if len(args_w) == 0: # from stdin XXX use current-input-port
            stdin = fdopen_as_stream(0, 'r')
            content = stdin.readall()
            return read_string(content)[0]
        else:
            assert len(args_w) == 1 # from given file
            w_file, = args_w
            assert isinstance(w_file, W_File)
            return read_string(w_file.w_readall().content())[0]

class W_CloseInputPort(W_NativeClosure):
    _symbol_ = 'close-input-port'

    def call(self, args_w):
        assert len(args_w) == 1
        w_file, = args_w
        assert isinstance(w_file, W_File)
        w_file.close()
        return w_unspec

class W_StringToSymbol(W_NativeClosure):
    _symbol_ = 'string->symbol'

    def call(self, args_w):
        assert len(args_w) == 1
        w_str, = args_w
        assert isinstance(w_str, W_String)
        return symbol(w_str.content())

class W_SymbolToString(W_NativeClosure):
    _symbol_ = 'symbol->string'

    def call(self, args_w):
        assert len(args_w) == 1
        w_sym, = args_w
        assert isinstance(w_sym, W_Symbol)
        return W_String(w_sym.sval)

class W_Gensym(W_NativeClosure):
    _symbol_ = 'gensym'

    def call(self, args_w):
        assert len(args_w) == 0
        return gensym()

# some custom functions

class W_OpenLibraryHandle(W_NativeClosure):
    _symbol_ = 'open-library-handle'

    def call(self, args_w):
        from tvm.rt.ffi import W_CDLL
        assert len(args_w) == 1
        w_arg, = args_w
        assert isinstance(w_arg, W_String)
        return W_CDLL(w_arg.content())

class W_BuildForeignFunction(W_NativeClosure):
    _symbol_ = 'build-foreign-function'

    @unroll_safe
    def call(self, args_w):
        from tvm.rt.ffi import W_CDLL
        assert len(args_w) == 4
        w_cdll, w_symbol_name, w_argtypenames, w_restypename = args_w
        assert isinstance(w_cdll, W_CDLL)
        assert isinstance(w_symbol_name, W_String)
        argtypenames_w, _ = w_argtypenames.to_list()
        argtypes_w = [name2type[typename.to_string()]
                      for typename in argtypenames_w]
        w_restype = name2type[w_restypename.to_string()]
        return w_cdll.getpointer(w_symbol_name.content(),
                                 argtypes_w, w_restype)

class W_LoadBytecodeFunction(W_NativeClosure):
    _symbol_ = 'load-bytecode-function'

    def call(self, args_w):
        from tvm.asm.assembler import load_bytecode_function
        assert len(args_w) == 1
        w_arg, = args_w
        w_func = load_bytecode_function(w_arg, None) # XXX
        return w_func.build_closure([])

class W_DumpBytecodeFunction(W_NativeClosure):
    _symbol_ = 'dump-bytecode-function'

    def call(self, args_w):
        from tvm.asm.assembler import dump_bytecode_function
        from tvm.rt.code import W_BytecodeClosure
        #
        assert len(args_w) == 1
        w_arg, = args_w
        assert isinstance(w_arg, W_BytecodeClosure)
        assert not w_arg.upvals_w
        return dump_bytecode_function(w_arg.w_func)

name2type = {
    'symbol': W_Symbol,
    'string': W_String,
    'integer': W_Integer,
    'void': W_Unspecified,
    'boolean': W_Boolean,
}

for val in globals().values():
    if (isinstance(val, type) and issubclass(val, W_NativeClosure) and
            hasattr(val, '_symbol_')):
        prelude_registry.append((symbol(val._symbol_), val()))
del val

