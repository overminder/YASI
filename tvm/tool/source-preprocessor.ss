(define (read-program . input-file)
  (let ([got (apply read input-file)])
    (if (eof-object? got) '()
        (cons got (apply read-program input-file)))))

(define qq-stack 0)

(define (expand-builtin-macro expr)
  (cond
    ([or (symbol? expr)
         (integer? expr)
         (string? expr)
         (boolean? expr)]
     expr)
    ([pair? expr]
     (let ([tag (car expr)]
           [rest (cdr expr)])
       (cond
         ([eq? tag 'let]
          ;; let => lambda
          (expand-let rest))
         ([eq? tag 'cond]
          ;; cond => if*
          (expand-cond rest))
         ([eq? tag 'and]
          ;; and => if*
          (expand-and rest))
         ([eq? tag 'or]
          ;; or => if*
          (expand-or rest))
         ([eq? tag 'require]
          ;; require a file
          (expand-require rest))
         ([eq? tag 'define]
          (let ([var-name (car rest)]
                [var-form (cdr rest)])
            (cons* tag var-name (expand-builtin-macro var-form))))
         ([eq? tag 'lambda]
          (let ([formals (car rest)]
                [body (cdr rest)])
            (cons* tag formals (expand-builtin-macro body))))
         ([eq? tag 'quote]
           expr) ;; nothing to do
         (else
          (map expand-builtin-macro expr)))))
    (else
     (error `(unknown form to expand: ,expr)))))

(define (expand-let form)
  (define (bindings->names lst)
    (map car lst))
  (define (bindings->forms lst)
    (map cadr lst))
  (let ([bindings (car form)]
        [body (cdr form)])
    `((lambda ,(bindings->names bindings)
        ,@(map expand-builtin-macro body))
      ,@(map expand-builtin-macro (bindings->forms bindings)))))

(define (expand-cond form)
  (define (expand form)
    (if (null? form) #f
        (let ([pred (caar form)]
              [body (cdar form)]
              [rest (cdr form)])
          (if (eq? pred 'else)
             `(begin ,@(map expand-builtin-macro body))
             `(if ,(expand-builtin-macro pred)
                   (begin ,@(map expand-builtin-macro body))
                  ,(expand rest))))))
  (expand form))

(define (expand-or form)
  (define tmp-sym (gensym "$Gensym_"))
  (define (expand form)
    (if (null? form) #f
        (let ([hd (expand-builtin-macro (car form))]
              [tl (cdr form)])
          `(begin
             (set! ,tmp-sym ,hd)
             (if ,tmp-sym
                 ,tmp-sym
                 ,(expand tl))))))
  `(begin
     (define ,tmp-sym #f)
    ,(expand form)))

(define (expand-and form)
  (define tmp-sym (gensym "$Gensym_"))
  (define (expand form)
    (if (null? form) #t
        (let ([hd (expand-builtin-macro (car form))]
              [tl (cdr form)])
          `(begin
             (set! ,tmp-sym ,hd)
             (if ,tmp-sym
                 ,(if (null? (cdr tl))
                      (expand-builtin-macro (car tl))
                      (expand tl))
                 #f)))))
  `(begin
     (define ,tmp-sym #f)
    ,(expand form)))

;; circular require?
(define (expand-require form)
  (let ([filename (car form)])
    (define file (open-input-file filename))
    (define prog (read-program file))
    (close-input-port file)
    `(begin ,@(expand-builtin-macro prog))))
