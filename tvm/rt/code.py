from pypy.rlib.debug import check_nonneg
from pypy.rlib.jit import elidable
from tvm.util import load_descr_file
from tvm.lang.model import W_Root

def load_code_descrs():
    namelist = load_descr_file(__file__, 'code.txt')
    last_u16 = namelist.index('_last_u16_')
    del namelist[last_u16]
    last_u16 -= 1

    last_u8 = namelist.index('_last_u8_')
    del namelist[last_u8]
    last_u8 -= 1
    namemap = dict((name, i) for (i, name) in enumerate(namelist))
    return namelist, namemap, last_u8, last_u16

codenames, codemap, last_u8, last_u16 = load_code_descrs()

class Op(object):
    vars().update(codemap)

# For debug's purpose and for dispatching.
def argwidth(opcode):
    if opcode <= last_u16:
        return 2
    elif opcode <= last_u8:
        return 1
    else:
        return 0

class W_BytecodeClosure(W_Root):
    _immutable_fields_ = ['w_func', 'upvals_w[*]']

    def __init__(self, w_func, upvals_w):
        self.w_func = w_func
        self.upvals_w = upvals_w

    def to_string(self):
        return '#<bytecode-closure %s>' % self.w_func.name


class W_BytecodeFunction(W_Root):
    _immutable_ = True
    _immutable_fields_ = ['consts_w[*]', 'names_w[*]', 'functions_w[*]']

    def __init__(self, code, nb_args, has_vararg, nb_locals, upval_descrs,
                 consts_w, names_w, functions_w, module_w, name='#f'):
        self.code = code
        self.name = name
        #
        check_nonneg(nb_args)
        self.nb_args = nb_args # including the vararg.
        self.has_vararg = has_vararg 
        check_nonneg(nb_locals)
        self.nb_locals = nb_locals # args + locals + upvals
        #
        self.upval_descrs = upval_descrs
        self.consts_w = consts_w
        self.names_w = names_w # a list of local var names
        self.functions_w = functions_w # a list of plain functions
        self.module_w = module_w

    def to_string(self):
        return '#<bytecode-function %s>' % self.name

    def build_closure(self, upvals_w):
        return W_BytecodeClosure(self, upvals_w)


class W_UpVal(W_Root):
    def __init__(self, w_value):
        self.w_value = w_value

    def to_string(self):
        return '#<upval (%s)>' % self.w_value.to_string()

