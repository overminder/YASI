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
  (if (= n 0) lst)
      (list-tail (cdr lst) (- n 1)))

(define (list-ref lst n)
  (car (list-tail lst n)))

(define (map proc args)
  (if (null? args) '()
      (cons (proc (car args))
            (map proc (cdr args)))))

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


