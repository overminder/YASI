from pypy.rlib.debug import check_nonneg
from tvm.util import load_descr_file
from tvm.lang.model import W_Root

def load_code_descr():
    namelist = load_descr_file(__file__, 'code.txt')
    last_u16 = namelist.index('_last_u16_')
    del namelist[last_u16]
    last_u16 -= 1

    last_u8 = namelist.index('_last_u8_')
    del namelist[last_u8]
    last_u8 -= 1
    namemap = dict((name, i) for (i, name) in enumerate(namelist))
    return namelist, namemap, last_u8, last_u16

codenames, codemap, last_u8, last_u16 = load_code_descr()

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

class W_BytecodeFunction(W_Root):
    _immutable_ = True
    name = '#f'

    def __init__(self, code, nb_args, nb_locals, stacksize,
                 const_w, module_w=None):
        self.code = code
        #
        check_nonneg(nb_args)
        self.nb_args = nb_args
        check_nonneg(nb_locals)
        self.nb_locals = nb_locals
        check_nonneg(stacksize)
        self.stacksize = stacksize
        #
        self.const_w = const_w
        self.module_w = module_w

    def to_string(self):
        return '#<bytecode-function %s>' % self.name


