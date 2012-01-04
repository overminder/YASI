import sys

def make_code(argl):
    return ''.join([chr(bytecode) for bytecode in argl])

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
                      Op.CALL, 2,
                      Op.RET])
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
    #frame = Frame(w_main, [])

    #w_retval = frame.execute()
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

