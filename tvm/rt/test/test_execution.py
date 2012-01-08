from tvm.rt.code import codemap, Op, W_BytecodeFunction
from tvm.rt.prelude import populate_module
from tvm.rt.execution import execute_function
from tvm.lang.model import W_Integer, symbol, w_true
from tvm.lang.env import ModuleDict

def make_code(*argl):
    return ''.join(chr(bytecode) for bytecode in argl)

def test_add():
    code = make_code(Op.LOADCONST, 0,
                     Op.LOADCONST, 1,
                     Op.LOADGLOBAL, 2,
                     Op.CALL, 2,
                     Op.RET)
    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_add = symbol('+')
    w_global = ModuleDict()
    populate_module(w_global)
    w_func = W_BytecodeFunction(code, 0, 0, 3, [w_one, w_two, w_add],
                                None, w_global)
    w_retval = execute_function(w_func, [])
    assert w_retval.to_int() == 3

def test_cond():
    code = make_code(Op.LOADCONST, 0,
                     Op.LOADCONST, 1,
                     Op.LOADGLOBAL, 2,
                     Op.CALL, 2,
                     Op.RET)
    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_lt = symbol('<')
    w_global = ModuleDict()
    populate_module(w_global)
    w_func = W_BytecodeFunction(code, 0, 0, 3, [w_one, w_two, w_lt],
                                None, w_global)
    w_retval = execute_function(w_func, [])
    assert w_retval is w_true
 
def test_call():
    w_global = ModuleDict()
    populate_module(w_global)
    #
    code = make_code(Op.LOAD, 0,
                     Op.LOAD, 1,
                     Op.LOADGLOBAL, 0,
                     Op.CALL, 2,
                     Op.RET)
    w_lt = symbol('<')
    w_func = W_BytecodeFunction(code, 2, 2, 5, [w_lt], None, w_global)

    maincode = make_code(Op.LOADCONST, 0,
                         Op.LOADCONST, 1,
                         Op.LOADCONST, 2,
                         Op.CALL, 2,
                         Op.RET)

    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_main = W_BytecodeFunction(maincode, 0, 0, 3, [w_one, w_two, w_func],
                                None, w_global)

    w_retval = execute_function(w_main, [])
    assert w_retval is w_true
 
def test_tailcall1():
    w_global = ModuleDict()
    populate_module(w_global)
    #
    code = make_code(Op.LOAD, 0,
                     Op.LOAD, 1,
                     Op.LOADGLOBAL, 0,
                     Op.TAILCALL, 2)
    w_lt = symbol('<')
    w_func = W_BytecodeFunction(code, 2, 2, 5, [w_lt], None, w_global)

    maincode = make_code(Op.LOADCONST, 0,
                         Op.LOADCONST, 1,
                         Op.LOADCONST, 2,
                         Op.CALL, 2,
                         Op.RET)

    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_main = W_BytecodeFunction(maincode, 0, 0, 3, [w_one, w_two, w_func],
                                None, w_global)
    w_retval = execute_function(w_main, [])
    assert w_retval is w_true
 
def test_fibo():
    w_global = ModuleDict()
    populate_module(w_global)
    #
    w_two = W_Integer(2)    # k[0]
    w_lt = symbol('<')      # k[1]
    w_one = W_Integer(1)    # k[2]
    w_sub = symbol('-')     # k[3]
    w_fibo = symbol('fibo') # k[4]
    w_add = symbol('+')     # k[5]
    consts_w = [w_two, w_lt, w_one, w_sub, w_fibo, w_add]
    code = make_code(Op.LOAD, 0, # n
                     Op.LOADCONST, 0, # 2
                     Op.LOADGLOBAL, 1, # '<
                     Op.CALL, 2, # push (< n 2)
                     Op.JIFNOT, 14, 0, # to recur_case
                     Op.LOAD, 0, # n
                     Op.RET, # return n
                     # recur_case
                     Op.LOAD, 0, # n
                     Op.LOADCONST, 2, # 1
                     Op.LOADGLOBAL, 3, # '-
                     Op.CALL, 2, # push (- n 1)
                     Op.LOADGLOBAL, 4, # 'fibo
                     Op.CALL, 1, # push (fibo (- n 1))
                     Op.LOAD, 0, # n
                     Op.LOADCONST, 0, # 2
                     Op.LOADGLOBAL, 3, # '-
                     Op.CALL, 2, # push (- n 2)
                     Op.LOADGLOBAL, 4, # 'fibo
                     Op.CALL, 1, # push (fibo (- n 2))
                     Op.LOADGLOBAL, 5, # '+
                     Op.TAILCALL, 2)
    w_func = W_BytecodeFunction(code, 1, 1, 5, consts_w, None, w_global)
    w_global.setitem(w_fibo, w_func)

    maincode = make_code(Op.LOADCONST, 0,
                         Op.LOADCONST, 1,
                         Op.CALL, 1,
                         Op.RET)

    w_ten = W_Integer(10)
    w_main = W_BytecodeFunction(maincode, 0, 0, 2, [w_ten, w_func],
                                None, w_global)

    w_retval = execute_function(w_main, [])
    assert w_retval.to_int() == 55
 
