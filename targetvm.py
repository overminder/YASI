import sys
from tvm.lang.reader import read_string
from tvm.rt.prelude import populate_module
from tvm.rt.execution import execute_function
from tvm.lang.env import ModuleDict
from tvm.asm.assembler import load_bytecode_function

def run_compiled_code(filename):
    from pypy.rlib.streamio import open_file_as_stream
    #
    w_global = ModuleDict()
    populate_module(w_global)
    #
    stream = open_file_as_stream(filename, 'r')
    content = stream.readall()
    stream.close()
    w_expr, = read_string(content)
    w_func = load_bytecode_function(w_expr, w_global)
    #
    w_retval = execute_function(w_func, [])
    print w_retval.to_string()

def main(argv):
    try:
        filename = argv[1]
    except (IndexError, ValueError):
        print 'usage: %s [bytecode-file-name]' % argv[0]
        return 1
    run_compiled_code(filename)
    return 0

def target(config, argl):
    return main, None

def jitpolicy(driver):
    from pypy.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == '__main__':
    main(sys.argv)

