from pypy.rlib.jit import dont_look_inside
from tvm.lang.model import symbol, list_to_pair, W_Integer
from tvm.rt.code import W_BytecodeFunction

@dont_look_inside
def load_bytecode_function(w_expr, w_module):
    fields_w, w_rest = w_expr.to_list()
    assert w_rest.is_null()
    assert len(fields_w) == 8
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
    (w_tag, w_nb_args), _ = fields_w[3].to_list()
    assert w_tag.to_string() == 'NB-ARGS'
    nb_args = w_nb_args.to_int()
    assert nb_args >= 0
    #
    (w_tag, w_nb_locals), _ = fields_w[4].to_list()
    assert w_tag.to_string() == 'NB-LOCALS'
    nb_locals = w_nb_locals.to_int()
    assert nb_locals >= 0
    #
    (w_tag, w_upval_descrs), _ = fields_w[5].to_list()
    assert w_tag.to_string() == 'UPVAL-DESCRS'
    descrlist_w, _ = w_upval_descrs.to_list()
    upval_descrs = ''.join([chr(c.to_int()) for c in descrlist_w])
    #
    (w_tag, w_consts), _ = fields_w[6].to_list()
    assert w_tag.to_string() == 'CONSTS'
    constlist_w, _ = w_consts.to_list()
    consts_w = [None] * len(constlist_w)
    for i in xrange(len(constlist_w)):
        w_literal = constlist_w[i]
        w_tag = w_literal.car_w()
        if w_tag.to_string() == 'LITERAL':
            consts_w[i] = w_literal.cdr_w().car_w()
        else:
            assert w_tag.to_string() == 'BYTECODE-FUNCTION'
            consts_w[i] = load_bytecode_function(w_literal, w_module)
    #
    (w_tag, w_names), _ = fields_w[7].to_list()
    assert w_tag.to_string() == 'NAMES'
    names_w, _ = w_names.to_list()
    return W_BytecodeFunction(code, nb_args, nb_locals, upval_descrs,
                              consts_w, names_w[:], w_module, funcname)

@dont_look_inside
def dump_bytecode_function(w_func):
    assert isinstance(w_func, W_BytecodeFunction)
    fields_w = [None] * 8
    fields_w[0] = symbol('BYTECODE-FUNCTION')
    fields_w[1] = list_to_pair([symbol('NAME'), symbol(w_func.name)])
    w_code = list_to_pair([W_Integer(ord(c)) for c in w_func.code])
    fields_w[2] = list_to_pair([symbol('CODE'), w_code])
    fields_w[3] = list_to_pair([symbol('NB-ARGS'), W_Integer(w_func.nb_args)])
    fields_w[4] = list_to_pair([symbol('NB-LOCALS'),
                                W_Integer(w_func.nb_locals)])
    w_upval_descrs = list_to_pair([W_Integer(ord(c))
                                   for c in w_func.upval_descrs])
    fields_w[5] = list_to_pair([symbol('UPVAL-DESCRS'), w_upval_descrs])
    w_consts = list_to_pair([dump_bytecode_function(w_const)
                             if isinstance(w_const, W_BytecodeFunction)
                             else list_to_pair([symbol('LITERAL'), w_const])
                             for w_const in w_func.consts_w])
    fields_w[6] = list_to_pair([symbol('CONSTS'), w_consts])
    w_names = list_to_pair(w_func.names_w)
    fields_w[7] = list_to_pair([symbol('NAMES'), w_names])
    return list_to_pair(fields_w)

