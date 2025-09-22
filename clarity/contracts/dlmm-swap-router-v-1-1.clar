;; dlmm-swap-router-v-1-1

;; Use DLMM pool trait and SIP 010 trait
(use-trait dlmm-pool-trait .dlmm-pool-trait-v-1-1.dlmm-pool-trait)
(use-trait sip-010-trait .sip-010-trait-ft-standard-v-1-1.sip-010-trait)

;; Error constants
(define-constant ERR_NO_RESULT_DATA (err u2001))
(define-constant ERR_BIN_SLIPPAGE (err u2002))
(define-constant ERR_MINIMUM_RECEIVED (err u2003))
(define-constant ERR_MINIMUM_X_AMOUNT (err u2004))
(define-constant ERR_MINIMUM_Y_AMOUNT (err u2005))
(define-constant ERR_NO_ACTIVE_BIN_DATA (err u2006))
(define-constant ERR_EMPTY_SWAPS_LIST (err u2007))
(define-constant ERR_RESULTS_LIST_OVERFLOW (err u2008))

;; Swap through multiple bins in multiple pools
(define-public (swap-multi
    (swaps (list 350 {pool-trait: <dlmm-pool-trait>, x-token-trait: <sip-010-trait>, y-token-trait: <sip-010-trait>, expected-bin-id: int, amount: uint, min-received: uint, x-for-y: bool}))
    (max-unfavorable-bins uint)
  )
  (let (
    (swap-result (try! (fold fold-swap-multi swaps (ok {results: (list ), unfavorable: u0}))))
  )
    (asserts! (> (len swaps) u0) ERR_EMPTY_SWAPS_LIST)
    (asserts! (<= (get unfavorable swap-result) max-unfavorable-bins) ERR_BIN_SLIPPAGE)
    (ok swap-result)
  )
)

