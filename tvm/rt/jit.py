from pypy.rlib.jit import JitDriver

def get_location(pc, w_func):
    return '?'

jitdriver = JitDriver(greens=['pc', 'w_func'],
                      reds=['frame'],)
                      #virtualizables=['frame'],
                      #get_printable_location=get_location)

