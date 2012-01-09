from pypy.rlib.jit import unroll_safe, dont_look_inside
from tvm.lang.model import symbol, list_to_pair, W_Integer, w_boolean
from tvm.rt.code import W_BytecodeFunction

@dont_look_inside
def load_bytecode_function(w_expr, w_module):
    fields_w, w_rest = w_expr.to_list()
    assert w_rest.is_null()
    assert len(fields_w) == 9
    assert fields_w[0].to_string() == 'BYTECODE-FUNCTION'
    #
    (w_tag, w_funcname), _ = fields_w[1].to_list()
    assert w_tag.to_string() == 'NAME'
    funcname = w_funcname.to_string()
    #
    (w_tag, w_code), _ = fields_w[2].to_list()
    assert w_tag.to_string() == 'CODE'
    codelist_w, _ = w_code.to_list()
    code = ''.join([chr(c.to_int()) for c in codelist_w])
    #
    (w_tag, w_nb_args, w_has_vararg), _ = fields_w[3].to_list()
    assert w_tag.to_string() == 'NB-ARGS'
    nb_args = w_nb_args.to_int()
    assert nb_args >= 0
    has_vararg = w_has_vararg.to_bool()
    #
    (w_tag, w_nb_locals), _ = fields_w[4].to_list()
    assert w_tag.to_string() == 'NB-LOCALS'
    nb_locals = w_nb_locals.to_int()
    assert nb_locals >= 0
    #
    (w_tag, w_upval_descrs), _ = fields_w[5].to_list()
    assert w_tag.to_string() == 'UPVAL-DESCRS'
    descrlist_w, _ = w_upval_descrs.to_list()
    descr_chars = []
    for w_descr in descrlist_w:
        (w_from, w_to), _ = w_descr.to_list()
        descr_chars.append(chr(w_from.to_int()))
        descr_chars.append(chr(w_to.to_int()))
    upval_descrs = ''.join(descr_chars)
    #
    (w_tag, w_consts), _ = fields_w[6].to_list()
    assert w_tag.to_string() == 'CONSTS'
    consts_w, _ = w_consts.to_list()
    #
    (w_tag, w_names), _ = fields_w[7].to_list()
    assert w_tag.to_string() == 'NAMES'
    names_w, _ = w_names.to_list()
    #
    (w_tag, w_functions), _ = fields_w[8].to_list()
    assert w_tag.to_string() == 'FUNCTIONS'
    func_literals_w, _ = w_functions.to_list()
    functions_w = [load_bytecode_function(w_literal, w_module)
                   for w_literal in func_literals_w]
    return W_BytecodeFunction(code, nb_args, has_vararg, nb_locals,
                              upval_descrs, consts_w[:], names_w[:],
                              functions_w[:], w_module, funcname)

@dont_look_inside
def dump_bytecode_function(w_func):
    assert isinstance(w_func, W_BytecodeFunction)
    fields_w = [None] * 9
    fields_w[0] = symbol('BYTECODE-FUNCTION')
    fields_w[1] = list_to_pair([symbol('NAME'), symbol(w_func.name)])
    w_code = list_to_pair([W_Integer(ord(c)) for c in w_func.code])
    fields_w[2] = list_to_pair([symbol('CODE'), w_code])
    fields_w[3] = list_to_pair([symbol('NB-ARGS'), W_Integer(w_func.nb_args),
                                w_boolean(w_func.has_vararg)])
    fields_w[4] = list_to_pair([symbol('NB-LOCALS'),
                                W_Integer(w_func.nb_locals)])
    upval_descrs_w = []
    i = 0
    while i < len(w_func.upval_descrs):
        c0, c1 = w_func.upval_descrs[i], w_func.upval_descrs[i + 1]
        i += 2
        upval_descrs_w.append(list_to_pair([W_Integer(ord(c0)),
                                            W_Integer(ord(c1))]))
    w_upval_descrs = list_to_pair(upval_descrs_w[:])
    fields_w[5] = list_to_pair([symbol('UPVAL-DESCRS'), w_upval_descrs])
    w_consts = list_to_pair(w_func.consts_w)
    fields_w[6] = list_to_pair([symbol('CONSTS'), w_consts])
    w_names = list_to_pair(w_func.names_w)
    fields_w[7] = list_to_pair([symbol('NAMES'), w_names])
    w_functions = list_to_pair([dump_bytecode_function(w_function)
                                for w_function in w_func.functions_w])
    fields_w[8] = list_to_pair([symbol('FUNCTIONS'), w_functions])
    return list_to_pair(fields_w)

