(define *debug* #f)

(define *tail-call-opt* #t)

(if *debug*
    (import (ice-9 pretty-print)))

(define _ #f)
(define *unspec* (set! _ #t)) ;; hack to make #<unspecified>

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

;; (a b . c) -> ((a b) . c) | (a b) -> ((a b) . ())
(define (split-dotted-pair lst)
  (if (pair? lst)
      (let ([hd (car lst)]
            [rest (split-dotted-pair (cdr lst))])
        (cons (cons hd (car rest))
              (cdr rest)))
      (cons '() lst)))

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
                   ,(logand (ash (car oparg) -8) 255))))))))

;; entry point
(define (compile-program program)
  (define main-function (make-function 'main ;; function-name
                                       '(() . ()) ;; formal-args
                                       #f)) ;; outer
  (compile-function program main-function)
  (main-function 'format-output))

(define (compile-function body function)
  (let ([body-len (length body)]
        [tail? (not (function 'is-toplevel?))]) ;; no tailcall at toplevel
    (for-each (lambda (expr)
                (compile-expr-in expr function #f)
                (function 'emit 'POP))
              (list-head body (- body-len 1)))
    (compile-expr-in (list-ref body (- body-len 1)) function tail?))
  (function 'emit 'RET)
  (function 'resolve-deferred-lambda))

(define (compile-expr-in expr function tailp)
  (cond
    ([pair? expr]
     (compile-pair-in expr function tailp))
    ([symbol? expr]
     (compile-var-in expr function))
    ([or (integer? expr)
         (boolean? expr)
         (string? expr)
         (eq? expr *unspec*)]
     (compile-const-in expr function))
    (else
     (error `(cannot compile expr: ,expr)))))

(define (compile-pair-in pair function tailp)
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
       (compile-lambda-in #f args function))
      ([eq? tag 'begin]
       (if (null? args)
           (compile-const-in *unspec* function)
           (begin
             (let ([body-len (length args)])
               (for-each (lambda (expr)
                           (compile-expr-in expr function #f)
                           (function 'emit 'POP))
                         (list-head args (- body-len 1)))
               (compile-expr-in (list-ref args (- body-len 1))
                                function tailp)))))
      ([eq? tag 'if]
       (compile-if-in args function tailp))
      (else
       (compile-application-in tag args function tailp)))))

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
       (error `(not-reached: compile-var-in ,name => ,type))))))

(define (compile-const-in const function)
  (let ([index (function 'intern-const const)])
    (function 'emit 'LOADCONST index)))

(define (compile-define-in define-expr function)
  (let ([first (car define-expr)]
        [rest (cdr define-expr)]
        [var-name #f])
    (cond
      ([symbol? first] ;; defining an variable -- eval the form
       (compile-expr-in (car rest) function #f)
       (set! var-name first))
      ([pair? first] ;; defining an lambda -- build the lambda
       (let ([name (car first)]
             [formal-args (cdr first)])
         (compile-lambda-in name (cons formal-args rest) function)
         (set! var-name name)))
      (else
       (error 'syntax-error)))
    ;; store the value
    (if (function 'is-toplevel?)
      (let ([name-index (function 'get-name var-name)])
        (function 'emit 'STOREGLOBAL name-index))
      (let ([local-index (function 'define-var var-name)])
        (function 'emit 'STORE local-index))))
  (function 'emit 'LOADCONST (function 'intern-const *unspec*)))

(define (compile-set!-in set-expr function)
  (let ([name (car set-expr)]
        [form (cadr set-expr)])
    (compile-expr-in form function #f)
    (let ([type (function 'type-of-var name)])
      (cond
        ([eq? type 'local]
         (function 'emit 'STORE (function 'get-local name)))
        ([eq? type 'global]
         (function 'emit 'STOREGLOBAL (function 'get-name name)))
        ([eq? type 'upval]
         (function 'emit 'STOREUPVAL (function 'get-upval name)))
        (else
         (error '(not-reached: compile-expr-in))))))
  (function 'emit 'LOADCONST (function 'intern-const *unspec*)))

(define (compile-lambda-in name lambda-expr function)
  (let ([arg-descr (split-dotted-pair (car lambda-expr))]
        [body (cdr lambda-expr)])
    (let ([func-index (function 'add-deferred-lambda
                                name
                                arg-descr
                                body)])
      (function 'emit 'BUILDCLOSURE func-index))))

(define (compile-if-in if-expr function tailp)
  (let ([pred (car if-expr)]
        [then (cadr if-expr)]
        [otherwise (if (= (length if-expr) 3)
                       (caddr if-expr)
                       *unspec*)])
    (compile-expr-in pred function #f)
    (function 'emit 'JIFNOT -1)
    (let ([insn-jifnot (function 'last-code-ref)]
          [insn-j #f]
          [after-then #f]
          [after-else #f])
      (compile-expr-in then function tailp)
      (function 'emit 'J -1)
      (set! insn-j (function 'last-code-ref))
      (set! after-then (function 'current-pc))
      (set-car! (cdr insn-jifnot) after-then) ;; patch after-pred -> else
      (compile-expr-in otherwise function tailp)
      (set! after-else (function 'current-pc))
      (set-car! (cdr insn-j) after-else)))) ;; patch after-then -> end

(define (compile-application-in proc args function tailp)
  (for-each (lambda (expr)
              (compile-expr-in expr function #f))
            args)
  (compile-expr-in proc function #f)
  (if (and tailp *tail-call-opt*)
      (function 'emit 'TAILCALL (length args))
      (function 'emit 'CALL (length args))))

;; Context and Function

(define (make-function *name* *formal-args* *outer*)
  (define *pos-args* (car *formal-args*))
  (define *vararg* (cdr *formal-args*))
  (define *has-vararg?* (not (null? *vararg*)))
  (let ([*raw-code* '()]
        [*consts* '()]
        [*names* '()] ;; (name, name-index)
        [*upvals* '()] ;; (name, copy-from-outer-index, upval-index)
        [*promoted-upvals* '()] ;; local-index* for outer function

        ;; (name, local-index), and initialize the arguments
        [*locals* (let ([i -1])
                    (map (lambda (name)
                           (set! i (+ i 1))
                           `(,name ,i))
                         (if *has-vararg?*
                             (append *pos-args* `(,*vararg*))
                             *pos-args*)))]
        [*current-pc* 0]
        [*deferred-lambda* '()]
        [*functions* #f])

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
              ;; fresh upval, outer should promote it
              (add-to-upval-descr name (*outer* 'promote-to-upval name))
               'upval)
             ([eq? outer-type 'upval]
              ;; already upval, just copy
              (add-to-upval-descr name (*outer* 'get-upval name))
               'upval)
             (else
              (assert (eq? outer-type 'global) 'wtf)
              outer-type))))
        (else
         'global))) ;; or if I am the toplevel

    (define (add-to-upval-descr name outer-index)
      (let ([next-local-index (+ (length *locals*) (length *upvals*))])
        (set! *upvals* (cons `(,name ,outer-index ,next-local-index)
                             *upvals*))
        next-local-index))

    (define (promote-to-upval name)
      (let ([local-index (cadr (assoc name *locals*))])
        (if (not (list-index *promoted-upvals* local-index))
            ;; to avoid duplicate upval
            (set! *promoted-upvals* (cons local-index *promoted-upvals*)))
        (patch-local-access local-index)
        local-index))

    (define (get-upval name)
      (caddr (assoc name *upvals*)))

    (define (patch-local-access local-index)
      (for-each (lambda (code)
                  (let ([opname (car code)])
                    (cond
                      ([and (eq? opname 'LOAD)
                            (= (cadr code) local-index)]
                       (set-car! code 'LOADUPVAL))
                      ([and (eq? opname 'STORE)
                            (= (cadr code) local-index)]
                       (set-car! code 'STOREUPVAL)))))
                *raw-code*))

    (define (insert-upval-builder)
      ;; patch jumps
      (define new-upval-len (length *promoted-upvals*))
      (set! new-upval-len (+ new-upval-len new-upval-len))
      (for-each (lambda (code)
                  (let ([opname (car code)]
                        [oparg (cdr code)])
                    (cond
                      ([or (eq? opname 'J)
                           (eq? opname 'JIF)
                           (eq? opname 'JIFNOT)]
                       (set-car! oparg (+ (car oparg) new-upval-len))))))
                *raw-code*)
      ;; and insert upval builder
      (set! *raw-code* (append *raw-code*
                               (map (lambda (index)
                                      `(BUILDUPVAL ,index))
                                    *promoted-upvals*))))

    (define (get-local name)
      (cadr (assoc name *locals*)))

    (define (get-name name)
      (let ([maybe-name (assoc name *names*)])
        (if maybe-name (cadr maybe-name)
            (let ([new-index (length *names*)])
              (set! *names* (cons `(,name ,new-index) *names*))
              new-index))))

    (define (define-var name)
      (if (assoc name *locals*)
          (get-local name) ;; duplicate define
          (let ([next-local-index (+ (length *upvals*) (length *locals*))])
            (set! *locals* (cons `(,name ,next-local-index) *locals*))
            next-local-index)))

    (define (intern-const value)
      (let ([maybe-interned (assoc value *consts*)])
        (if maybe-interned
            (cadr maybe-interned)
            (let ([next-const (length *consts*)])
              (set! *consts* (cons `(,value ,next-const) *consts*))
              next-const))))

    (define (emit . args)
      ;; Simple optimization targeting define/set!: neutualize LOAD/POP
      (set! *current-pc* (+ *current-pc* (codesize args)))
      (set! *raw-code* (cons args *raw-code*)))

    (define (last-code-ref)
      (car *raw-code*))

    (define (remove-last-code)
      (set! *raw-code* (cdr *raw-code*)))

    (define (add-deferred-lambda name formal-args body)
      (let ([func-index (length *deferred-lambda*)]
            [deferred-lambda `(,name ,formal-args ,body)])
        (set! *deferred-lambda* (cons (cons func-index deferred-lambda)
                                      *deferred-lambda*))
        func-index))

    (define (resolve-deferred-lambda)
      (set! *functions*
        (map (lambda (lam-form)
               (let ([func-index (car lam-form)]
                     [name (cadr lam-form)]
                     [formal-args (caddr lam-form)]
                     [body (cadddr lam-form)])
                 (let ([function (make-function name
                                                formal-args
                                                self)])
                   (compile-function body function)
                   function)))
             *deferred-lambda*)))

    (define (format-output)
      (insert-upval-builder)
      `(BYTECODE-FUNCTION
         (NAME ,*name*)
         (CODE ,(concat-map assemble (reverse *raw-code*)))
         (NB-ARGS ,(+ (length *pos-args*) (if *has-vararg?* 1 0))
                  ,*has-vararg?*)
         (NB-LOCALS ,(+ (length *locals*) (length *upvals*)))
         (UPVAL-DESCRS ,(reverse (map cdr *upvals*)))
         (CONSTS ,(reverse (map car *consts*)))
         (NAMES ,(reverse (map car *names*)))
         (FUNCTIONS ,(reverse (map (lambda (func)
                                     (func 'format-output))
                                   *functions*)))))

    (define methods
      `((type-of-var ,type-of-var)
        (emit ,emit)
        (intern-const ,intern-const)
        (get-local ,get-local)
        (get-name ,get-name)
        (get-upval ,get-upval)
        (promote-to-upval ,promote-to-upval)
        (define-var ,define-var)
        (last-code-ref ,last-code-ref)
        (remove-last-code ,remove-last-code)
        (add-deferred-lambda ,add-deferred-lambda)
        (resolve-deferred-lambda ,resolve-deferred-lambda)
        (format-output ,format-output)
        ))

    ;; self
    (define self
      (lambda (attr . args)
        (cond
          ([eq? attr 'name]
            *name*)
          ([eq? attr 'outer]
            *outer*)
          ([eq? attr 'current-pc]
            *current-pc*)
          ([eq? attr 'is-toplevel?]
           (not *outer*))
          ([assoc attr methods]
           (apply (cadr (assoc attr methods)) args))
          (else
           (error `(attribute-error: ,attr ,args))))))

    self))

(load "source-preprocessor.ss")

(define (main)
  (let ([program (expand-builtin-macro (read-program))])
    ;(map pretty-print program)))
    ((if *debug* pretty-print write)
     (compile-program program))))

(main)

