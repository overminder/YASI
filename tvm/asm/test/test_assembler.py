from tvm.asm.assembler import load_bytecode_function, dump_bytecode_function
from tvm.lang.reader import read_string

compiled_source = '''
(BYTECODE-FUNCTION
  (NAME main)
  (CODE (255 254 253 252))
  (NB-ARGS 0)
  (NB-LOCALS 0)
  (UPVAL-DESCRS ())
  (CONSTS ((LITERAL 10)
  (LITERAL (1 2 3))))
  (NAMES (fibo display)))
'''

def test_load_dump():
    w_expr, = read_string(compiled_source)
    w_func0 = load_bytecode_function(w_expr, None)
    w_expr0 = dump_bytecode_function(w_func0)
    assert w_expr.to_string() == w_expr0.to_string()

