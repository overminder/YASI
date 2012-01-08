from tvm.asm.assembler import dump_bytecode_function

def make_code(argl):
    return ''.join([chr(bytecode) for bytecode in argl])

def main():
    from tvm.rt.code import codemap, Op, W_BytecodeFunction
    from tvm.rt.prelude import populate_module
    from tvm.rt.execution import execute_function
    from tvm.lang.model import W_Integer, symbol, w_true
    from tvm.lang.env import ModuleDict
    #
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
    code = make_code([Op.LOAD, 0, # n
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
                      Op.TAILCALL, 2])
    w_func = W_BytecodeFunction(code, 1, 1, '', consts_w, names_w, w_global,
                                name='fibo')

    maincode = make_code([Op.BUILDCLOSURE, 0,
                          Op.STOREGLOBAL, 0,
                          Op.LOADCONST, 1,
                          Op.LOADGLOBAL, 0,
                          Op.CALL, 1,
                          Op.RET])

    w_arg = W_Integer(30)
    w_main = W_BytecodeFunction(maincode, 0, 0, '', [w_func, w_arg],
                                [w_fibo], w_global, name='main')
    print dump_bytecode_function(w_main).to_string()

if __name__ == '__main__':
    main()

