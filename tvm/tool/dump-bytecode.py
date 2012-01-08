#!/usr/bin/env python

import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '../../')))

from datetime import datetime
from tvm.rt.code import codenames, argwidth

w = sys.stdout.write
w(';; dumped by dump-bytecode.py at %s\n' % datetime.now())
w(';; format is (opcode-name opcode-value argument-type)\n')
w('(')

for op, name in enumerate(codenames):
    if op != 0:
        w(' ')
    w('(%s %d %s)' % (name, op, ['void', 'u8', 'u16'][argwidth(op)]))
    if op != len(codenames) - 1:
        w('\n')

w(')\n')
#
