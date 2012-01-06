from pypy.rlib.jit import JitDriver

def nextbyte(pc, w_func):
    ch = w_func.code[pc]
    return ord(ch), pc + 1

def nextshort(pc, w_func):
    byte0, pc = nextbyte(pc, w_func)
    byte1, pc = nextbyte(pc, w_func)
    return ((byte1 << 8) | byte0), pc

def get_location(pc, w_func):
    from tvm.rt.code import codenames, Op, argwidth
    savedpc = pc
    op, pc = nextbyte(pc, w_func)
    width = argwidth(op)
    if width == 2:
        oparg, pc = nextshort(pc, w_func)
    elif width == 1:
        oparg, pc = nextbyte(pc, w_func)
    else:
        oparg = 0
    #
    head = '%d:%s' % (savedpc, codenames[op])
    if savedpc == 0:
        head = ('Enter Function %s:' % w_func.name) + head
    #
    if op in [Op.LOAD, Op.STORE]:
        tail = '(%d) ;; %s' % (oparg, w_func.names_w[oparg].to_string())
    elif op in [Op.LOADGLOBAL, Op.STOREGLOBAL, Op.LOADCONST]:
        tail = '(%d) ;; %s' % (oparg, w_func.consts_w[oparg].to_string())
    elif op in [Op.CALL, Op.TAILCALL]:
        tail = '() ;; argc = %d' % oparg
    elif op == Op.RET:
        tail = '()'
    elif op in [Op.J, Op.JIF, Op.JIFZ]:
        tail = '() ;; to %d' % oparg
    else:
        assert 0
    return head + ' ' + tail

jitdriver = JitDriver(greens=['pc', 'w_func'],
                      reds=['frame'],
                      virtualizables=['frame'],
                      get_printable_location=get_location)

