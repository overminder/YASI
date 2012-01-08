from ..model import W_Pair, W_Symbol, W_Integer
from ..reader import read_string

def test_read_string():
    s0 = '(+ 1 2)'
    p0 = read_string(s0)
    assert len(p0) == 1
    w0, = p0
    assert isinstance(w0, W_Pair)
    lst0, rest0 = w0.to_list()
    assert rest0.is_null()
    assert len(lst0) == 3
    item0_0, item0_1, item0_2 = lst0
    assert isinstance(item0_0, W_Symbol)
    assert isinstance(item0_1, W_Integer)
    assert isinstance(item0_2, W_Integer)

