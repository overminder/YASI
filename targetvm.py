import sys
from tvm import config
from tvm.error import OperationError
from tvm.lang.reader import read_string
from tvm.rt.prelude import populate_module
from tvm.rt.execution import execute_function
from tvm.lang.env import ModuleDict
from tvm.lang.model import list_to_pair
from tvm.asm.assembler import load_bytecode_function

def load_file(filename):
    from pypy.rlib.streamio import open_file_as_stream
    stream = open_file_as_stream(filename, 'r')
    content = stream.readall()
    stream.close()
    return read_string(content)

def make_module():
    w_global = ModuleDict()
    populate_module(w_global)
    return w_global

def run_bytecode(w_expr, w_global):
    w_func = load_bytecode_function(w_expr, w_global)
    execute_function(w_func, [])

def run_source(w_expr, w_global):
    from tvm.bootstrap.stage2 import compile_expr
    w_func = compile_expr(w_expr, w_global)
    execute_function(w_func, [])

def main(argv):
    config.default.open_file_handle()
    try:
        filename = argv[1]
    except (IndexError, ValueError):
        print 'usage: %s [file-name]' % argv[0]
        return 1
    try:
        if argv[2] == '--stacksize':
            stacksize = int(argv[3])
            assert stacksize >= 0
            config.default.vm_stacksize = stacksize
    except (IndexError, ValueError):
        pass
    #
    w_global = make_module()
    exprlist_w = load_file(filename)
    if len(exprlist_w) == 1:
        if exprlist_w[0].car_w().to_string() == 'BYTECODE-FUNCTION':
            run_bytecode(exprlist_w[0], w_global)
        else:
            run_source(list_to_pair(exprlist_w), w_global)
    else:
        run_source(list_to_pair(exprlist_w), w_global)
    #
    leave_program()
    return 0

def leave_program():
    config.default.stdout.flush()

def target(config, argl):
    return main, None

def jitpolicy(driver):
    from pypy.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == '__main__':
    main(sys.argv)

