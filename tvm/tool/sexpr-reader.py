#!/usr/bin/env python

import path_fix
import sys
from tvm.lang.reader import read_string

with open(sys.argv[1]) as f:
    sexpr_list = read_string(f.read())
    print '\n'.join(sexpr.to_string() for sexpr in sexpr_list)
