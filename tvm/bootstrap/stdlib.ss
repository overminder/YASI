(define (id x) x)
(define (not x) (if x #f #t))

(define (<= x y)
  (or (< x y)
      (= x y)))

(define (>= x y)
  (or (> x y)
      (= x y)))

(define (caar x) (car (car x)))
(define (cadr x) (car (cdr x)))
(define (cdar x) (cdr (car x)))
(define (cddr x) (cdr (cdr x)))

(define (caaar x) (car (car (car x))))
(define (caadr x) (car (car (cdr x))))
(define (cadar x) (car (cdr (car x))))
(define (caddr x) (car (cdr (cdr x))))
(define (cdaar x) (cdr (car (car x))))
(define (cdadr x) (cdr (car (cdr x))))
(define (cddar x) (cdr (cdr (car x))))
(define (cdddr x) (cdr (cdr (cdr x))))

(define (caaaar x) (car (car (car (car x)))))
(define (caaadr x) (car (car (car (cdr x)))))
(define (caadar x) (car (car (cdr (car x)))))
(define (caaddr x) (car (car (cdr (cdr x)))))
(define (cadaar x) (car (cdr (car (car x)))))
(define (cadadr x) (car (cdr (car (cdr x)))))
(define (caddar x) (car (cdr (cdr (car x)))))
(define (cadddr x) (car (cdr (cdr (cdr x)))))

(define (cdaaar x) (cdr (car (car (car x)))))
(define (cdaadr x) (cdr (car (car (cdr x)))))
(define (cdadar x) (cdr (car (cdr (car x)))))
(define (cdaddr x) (cdr (car (cdr (cdr x)))))
(define (cddaar x) (cdr (cdr (car (car x)))))
(define (cddadr x) (cdr (cdr (car (cdr x)))))
(define (cdddar x) (cdr (cdr (cdr (car x)))))
(define (cddddr x) (cdr (cdr (cdr (cdr x)))))

(define (list . x)
  x)

(define (cons* . args)
  (let ([rv (reverse args)])
    (append (reverse (cdr rv)) (car rv))))

(define length
  (let ()
    (define (length1 arg res)
      (if (null? arg) res
          (length1 (cdr arg) (+ 1 res))))
    (lambda (lst)
      (length1 lst 0))))

(define reverse
  (let ()
    (define (reverse1 arg res)
      (if (null? arg) res
          (reverse1 (cdr arg) (cons (car arg) res))))
    (lambda (lst)
      (reverse1 lst '()))))

(define (list-tail lst n)
  (if (<= n 0) lst
      (list-tail (cdr lst) (- n 1))))

(define (list-head lst n)
  (if (= n 0) '()
      (cons (car lst) (list-head (cdr lst) (- n 1)))))

(define (list-ref lst n)
  (car (list-tail lst n)))

(define (list-index lst item)
  (define (loop lst n)
    (if (null? lst) #f
        (if (equal? (car lst) item)
            n
            (loop (cdr lst) (+ n 1)))))
  (loop lst 0))
                    

;; tail-recursive map is 2 times faster than its non-tr counter part
(define (map proc args)
  (define (rev-map args res)
    (if (null? args) res
        (rev-map (cdr args) (cons (proc (car args)) res))))
  (reverse (rev-map args '())))

(define (for-each proc args)
  (if (null? args) '()
      (begin
        (proc (car args))
        (for-each proc (cdr args)))))

(define (append lst1 lst2)
  (if (null? lst1) lst2
      (cons (car lst1) (append (cdr lst1) lst2))))

(define (assoc key alist)
  (if (null? alist) #f
      (if (equal? key (caar alist))
          (car alist)
          (assoc key (cdr alist)))))

(define (range . args)
  (define (mkrange start end step)
    (if (< start end)
        (cons start (mkrange (+ start step) end step))
        '()))
  (define len (length args))
  (cond
    ([= len 1]
     (mkrange 0 (car args) 1))
    ([= len 2]
     (mkrange (car args) (cadr args) 1))
    ([= len 3]
     (mkrange (car args) (cadr args) (caddr args)))
    (else
     (error `(wrong argument count: range ,args)))))


;; utils
(define (fibo n)
  (if (< n 2)
      n
      (+ (fibo (- n 1))
         (fibo (- n 2)))))

(define (prn x)
  (display x)
  (newline))

(define write display) ;; for now

(define (do-times n proc . args)
  (define (thunk)
    (apply proc args))
  (define (loop n)
    (if (< n 1) #f
        (begin
          (thunk)
          (loop (- n 1)))))
  (loop n))

;; make #<unspecified>
(define *unspec* #f)
(define *unspec* (set! *unspec* #t))

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

(define (split-dotted-pair lst)
  (if (pair? lst)
      (let ([hd (car lst)]
            [rest (split-dotted-pair (cdr lst))])
        (cons (cons hd (car rest))
              (cdr rest)))
      (cons '() lst)))

