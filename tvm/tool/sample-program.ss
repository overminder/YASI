;(define libc (open-library-handle "libc.so.6"))
;(define printf (build-foreign-function libc "printf"
;                                       '(string string) 'integer))
;(define puts (build-foreign-function libc "puts"
;                                     '(string) 'void))
;(printf "hello, %s" "world")
;(puts "")
;
;(define file (open-input-file "compiled-bytecode.ss"))
;(define content (read file))
;(close-input-port file)

(define (fibo n)
  (if (< n 2) n
      ;(+ (fibo (- n 1))
      (+ (apply fibo (cons (- n 1) '()))
         (fibo (- n 2)))))

(display (fibo 30))
(newline)

