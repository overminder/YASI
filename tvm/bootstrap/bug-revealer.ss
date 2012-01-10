((lambda ()
  (define some-upval 0)
  ((lambda (_) some-upval)
     (if #f 1 2))))

