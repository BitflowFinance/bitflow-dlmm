;; dlmm-core-trait-v-1-1

;; Define core trait for DLMM Core
(define-trait dlmm-core-trait
  (
    (accept-migrated-pool (principal principal principal uint uint (string-ascii 32) (string-ascii 32) bool) (response bool uint))
  )
)