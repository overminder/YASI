(import (ice-9 pretty-print))

(define *debug* #f)

(define _ #f)
(define *unspec* (set! _ #f)) ;; hack to make #<unspecified>

(define (assert condition msg)
  (if (not condition)
      (error msg)))

(define (all lst)
  (if (null? lst) #t
      (and (car lst)
           (all (cdr lst)))))

(define (flatten lst)
  (if (null? lst) lst
      (append (car lst) (flatten (cdr lst)))))

(define (concat-map proc args)
  (let ([map-result (map proc args)])
    (flatten map-result)))

(define *bytecode-descr*
  (let ([descr-file (open-input-file "bytecode-descr.ss")])
    (let ([content (read descr-file)])
      (close-input-port descr-file)
      content)))

(define (codesize code)
  (let ([size-descr (caddr (assoc (car code) *bytecode-descr*))])
    (cond
      ([eq? size-descr 'void]
        1)
      ([eq? size-descr 'u8]
        2)
      ([eq? size-descr 'u16]
        3))))

(define assemble
  (if *debug*
      (lambda (x) `(,x))
      (lambda (code)
        (let ([op (cadr (assoc (car code) *bytecode-descr*))]
              [oparg (cdr code)]
              [size (codesize code)])
          (cond
            ([= size 1]
             `(,op))
            ([= size 2]
             `(,op ,(car oparg)))
            ([= size 3]
             `(,op ,(logand (car oparg) 255)
                   ,(logand (ash -8 (car oparg)) 255))))))))

;; entry point
(define (compile-program program)
  (define main-function (make-function 'main ;; function-name
                                       '() ;; formal-args
                                       #f)) ;; outer
  (compile-function program main-function)
  (main-function 'format-output))

(define (compile-function body function)
  (for-each (lambda (expr)
              (compile-expr-in expr function))
            body)
  (function 'emit 'RET)
  (function 'resolve-deferred-lambda))

(define (compile-expr-in expr function)
  (cond
    ([pair? expr]
     (compile-pair-in expr function))
    ([symbol? expr]
     (compile-var-in expr function))
    ([or (integer? expr)
         (boolean? expr)
         (string? expr)
         (eq? expr *unspec*)]
     (compile-const-in expr function))
    (else
     (error `(cannot compile expr: ,expr)))))

(define (compile-pair-in pair function)
  (let ([tag (car pair)]
        [args (cdr pair)])
    (cond
      ([eq? tag 'quote]
       (compile-const-in (car args) function))
      ([eq? tag 'define]
       (compile-define-in args function))
      ([eq? tag 'set!]
       (compile-set!-in args function))
      ([eq? tag 'lambda]
       (compile-lambda-in args function))
      ([eq? tag 'begin]
       (if (null? args)
           (compile-const-in *unspec* function)
           (begin
             (for-each (lambda (expr)
                         (compile-expr-in expr function)
                         (function 'emit 'POP))
                       args)
             (function 'remove-last-code)))) ;; remove last POP
      ([eq? tag 'if]
       (compile-if-in args function))
      (else
       (compile-application-in tag args function)))))

(define (compile-var-in name function)
  (let ([type (function 'type-of-var name)])
    (cond
      ([eq? type 'local]
       (function 'emit 'LOAD (function 'get-local name)))
      ([eq? type 'global]
       (function 'emit 'LOADGLOBAL (function 'get-name name)))
      ([eq? type 'upval]
       (function 'emit 'LOADUPVAL (function 'get-upval name)))
      (else
       (error 'not-reached)))))

(define (compile-const-in const function)
  (let ([index (function 'intern-const const)])
    (function 'emit 'LOADCONST index)))

(define (compile-define-in args function)
  (let ([first (car args)]
        [rest (cdr args)])
    (cond
      ([symbol? first] ;; defining an variable
       (let ([local-index (function 'define-var first)])
         (compile-expr-in (car rest) function)
         (function 'emit 'STORE local-index)))
      ([pair? first] ;; defining an lambda
       (let ([name (car first)]
             [formal-args (cdr first)])
         (assert (and (list? formal-args)
                      (all (map symbol? formal-args)))
                 'wrong-formal-args)
         (let ([context (function 'context)])
           (let ([func-index (context 'add-deferred-lambda
                                      name formal-args rest)]
                 [local-index (function 'define-var name)])
             (function 'emit 'BUILDCLOSURE func-index)
             (function 'emit 'STORE local-index)))))
      (else
       (error 'syntax-error)))))

(define (compile-set!-in set-expr function)
  (let ([name (car set-expr)]
        [form (cadr set-expr)])
    (compile-expr-in form function)
    (let ([type (function 'type-of-var name)])
      (cond
        ([eq? type 'local]
         (function 'emit 'STORE (function 'get-local name)))
        ([eq? type 'global]
         (function 'emit 'STOREGLOBAL (function 'get-name name)))
        ([eq? type 'upval]
         (function 'emit 'STOREUPVAL (function 'get-upval name)))
        (else
         (error 'not-reached))))))

(define (compile-lambda-in lambda-expr function)
  (let ([formal-args (car lambda-expr)]
        [body (cdr lambda-expr)]
        [context (function 'context)])
    (function 'emit 'BUILDCLOSURE
              (context 'add-deferred-lambda #f formal-args body))))

(define (compile-if-in if-expr function)
  (let ([pred (car if-expr)]
        [then (cadr if-expr)]
        [otherwise (if (= (length if-expr) 3)
                       (caddr if-expr)
                       *unspec*)])
    (compile-expr-in pred function)
    (function 'emit 'JIFNOT -1)
    (let ([insn-jifnot (function 'last-code-ref)]
          [insn-j #f]
          [after-then #f]
          [after-else #f])
      (compile-expr-in then function)
      (function 'emit 'J -1)
      (set! insn-j (function 'last-code-ref))
      (set! after-then (function 'current-pc))
      (set-car! (cdr insn-jifnot) after-then) ;; patch after-pred -> else
      (compile-expr-in otherwise function)
      (set! after-else (function 'current-pc))
      (set-car! (cdr insn-j) after-else)))) ;; patch after-then -> end

(define (compile-application-in proc args function)
  (for-each (lambda (expr)
              (compile-expr-in expr function))
            args)
  (compile-expr-in proc function)
  (function 'emit 'CALL (length args)))

;; Context and Function

(define (make-function *name* *formal-args* *outer*)
  (define *raw-code* '())
  (define *consts* '())
  (define *names* '()) ;; (name, name-index)
  (define *locals* '()) ;; (name, local-index)
  (define *upvals* '()) ;; (name, upval-rel-index)
  (define *current-pc* 0)
  (define *deferred-lambda* '())

  (define (type-of-var name)
    (cond
      ([assoc name *locals*]
       'local)
      ([assoc name *upvals*]
       'upval)
      (*outer*
       (let ([outer-type (*outer* 'type-of-var name)])
         (cond
           ([eq? outer-type 'local]
            (add-to-upval-descr name (*outer* 'promote-to-upval name))
             'upval)
           ([eq? outer-type 'upval]
            (add-to-upval-descr name (*outer* 'get-upval name)))
           (else
            (assert (eq? outer-type 'global) 'wtf)
            outer-type))))
      (else
       'global))) ;; or if I am the toplevel

  (define (add-to-upval-descr name outer-index)
    (set! *upvals* (cons `(,name ,outer-index) *upvals*)))

  (define (promote-to-upval name)
    (let ([local-index (cadr (assoc *locals* name))])
      (patch-local-access local-index)
      local-index))

  (define (patch-local-access local-index)
    (define (patch code)
      (if (null? code) #f
          (let ([thiscode (car code)]
                [rest (cdr code)])
            (cond
              ([eq? (caar thiscode) 'LOAD]
               (set-car! code `(LOADUPVAL ,(cadr thiscode))))
              ([eq? (caar thiscode) 'STORE]
               (set-car! code `(STOREUPVAL ,(cadr thiscode)))))
            (patch rest))))
    (patch *raw-code*))

  (define (get-local name)
    (cadr (assoc name *locals*)))

  (define (get-upval name)
    (cadr (assoc name *upvals*)))

  (define (get-name name)
    (let ([maybe-name (assoc name *names*)])
      (if maybe-name (cadr maybe-name)
          (let ([new-index (length *names*)])
            (set! *names* (cons `(,name ,new-index) *names*))
            new-index))))

  (define (define-var name)
    (if (assoc name *locals*)
        (get-local name) ;; duplicate define
        (let ([local-index (length *locals*)])
          (set! *locals* (cons `(,name ,local-index) *locals*))
          local-index)))

  (define (intern-const value)
    (let ([maybe-interned (assoc value *consts*)])
      (if maybe-interned
          (cadr maybe-interned)
          (let ([next-const (length *consts*)])
            (set! *consts* (cons `(,value ,next-const) *consts*))
            next-const))))

  (define (emit . args)
    (set! *current-pc* (+ *current-pc* (codesize args)))
    (set! *raw-code* (cons args *raw-code*)))

  (define (remove-last-code)
    (let ([last-code (car *raw-code*)])
      (set! *current-pc* (- *current-pc* (codesize last-code)))
      (set! *raw-code* (cdr *raw-code*))))

  (define (last-code-ref)
    (car *raw-code*))

  (define (resolve-deferred-lambda)
    #f)

  (define (format-output)
    `(BYTECODE-FUNCTION
       (NAME ,*name*)
       (CODE ,(concat-map assemble (reverse *raw-code*)))
       (NB-ARGS ,(length *formal-args*))
       (NB-LOCALS ,(+ (length *locals*) (length *upvals*)))
       (UPVAL-DESCRS ,*upvals*)
       (CONSTS ,(reverse (map car *consts*)))
       (NAMES ,(reverse (map car *names*)))
       (FUNCTIONS ())))

  (define methods
    `((type-of-var ,type-of-var)
      (emit ,emit)
      (intern-const ,intern-const)
      (get-local ,get-local)
      (get-name ,get-name)
      (get-upval ,get-upval)
      (define-var ,define-var)

      (last-code-ref ,last-code-ref)
      (remove-last-code ,remove-last-code)

      (resolve-deferred-lambda ,resolve-deferred-lambda)
      (format-output ,format-output)
      ))

  ;; self
  (lambda (attr . args)
    (cond
      ([eq? attr 'name]
        *name*)
      ([eq? attr 'outer]
        *outer*)
      ([eq? attr 'current-pc]
        *current-pc*)
      ([assoc attr methods]
        (apply (cadr (assoc attr methods)) args))
      (else
       (error `(attribute-error: ,attr ,args))))))

(define (read-program)
  (let ([got (read)])
    (if (eof-object? got) '()
        (cons got (read-program)))))

(define (main)
  (let ([program (read-program)])
    (pretty-print (compile-program program))))

(main)

