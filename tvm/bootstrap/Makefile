SRC = stage2.ss bootstrap-compiler.ss
LIB = stdlib.ss source-preprocessor.ss
SCM = guile

all : stage2-compiled.ss check

check : stage2-compiled.ss
	../../targetvm-c stage2-compiled.ss

stage2-compiled.ss : $(SRC) $(LIB)
	$(SCM) bootstrap-compiler.ss < stage2.ss > stage2-compiled.ss

