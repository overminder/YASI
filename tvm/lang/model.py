from pypy.rlib.jit import unroll_safe
from pypy.tool.pairtype import extendabletype
from tvm.error import OperationError

class W_Root(object):
    __metaclass__ = extendabletype

    def to_string(self):
        return '#<object>'

    def __repr__(self):
        return self.to_string()

    def to_int(self):
        raise W_TypeError('Int', self, 'to_int()').wrap()

    def to_bool(self):
        return True

    def make_to_list():
        def to_list(self):
            items_w = []
            while isinstance(self, W_Pair):
                items_w.append(self.w_car)
                self = self.w_cdr
            return items_w, self
        return to_list

    to_list = make_to_list()
    to_list_unrolled = unroll_safe(make_to_list()) # used by primitive-apply
    del make_to_list

    def is_null(self):
        return self is w_nil

    # Pointer identity
    def is_w(self, w_x):
        if self is w_x:
            return w_true
        return w_false

    # Generic value equality.
    def equal_w(self, w_x):
        return self.is_w(w_x)

    def car_w(self):
        raise W_TypeError('Pair', self, 'car_w()').wrap()

    def cdr_w(self):
        raise W_TypeError('Pair', self, 'cdr_w()').wrap()

    def set_car(self, w_car):
        raise W_TypeError('Pair', self,
                          'set_car(%s)' % w_car.to_string()).wrap()

    def set_cdr(self, w_cdr):
        raise W_TypeError('Pair', self,
                          'set_cdr(%s)' % w_cdr.to_string()).wrap()


class W_Pair(W_Root):
    def __init__(self, w_car, w_cdr):
        self.w_car = w_car
        self.w_cdr = w_cdr

    def to_string(self):
        items_w, w_rest = self.to_list()
        head = '(' + ' '.join([w_x.to_string() for w_x in items_w])
        if w_rest.is_null():
            return head + ')'
        else:
            return head + ' . ' + w_rest.to_string() + ')'

    # Recursively compare equality
    def equal_w(self, w_x):
        if isinstance(w_x, W_Pair):
            return (self.w_car.equal_w(w_x.w_car) and
                    self.w_cdr.equal_w(w_x.w_cdr))
        return w_false

    def car_w(self):
        return self.w_car

    def cdr_w(self):
        return self.w_cdr

    def set_car(self, w_car):
        self.w_car = w_car

    def set_cdr(self, w_cdr):
        self.w_cdr = w_cdr

class W_Integer(W_Root):
    _immutable_ = True

    def __init__(self, ival):
        self.ival = ival

    def to_string(self):
        return '%d' % self.ival

    def to_int(self):
        return self.ival

    def equal_w(self, w_x):
        if isinstance(w_x, W_Integer):
            if self.ival == w_x.ival:
                return w_true
        return w_false

class W_Symbol(W_Root):
    """ interned string object
    """
    _immutable_ = True

    def __init__(self, sval):
        self.sval = sval

    def to_string(self):
        return self.sval

class InternState(object):
    def __init__(self):
        self.interned_w = {}

    def intern(self, sval):
        w_sym = self.interned_w.get(sval, None)
        if w_sym is None:
            w_sym = W_Symbol(sval)
            self.interned_w[sval] = w_sym
        return w_sym

intern_state = InternState()
symbol = intern_state.intern

class GensymCounter(object):
    i = 0
gensym_counter = GensymCounter()

def gensym(prefix='$Gensym_'):
    i = gensym_counter.i
    s = prefix + str(i)
    while s in intern_state.interned_w:
        i += 1
        s = prefix + str(i)
    gensym_counter.i = i + 1
    return symbol(s)


class W_String(W_Root):
    _immutable_ = True

    def __init__(self, sval):
        assert sval is not None
        self.chars = [c for c in sval]

    def to_string(self):
        return '"' + self.content() + '"'

    def content(self):
        return ''.join(self.chars)

    def equal_w(self, w_x):
        if isinstance(w_x, W_String):
            return w_boolean(w_x.content() == self.content())
        return w_false


class W_File(W_Root):
    def __init__(self, stream):
        self.stream = stream

    def to_string(self):
        return '#<file %s>' % self.stream

    def w_readall(self):
        return W_String(self.stream.readall())

    def close(self):
        self.stream.close()


class W_Nil(W_Root):
    def to_string(self):
        return '()'

w_nil = W_Nil()


class W_Boolean(W_Root):
    def __init__(self, bval):
        self.bval = bval

    def to_string(self):
        if self.bval:
            return '#t'
        else:
            return '#f'

    def to_bool(self):
        return self.bval

w_true = W_Boolean(True)

w_false = W_Boolean(False)

def w_boolean(bval):
    if bval:
        return w_true
    else:
        return w_false

class W_Unspecified(W_Root):
    def to_string(self):
        return '#<unspecified>'

w_unspec = W_Unspecified()

class W_Eof(W_Root):
    def to_string(self):
        return '#<eof>'

w_eof = W_Eof()


def make_list_to_pair():
    def list_to_pair(list_w, w_last=w_nil):
        for i in xrange(len(list_w) - 1, -1, -1):
            w_item = list_w[i]
            w_last = W_Pair(w_item, w_last)
        return w_last
    return list_to_pair

list_to_pair = make_list_to_pair()
list_to_pair_unroll = unroll_safe(make_list_to_pair()) # performance hack


################################################################################
################################################################################

class W_Error(W_Root):
    def to_string(self):
        return '#<error>'

    def wrap(self):
        return OperationError(self)


class W_TypeError(W_Error):
    def __init__(self, expected, w_got, where):
        self.expected = expected
        self.w_got = w_got
        self.where = where

    def to_string(self):
        return '#<TypeError: expecting %s, but got %s at %s.>' % (
                self.expected, self.w_got.to_string(), self.where)


class W_IndexError(W_Error):
    def __init__(self, w_array, index, where):
        self.w_array = w_array
        self.index = index
        self.where = where

    def to_string(self):
        return '#<IndexError: array index out of bound (%d) at %s.>' % (
                self.index, self.where)


class W_ValueError(W_Error):
    def __init__(self, why, w_got, where):
        self.why = why
        self.w_got = w_got
        self.where = where

    def to_string(self):
        return '#<ValueError: %s for %s at %s.>' % (
                self.why, self.w_got.to_string(), self.where)

class W_NameError(W_Error):
    def __init__(self, w_name):
        self.w_name = w_name

    def to_string(self):
        return '#<NameError: name "%s" is not defined.>' % (
                self.w_name.to_string())


