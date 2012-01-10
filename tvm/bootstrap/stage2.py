from tvm.asm.assembler import load_bytecode_function
from tvm.lang.reader import read_string
from tvm.lang.model import symbol
from tvm.util import localpath
from tvm.lang.env import ModuleDict
from tvm.rt.prelude import populate_module
from tvm.rt.execution import execute_function

with open(localpath(__file__, 'stage2-compiled-lib.ss')) as f:
    content = f.read()

w_lib_expr = read_string(content)[0]
lib_module = ModuleDict()
populate_module(lib_module)
w_lib_function = load_bytecode_function(w_lib_expr, lib_module)
execute_function(w_lib_function, [])

w_macro_expander = lib_module.getitem(symbol("expand-builtin-macro")).w_func
w_code_compiler = lib_module.getitem(symbol("compile-program")).w_func

def compile_expr(w_expr, w_module):
    w_expanded = execute_function(w_macro_expander, [w_expr])
    w_compiled = execute_function(w_code_compiler, [w_expanded])
    return load_bytecode_function(w_compiled, w_module)

