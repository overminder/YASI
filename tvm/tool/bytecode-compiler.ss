(define _ #f)
(define *unspec* (set! _ #f)) ;; hack to make #<unspecified>

(define (assert condition msg)
  (if (not condition)
      (error msg)))

(define (all lst)
  (if (null? lst) #t
      (and (car lst)
           (all (cdr lst)))))

(define (compile-to-bytecode program context)
  (compile-function program context))

(define (compile-function program context)
  (let ([current-function (context 'current-function)])
    (for-each (lambda (expr)
                (compile-expr-in expr current-function))
              program)))

(define (compile-expr-in expr function)
  (cond
    ([pair? expr]
     (compile-pair-in expr function))
    ([symbol? expr]
     (compile-var-in expr function))
    ([or (integer? expr)
         (boolean? expr)]
     (compile-const-in expr function))))

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
           (for-each (lambda (expr)
                       (compile-expr-in expr function))
                     args)))
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
  (function 'load-const const))

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
           (let ([func (context 'add-deferred-lambda name formal-args rest)]
                 [local-index (function 'define-var first)])
             (function 'emit 'BUILDCLOSURE func)
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

(define (compile-application-in proc args function)
  (for-each (lambda (expr)
              (compile-expr-in expr function))
            args)
  (compile-expr-in proc function)
  (function 'emit 'CALL (length args)))

;; Context and Function

(define (make-context)
  (define current-function (make-function 'main ;; name
                                          '() ;; formal-args
                                          #f ;; outer-function
                                          self)) ;; context
  (define main-function current-function)

  (define (add-deferred-lambda name formal-args body)
    (current-function 'add-deferred-lambda
                      (make-function name formal-args current-function self)
                      body))

  (define (resolve-deferred-lambda)
    (define saved-current-function current-function)
    (for-each (lambda (form)
                (let ([function (car form)]
                      [body (cadr form)])
                  (set! current-function function)
                  (compile-function body self)))
      (saved-current-function 'get-deferred-lambda))
    (set! current-function saved-current-function))

  ;; self
  (define self
    (lambda (attr . args)
      (cond
        ([eq? attr 'current-function]
          current-function)
        ([eq? attr 'main-function]
          main-function)
        ([eq? attr 'add-deferred-lambda]
         (apply add-deferred-lambda args))
        ([eq? attr 'resolve-deferred-lambda]
         (apply resolve-deferred-lambda args)))))
  self)

(define (make-function name formal-args outer context)
  (define *raw-code* '())
  (define *consts* '())
  (define *names* '()) ;; (name, name-index)
  (define *locals* '()) ;; (name, local-index)
  (define *upvals* '()) ;; (name, upval-rel-index)

  (define (type-of-var name)
    (cond
      ([assoc name *locals*]
       'local)
      ([assoc name *upvals*]
       'upval)
      (outer
       (let ([outer-type (outer 'type-of-var name)])
         (cond
           ([eq? outer-type 'local]
            (add-to-upval-descr name (outer 'promote-to-upval name))
             'upval)
           ([eq? outer-type 'upval]
            (add-to-upval-descr name (outer 'get-upval name)))
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
    (cadr (assoc *locals* name)))

  (define (get-upval name)
    (cadr (assoc *upvals* name)))

  (define (get-name name)
    (let ([maybe-name (assoc *names* name)])
      (if maybe-name (cadr maybe-name)
          (let ([new-index (length *names*)])
            (set! *names* (cons `(,name ,new-index) *names*))
            new-index))))

  (define (emit . args)
    (set! *raw-code* (cons args *raw-code*)))

  ;; self
  (lambda (attr . args)
    (cond
      ([eq? attr 'name]
        name)
      ([eq? attr 'outer]
        outer)
      ([eq? attr 'context]
        context)
      (else
       (error 'attribute-error)))))

