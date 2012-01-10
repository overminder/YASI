(define rl:lib (open-library-handle "libreadline.so"))
(define rl:readline (build-foreign-function rl:lib "readline"
                                           '(string) 'string))
(define rl:add-history (build-foreign-function rl:lib "add_history"
                                               '(string) 'void))
;; XXX leaking
(set! rl:readline
  (let ([readline rl:readline])
    (lambda prompt
      (if (null? prompt)
          (set! prompt ">>> ")
          (set! prompt (car prompt)))
      (let ([line (readline prompt)])
        (rl:add-history line)
        line))))

