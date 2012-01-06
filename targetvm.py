import sys

def make_code(argl):
    return ''.join([chr(bytecode) for bytecode in argl])

def test_loop(n):
    from tvm.error import OperationError
    from tvm.rt.code import codemap, Op, W_BytecodeFunction
    from tvm.rt.prelude import populate_module
    from tvm.rt.execution import execute_function
    from tvm.lang.model import W_Integer, symbol, w_true
    from tvm.lang.env import ModuleDict
    #
    w_global = ModuleDict()
    populate_module(w_global)
    #
    w_one = W_Integer(1)    # k[0]
    w_lt = symbol('<')      # k[1]
    w_sub = symbol('-')     # k[2]
    w_loop = symbol('loop') # k[3]
    w_add = symbol('+')     # k[4]
    consts_w = [w_one, w_lt, w_sub, w_loop, w_add]
    code = make_code([Op.LOAD, 0, # n
                      Op.LOADCONST, 0, # 1
                      Op.LOADGLOBAL, 1, # '<
                      Op.CALL, 2, # push (< n 1)
                      Op.JIFZ, 14, 0, # to recur_case
                      Op.LOAD, 1, # s
                      Op.RET, # return s
                      # recur_case
                      Op.LOAD, 0, # n
                      Op.LOADCONST, 0, # 1
                      Op.LOADGLOBAL, 2, # '-
                      Op.CALL, 2, # push (- n 1)
                      Op.STORE, 0, # write (- n 1) back to n
                      Op.LOAD, 0, # (- n 1)
                      Op.LOAD, 1, # s
                      Op.LOADGLOBAL, 4, # '+
                      Op.CALL, 2, # push (+ s (- n 1))
                      Op.STORE, 1, # write back to s
                      Op.LOAD, 0,
                      Op.LOAD, 1,
                      Op.LOADGLOBAL, 3, # 'loop
                      Op.TAILCALL, 2,
                     ])
    names_w = [symbol('n'), symbol('s')]
    w_func = W_BytecodeFunction(code, 2, 2, 5, consts_w, names_w, w_global)
    w_func.name = 'loop'
    w_global.setitem(w_loop, w_func)

    maincode = make_code([Op.LOADCONST, 0,
                          Op.LOADCONST, 1,
                          Op.LOADCONST, 2,
                          Op.CALL, 2,
                          Op.RET])

    w_inputarg = W_Integer(n)
    w_zero = W_Integer(0)
    w_main = W_BytecodeFunction(maincode, 0, 0, 3, [w_inputarg, w_zero, w_func],
                                [], w_global)
    w_main.name = 'main'

    try:
        w_retval = execute_function(w_main, [])
        print w_retval.to_string()
    except OperationError as e:
        print e.unwrap().to_string()

def test_fibo(n):
    from tvm.rt.code import codemap, Op, W_BytecodeFunction
    from tvm.rt.prelude import populate_module
    from tvm.rt.execution import execute_function
    from tvm.lang.model import W_Integer, symbol, w_true
    from tvm.lang.env import ModuleDict
    #
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
    code = make_code([Op.LOAD, 0, # n
                      Op.LOADCONST, 0, # 2
                      Op.LOADGLOBAL, 1, # '<
                      Op.CALL, 2, # push (< n 2)
                      Op.JIFZ, 14, 0, # to recur_case
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
                      Op.TAILCALL, 2])
    names_w = [symbol('n')]
    w_func = W_BytecodeFunction(code, 1, 1, 5, consts_w, names_w, w_global)
    w_func.name = 'fibo'
    w_global.setitem(w_fibo, w_func)

    maincode = make_code([Op.LOADCONST, 0,
                          Op.LOADCONST, 1,
                          Op.CALL, 1,
                          Op.RET])

    w_ten = W_Integer(n)
    w_main = W_BytecodeFunction(maincode, 0, 0, 2, [w_ten, w_func],
                                [], w_global)
    w_main.name = 'main'

    w_retval = execute_function(w_main, [])
    print w_retval.to_string()

def main(argv):
    try:
        n = int(argv[1])
    except (IndexError, ValueError):
        n = 30
    test_fibo(n)
    return 0

def target(config, argl):
    return main, None

def jitpolicy(driver):
    from pypy.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == '__main__':
    main(sys.argv)

