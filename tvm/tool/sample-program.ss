(define libc (open-library-handle "libc.so.6"))
(define printf (build-foreign-function libc "printf"
                                       '(string string) 'integer))
(define puts (build-foreign-function libc "puts"
                                     '(string) 'void))
(printf "hello, %s" "world")
(puts "")

(define file (open-input-file "compiled-bytecode.ss"))
(define content (read file))
(close-input-port file)