;; Swap through multiple bins in multiple pools using the same token pair
(define-public (swap-same-multi
    (swaps (list 350 {pool-trait: <dlmm-pool-trait>, expected-bin-id: int, min-received: uint, x-for-y: bool}))
    (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
    (amount uint) (min-x-amount-total uint) (min-y-amount-total uint) (max-unfavorable-bins uint)
  )
  (let (
    (initial-x-for-y (get x-for-y (unwrap! (element-at swaps u0) ERR_EMPTY_SWAPS_LIST)))
    (x-amount-for-swap (if initial-x-for-y amount u0))
    (y-amount-for-swap (if initial-x-for-y u0 amount))
    (swap-result (try! (fold fold-swap-same-multi swaps (ok {x-token-trait: x-token-trait, y-token-trait: y-token-trait, results: (list ), x-amount-for-swap: x-amount-for-swap, y-amount-for-swap: y-amount-for-swap, x-amount: u0, y-amount: u0, unfavorable: u0}))))
    (x-amount-total (get x-amount swap-result))
    (y-amount-total (get y-amount swap-result))
    (unfavorable (get unfavorable swap-result))
 )
    (asserts! (> (len swaps) u0) ERR_EMPTY_SWAPS_LIST)
    (asserts! (<= unfavorable max-unfavorable-bins) ERR_BIN_SLIPPAGE)
    (asserts! (>= x-amount-total min-x-amount-total) ERR_MINIMUM_X_AMOUNT)
    (asserts! (>= y-amount-total min-y-amount-total) ERR_MINIMUM_Y_AMOUNT)
    (ok {results: (get results swap-result), x-amount: x-amount-total, y-amount: y-amount-total, unfavorable: unfavorable})
  )
)

;; Swap through multiple bins in multiple pools using the same token pair and X for Y direction
(define-public (swap-x-for-y-same-multi
    (swaps (list 350 {pool-trait: <dlmm-pool-trait>, expected-bin-id: int, min-received: uint}))
    (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
    (amount uint) (min-y-amount-total uint) (max-unfavorable-bins uint)
  )
  (let (
    (swap-result (try! (fold fold-swap-x-for-y-same-multi swaps (ok {x-token-trait: x-token-trait, y-token-trait: y-token-trait, results: (list ), x-amount-for-swap: amount, y-amount: u0, unfavorable: u0}))))
    (y-amount-total (get y-amount swap-result))
    (unfavorable (get unfavorable swap-result))
 )
    (asserts! (> (len swaps) u0) ERR_EMPTY_SWAPS_LIST)
    (asserts! (<= unfavorable max-unfavorable-bins) ERR_BIN_SLIPPAGE)
    (asserts! (>= y-amount-total min-y-amount-total) ERR_MINIMUM_Y_AMOUNT)
    (ok {results: (get results swap-result), y-amount: y-amount-total, unfavorable: unfavorable})
  )
)

;; Swap through multiple bins in multiple pools using the same token pair and Y for X direction
(define-public (swap-y-for-x-same-multi
    (swaps (list 350 {pool-trait: <dlmm-pool-trait>, expected-bin-id: int, min-received: uint}))
    (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
    (amount uint) (min-x-amount-total uint) (max-unfavorable-bins uint)
  )
  (let (
    (swap-result (try! (fold fold-swap-y-for-x-same-multi swaps (ok {x-token-trait: x-token-trait, y-token-trait: y-token-trait, results: (list ), y-amount-for-swap: amount, x-amount: u0, unfavorable: u0}))))
    (x-amount-total (get x-amount swap-result))
    (unfavorable (get unfavorable swap-result))
 )
    (asserts! (> (len swaps) u0) ERR_EMPTY_SWAPS_LIST)
    (asserts! (<= unfavorable max-unfavorable-bins) ERR_BIN_SLIPPAGE)
    (asserts! (>= x-amount-total min-x-amount-total) ERR_MINIMUM_X_AMOUNT)
    (ok {results: (get results swap-result), x-amount: x-amount-total, unfavorable: unfavorable})
  )
)

;; Fold function to swap through multiple bins in multiple pools
(define-private (fold-swap-multi
    (swap {pool-trait: <dlmm-pool-trait>, x-token-trait: <sip-010-trait>, y-token-trait: <sip-010-trait>, expected-bin-id: int, amount: uint, min-received: uint, x-for-y: bool})
    (result (response {results: (list 350 {in: uint, out: uint}), unfavorable: uint} uint))
  )
  (let (
    (result-data (unwrap! result ERR_NO_RESULT_DATA))
    (pool-trait (get pool-trait swap))
    (x-token-trait (get x-token-trait swap))
    (y-token-trait (get y-token-trait swap))
    (amount (get amount swap))
    (x-for-y (get x-for-y swap))
    (active-bin-id (unwrap! (contract-call? pool-trait get-active-bin-id) ERR_NO_ACTIVE_BIN_DATA))
    (bin-id-delta (- active-bin-id (get expected-bin-id swap)))
    (is-unfavorable (if x-for-y (> bin-id-delta 0) (< bin-id-delta 0)))
    (swap-result (if x-for-y
                     (try! (contract-call? .dlmm-core-v-1-1 swap-x-for-y pool-trait x-token-trait y-token-trait active-bin-id amount))
                     (try! (contract-call? .dlmm-core-v-1-1 swap-y-for-x pool-trait x-token-trait y-token-trait active-bin-id amount))))
    (updated-results (unwrap! (as-max-len? (append (get results result-data) swap-result) u350) ERR_RESULTS_LIST_OVERFLOW))
  )
    (asserts! (>= (get out swap-result) (get min-received swap)) ERR_MINIMUM_RECEIVED)
    (ok {
      results: updated-results,
      unfavorable: (+ (get unfavorable result-data) (if is-unfavorable (abs-int bin-id-delta) u0))
    })
  )
)

;; Fold function to swap through multiple bins in multiple pools using the same token pair
(define-private (fold-swap-same-multi
    (swap {pool-trait: <dlmm-pool-trait>, expected-bin-id: int, min-received: uint, x-for-y: bool})
    (result (response {x-token-trait: <sip-010-trait>, y-token-trait: <sip-010-trait>, results: (list 350 {in: uint, out: uint}), x-amount-for-swap: uint, y-amount-for-swap: uint, x-amount: uint, y-amount: uint, unfavorable: uint} uint))
  )
  (let (
      (result-data (unwrap! result ERR_NO_RESULT_DATA))
      (pool-trait (get pool-trait swap))
      (x-for-y (get x-for-y swap))
      (x-token-trait (get x-token-trait result-data))
      (y-token-trait (get y-token-trait result-data))
      (x-amount-for-swap (get x-amount-for-swap result-data))
      (y-amount-for-swap (get y-amount-for-swap result-data))
      (x-amount (get x-amount result-data))
      (y-amount (get y-amount result-data))
      (amount-for-swap (if x-for-y x-amount-for-swap y-amount-for-swap))
  )
    (if (> amount-for-swap u0)
        (let (
          (active-bin-id (unwrap! (contract-call? pool-trait get-active-bin-id) ERR_NO_ACTIVE_BIN_DATA))
          (bin-id-delta (- active-bin-id (get expected-bin-id swap)))
          (is-unfavorable (if x-for-y (> bin-id-delta 0) (< bin-id-delta 0)))
          (swap-result (if x-for-y
                           (try! (contract-call? .dlmm-core-v-1-1 swap-x-for-y pool-trait x-token-trait y-token-trait active-bin-id amount-for-swap))
                           (try! (contract-call? .dlmm-core-v-1-1 swap-y-for-x pool-trait x-token-trait y-token-trait active-bin-id amount-for-swap))))
          (in (get in swap-result))
          (out (get out swap-result))
          (updated-results (unwrap! (as-max-len? (append (get results result-data) swap-result) u350) ERR_RESULTS_LIST_OVERFLOW))
          (updated-x-amount-for-swap (if x-for-y (- x-amount-for-swap in) (+ x-amount-for-swap out)))
          (updated-y-amount-for-swap (if x-for-y (+ y-amount-for-swap out) (- y-amount-for-swap in)))
          (updated-x-amount (if x-for-y x-amount (+ x-amount out)))
          (updated-y-amount (if x-for-y (+ y-amount out) y-amount))
        )
          (asserts! (>= out (get min-received swap)) ERR_MINIMUM_RECEIVED)
          (ok {
            x-token-trait: x-token-trait,
            y-token-trait: y-token-trait,
            results: updated-results,
            x-amount-for-swap: updated-x-amount-for-swap,
            y-amount-for-swap: updated-y-amount-for-swap,
            x-amount: updated-x-amount,
            y-amount: updated-y-amount,
            unfavorable: (+ (get unfavorable result-data) (if is-unfavorable (abs-int bin-id-delta) u0))
          })
        )
        (ok result-data))
  )
)

;; Fold function to swap through multiple bins in multiple pools using the same token pair and X for Y direction
(define-private (fold-swap-x-for-y-same-multi
    (swap {pool-trait: <dlmm-pool-trait>, expected-bin-id: int, min-received: uint})
    (result (response {x-token-trait: <sip-010-trait>, y-token-trait: <sip-010-trait>, results: (list 350 {in: uint, out: uint}), x-amount-for-swap: uint, y-amount: uint, unfavorable: uint} uint))
  )
  (let (
      (result-data (unwrap! result ERR_NO_RESULT_DATA))
      (pool-trait (get pool-trait swap))
      (x-token-trait (get x-token-trait result-data))
      (y-token-trait (get y-token-trait result-data))
      (x-amount-for-swap (get x-amount-for-swap result-data))
  )
    (if (> x-amount-for-swap u0)
        (let (
          (active-bin-id (unwrap! (contract-call? pool-trait get-active-bin-id) ERR_NO_ACTIVE_BIN_DATA))
          (bin-id-delta (- active-bin-id (get expected-bin-id swap)))
          (is-unfavorable (> bin-id-delta 0))
          (swap-result (try! (contract-call? .dlmm-core-v-1-1 swap-x-for-y pool-trait x-token-trait y-token-trait active-bin-id x-amount-for-swap)))
          (out (get out swap-result))
          (updated-results (unwrap! (as-max-len? (append (get results result-data) swap-result) u350) ERR_RESULTS_LIST_OVERFLOW))
          (updated-x-amount-for-swap (- x-amount-for-swap (get in swap-result)))
          (updated-y-amount (+ (get y-amount result-data) out))
        )
          (asserts! (>= out (get min-received swap)) ERR_MINIMUM_RECEIVED)
          (ok {
            x-token-trait: x-token-trait,
            y-token-trait: y-token-trait,
            results: updated-results,
            x-amount-for-swap: updated-x-amount-for-swap,
            y-amount: updated-y-amount,
            unfavorable: (+ (get unfavorable result-data) (if is-unfavorable (abs-int bin-id-delta) u0))
          })
        )
        (ok result-data))
  )
)

;; Fold function to swap through multiple bins in multiple pools using the same token pair and Y for X direction
(define-private (fold-swap-y-for-x-same-multi
    (swap {pool-trait: <dlmm-pool-trait>, expected-bin-id: int, min-received: uint})
    (result (response {x-token-trait: <sip-010-trait>, y-token-trait: <sip-010-trait>, results: (list 350 {in: uint, out: uint}), y-amount-for-swap: uint, x-amount: uint, unfavorable: uint} uint))
  )
  (let (
      (result-data (unwrap! result ERR_NO_RESULT_DATA))
      (pool-trait (get pool-trait swap))
      (x-token-trait (get x-token-trait result-data))
      (y-token-trait (get y-token-trait result-data))
      (y-amount-for-swap (get y-amount-for-swap result-data))
  )
    (if (> y-amount-for-swap u0)
        (let (
          (active-bin-id (unwrap! (contract-call? pool-trait get-active-bin-id) ERR_NO_ACTIVE_BIN_DATA))
          (bin-id-delta (- active-bin-id (get expected-bin-id swap)))
          (is-unfavorable (< bin-id-delta 0))
          (swap-result (try! (contract-call? .dlmm-core-v-1-1 swap-y-for-x pool-trait x-token-trait y-token-trait active-bin-id y-amount-for-swap)))
          (out (get out swap-result))
          (updated-results (unwrap! (as-max-len? (append (get results result-data) swap-result) u350) ERR_RESULTS_LIST_OVERFLOW))
          (updated-y-amount-for-swap (- y-amount-for-swap (get in swap-result)))
          (updated-x-amount (+ (get x-amount result-data) out))
        )
          (asserts! (>= out (get min-received swap)) ERR_MINIMUM_RECEIVED)
          (ok {
            x-token-trait: x-token-trait,
            y-token-trait: y-token-trait,
            results: updated-results,
            y-amount-for-swap: updated-y-amount-for-swap,
            x-amount: updated-x-amount,
            unfavorable: (+ (get unfavorable result-data) (if is-unfavorable (abs-int bin-id-delta) u0))
          })
        )
        (ok result-data))
  )
)

;; Get absolute value of a signed int as uint
(define-private (abs-int (value int))
  (to-uint (if (>= value 0) value (- value)))
)