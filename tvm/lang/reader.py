import sys
from pypy.rlib.jit import dont_look_inside
from pypy.rlib.parsing.makepackrat import (PackratParser, Status,
                                           BacktrackException)
from tvm.lang.model import (W_Root, W_Integer, W_Pair, w_nil, w_true, w_false,
                            symbol, w_unspec, W_String, w_eof)

@dont_look_inside
def read_string(source):
    exprs_w = SchemeParser(source).program()
    if len(exprs_w) == 0:
        return [w_eof]
    else:
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

    UNSPEC:
        '#<unspecified>';

    IDENT:
        `[0-9a-zA-Z_!?@#$%&*+-/<>=\.:]+`;

    STRING:
        '"'
        s = `[^"]*`
        '"'
        return {s};

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
        c = UNSPEC
        return {w_unspec}
      | IGNORE*
        c = INTEGER
        return {W_Integer(int(c or 'ERR'))}
      | IGNORE*
        c = IDENT
        return {symbol(c)}
      | IGNORE*
        c = STRING
        return {W_String(c)}
      | IGNORE*
        `'`
        c = sexpr
        return {w_tag('quote', c)}
      | IGNORE*
        '`'
        c = sexpr
        return {w_tag('quasiquote', c)}
      | IGNORE*
        ',@'
        c = sexpr
        return {w_tag('unquote-splicing', c)}
      | IGNORE*
        ','
        c = sexpr
        return {w_tag('unquote', c)}
      | IGNORE*
        '('
        c = pair
        IGNORE*
        ')'
        return {c}
      | IGNORE*
        '['
        c = pair
        IGNORE*
        ']'
        return {c};

    pair:
        car = sexpr
        IGNORE+
        '.'
        IGNORE+
        cdr = sexpr
        return {W_Pair(car, cdr)}
      | car = sexpr
        cdr = pair
        return {W_Pair(car, cdr)}
      | return {w_nil};
    '''
    noinit = True

