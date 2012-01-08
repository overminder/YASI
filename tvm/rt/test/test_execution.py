from tvm.rt.code import codemap, Op, W_BytecodeFunction
from tvm.rt.prelude import populate_module
from tvm.rt.execution import execute_function
from tvm.lang.model import W_Integer, symbol, w_true, w_unspec
from tvm.lang.env import ModuleDict

def make_code(*argl):
    return ''.join(chr(bytecode) for bytecode in argl)

def test_add():
    code = make_code(Op.LOADCONST, 0,
                     Op.LOADCONST, 1,
                     Op.LOADGLOBAL, 0,
                     Op.CALL, 2,
                     Op.RET)
    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_add = symbol('+')
    w_global = ModuleDict()
    populate_module(w_global)
    w_func = W_BytecodeFunction(code, 0, 0, '', [w_one, w_two],
                                [w_add], w_global, 'main')
    w_retval = execute_function(w_func, [])
    assert w_retval.to_int() == 3

def test_cond():
    code = make_code(Op.LOADCONST, 0,
                     Op.LOADCONST, 1,
                     Op.LOADGLOBAL, 0,
                     Op.CALL, 2,
                     Op.RET)
    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_lt = symbol('<')
    w_global = ModuleDict()
    populate_module(w_global)
    w_func = W_BytecodeFunction(code, 0, 0, '', [w_one, w_two],
                                [w_lt], w_global, 'main')
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
    w_func = W_BytecodeFunction(code, 2, 2, '', [],
                                [w_lt], w_global, 'lessthan')

    maincode = make_code(Op.LOADCONST, 0,
                         Op.LOADCONST, 1,
                         Op.BUILDCLOSURE, 2,
                         Op.CALL, 2,
                         Op.RET)

    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_main = W_BytecodeFunction(maincode, 0, 0, '', [w_one, w_two, w_func],
                                [], w_global, 'main')

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
    w_func = W_BytecodeFunction(code, 2, 2, '', [],
                                [w_lt], w_global, 'tailcaller')

    maincode = make_code(Op.LOADCONST, 0,
                         Op.LOADCONST, 1,
                         Op.BUILDCLOSURE, 2,
                         Op.CALL, 2,
                         Op.RET)

    w_one = W_Integer(1)
    w_two = W_Integer(2)
    w_main = W_BytecodeFunction(maincode, 0, 0, '', [w_one, w_two, w_func],
                                None, w_global)
    w_retval = execute_function(w_main, [])
    assert w_retval is w_true
 
def test_fibo():
    w_global = ModuleDict()
    populate_module(w_global)
    #
    w_two = W_Integer(2)
    w_lt = symbol('<')
    w_one = W_Integer(1)
    w_sub = symbol('-')
    w_fibo = symbol('fibo')
    w_add = symbol('+')
    consts_w = [w_two, w_one]
    names_w = [w_lt, w_sub, w_fibo, w_add]
    code = make_code(Op.LOAD, 0, # n
                     Op.LOADCONST, 0, # 2
                     Op.LOADGLOBAL, 0, # '<
                     Op.CALL, 2, # push (< n 2)
                     Op.JIFNOT, 14, 0, # to recur_case
                     Op.LOAD, 0, # n
                     Op.RET, # return n
                     # recur_case
                     Op.LOAD, 0, # n
                     Op.LOADCONST, 1, # 1
                     Op.LOADGLOBAL, 1, # '-
                     Op.CALL, 2, # push (- n 1)
                     Op.LOADGLOBAL, 2, # 'fibo
                     Op.CALL, 1, # push (fibo (- n 1))
                     Op.LOAD, 0, # n
                     Op.LOADCONST, 0, # 2
                     Op.LOADGLOBAL, 1, # '-
                     Op.CALL, 2, # push (- n 2)
                     Op.LOADGLOBAL, 2, # 'fibo
                     Op.CALL, 1, # push (fibo (- n 2))
                     Op.LOADGLOBAL, 3, # '+
                     Op.TAILCALL, 2)
    w_func = W_BytecodeFunction(code, 1, 1, '', consts_w, names_w, w_global)

    maincode = make_code(Op.BUILDCLOSURE, 0,
                         Op.STOREGLOBAL, 0,
                         Op.LOADCONST, 1,
                         Op.LOADGLOBAL, 0,
                         Op.CALL, 1,
                         Op.RET)

    w_ten = W_Integer(10)
    w_main = W_BytecodeFunction(maincode, 0, 0, '', [w_func, w_ten],
                                [w_fibo], w_global)

    w_retval = execute_function(w_main, [])
    assert w_retval.to_int() == 55
 
def test_immutable_upval():
    w_global = ModuleDict()
    populate_module(w_global)
    #
    inner_code = make_code(Op.LOADUPVAL, 0, # n
                           Op.RET)
    w_inner_func = W_BytecodeFunction(inner_code, 0, 1, '\0', [], [], None)

    outer_code = make_code(Op.BUILDUPVAL, 0,
                           Op.LOADCONST, 0,
                           Op.STOREUPVAL, 0,
                           Op.BUILDCLOSURE, 1,
                           Op.RET)
    w_one = W_Integer(1)
    w_outer_func = W_BytecodeFunction(outer_code, 0, 1, '',
                                      [w_one, w_inner_func], [], None)

    main_code = make_code(Op.BUILDCLOSURE, 0,
                          Op.CALL, 0, # outer() => inner
                          Op.CALL, 0, # inner() => 1
                          Op.RET)
    w_main = W_BytecodeFunction(main_code, 0, 0, '', [w_outer_func], [], None)
    #
    w_retval = execute_function(w_main, [])
    assert w_retval.to_int() == 1

def test_mutable_upval():
    w_global = ModuleDict()
    populate_module(w_global)
    w_one = W_Integer(1)
    w_two = W_Integer(2)
    #
    inner_code = make_code(Op.LOADUPVAL, 0, # n
                           Op.LOADCONST, 0, # 2
                           Op.LOADGLOBAL, 0, # '+
                           Op.CALL, 2,
                           Op.STOREUPVAL, 0, # n
                           Op.LOADCONST, 1, # void
                           Op.RET)
    w_inner_func = W_BytecodeFunction(inner_code, 0, 1, '\0',
                                      [w_two, w_unspec],
                                      [symbol('+')], w_global)

    outer_code = make_code(Op.BUILDUPVAL, 0,
                           Op.LOADCONST, 0, # 1
                           Op.STOREUPVAL, 0,
                           Op.BUILDCLOSURE, 1, # inner
                           Op.CALL, 0, # inner(), which changes the upval to 3
                           Op.POP,
                           Op.LOADUPVAL, 0,
                           Op.RET)
    w_outer_func = W_BytecodeFunction(outer_code, 0, 1, '',
                                      [w_one, w_inner_func], [], None)

    main_code = make_code(Op.BUILDCLOSURE, 0,
                          Op.CALL, 0, # outer() => 3
                          Op.RET)
    w_main = W_BytecodeFunction(main_code, 0, 0, '', [w_outer_func], [], None)
    #
    w_retval = execute_function(w_main, [])
    assert w_retval.to_int() == 3

