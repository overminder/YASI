import sys
from pypy.rlib.jit import dont_look_inside
from pypy.rlib.parsing.makepackrat import (PackratParser, Status,
                                           BacktrackException)
from tvm.lang.model import (W_Root, W_Integer, W_Pair, w_nil, w_true, w_false,
                            symbol, w_unspec)

@dont_look_inside
def read_string(source):
    exprs_w = SchemeParser(source).program()
    assert isinstance(exprs_w[0], W_Root) # XXX pypy hack
    return exprs_w

def w_tag(s, w_x):
    return W_Pair(symbol(s), W_Pair(w_x, w_nil))

class SchemeParser(PackratParser):
    r'''
    IGNORE:
        SPACE | COMMENT;

    SPACE:
        `[ \t\n\r]`;

    COMMENT:
        `;[^\n]*`;

    INTEGER:
        `[+-]?[0-9]+`;

    TRUE:
        '#t';

    FALSE:
        '#f';

    IDENT:
        `[0-9a-zA-Z_!?@#$%&*+-/<>=\.]+`;

    EOF:
        !__any__;

    program:
        c = sexpr*
        IGNORE*
        EOF
        return {c};

    sexpr:
        IGNORE*
        c = TRUE
        return {w_true}
      | IGNORE*
        c = FALSE
        return {w_false}
      | IGNORE*
        c = INTEGER
        return {W_Integer(int(c or 'ERR'))}
      | IGNORE*
        `'`
        c = sexpr
        return {w_tag('quote', c)}
      | IGNORE*
        c = IDENT
        return {symbol(c)}
      | IGNORE*
        '('
        c = pair
        IGNORE*
        ')'
        return {c};

    pair:
        car = sexpr
        cdr = pair
        return {W_Pair(car, cdr)}
      | car = sexpr
        IGNORE*
        '.'
        cdr = sexpr
        return {W_Pair(car, cdr)}
      | return {w_nil};
    '''
    noinit = True

