;; dlmm-core-v-1-1

;; Use DLLM pool trait and SIP 010 trait
(use-trait dlmm-pool-trait .dlmm-pool-trait-v-1-1.dlmm-pool-trait)
(use-trait sip-010-trait .sip-010-trait-ft-standard-v-1-1.sip-010-trait)

;; Error constants
(define-constant ERR_NOT_AUTHORIZED (err u0))
(define-constant ERR_INVALID_AMOUNT (err u0))
(define-constant ERR_ALREADY_BIN_STEP (err u0))
(define-constant ERR_BIN_STEP_LIMIT_REACHED (err u0))
(define-constant ERR_INVALID_MIN_BURNT_SHARES (err u0))
(define-constant ERR_NO_POOL_DATA (err u0))
(define-constant ERR_INVALID_POOL (err u0))
(define-constant ERR_POOL_NOT_CREATED (err u0))
(define-constant ERR_INVALID_POOL_URI (err u0))
(define-constant ERR_VARIABLE_FEES_MANAGER_FROZEN (err u0))
(define-constant ERR_INVALID_PRINCIPAL (err u0))
(define-constant ERR_INVALID_FEE (err u0))
(define-constant ERR_ALREADY_ADMIN (err u0))
(define-constant ERR_ADMIN_LIMIT_REACHED (err u0))
(define-constant ERR_ADMIN_NOT_IN_LIST (err u0))
(define-constant ERR_CANNOT_REMOVE_CONTRACT_DEPLOYER (err u0))
(define-constant ERR_VARIABLE_FEES_COOLDOWN (err u0))
(define-constant ERR_POOL_DISABLED (err u0))
(define-constant ERR_NOT_ACTIVE_BIN (err u0))
(define-constant ERR_INVALID_X_TOKEN (err u0))
(define-constant ERR_INVALID_Y_TOKEN (err u0))
(define-constant ERR_NO_BIN_FACTORS (err u0))
(define-constant ERR_INVALID_BIN_FACTOR (err u0))

;; Contract deployer address
(define-constant CONTRACT_DEPLOYER tx-sender)

;; Number of bins per pool
(define-constant NUM_OF_BINS u1001)

;; Maximum BPS
(define-constant BPS u10000)

;; Admins list and helper var used to remove admins
(define-data-var admins (list 5 principal) (list tx-sender))
(define-data-var admin-helper principal tx-sender)

;; ID of last created pool
(define-data-var last-pool-id uint u0)

;; Allowed bin steps and factor per bin
(define-data-var bin-steps (list 1000 uint) (list u1 u5 u10 u20))
(define-map bin-factors uint (list 1000 uint))

;; Minimum shares required to mint when creating a pool
(define-data-var minimum-total-shares uint u10000)

;; Minimum shares required to burn when creating a pool
(define-data-var minimum-burnt-shares uint u1000)

;; Data var used to enable or disable pool creation by anyone
(define-data-var public-pool-creation bool false)

;; Define pools map
(define-map pools uint {
  id: uint,
  name: (string-ascii 32),
  symbol: (string-ascii 32),
  pool-contract: principal,
  status: bool
})

;; Get admins list
(define-read-only (get-admins)
  (ok (var-get admins))
)

;; Get admin helper var
(define-read-only (get-admin-helper)
  (ok (var-get admin-helper))
)

;; Get ID of last created pool
(define-read-only (get-last-pool-id)
  (ok (var-get last-pool-id))
)

;; Get a pool by pool ID
(define-read-only (get-pool-by-id (id uint))
  (ok (map-get? pools id))
)

;; Get allowed bin steps
(define-read-only (get-bin-steps)
  (ok (var-get bin-steps))
)

;; Get minimum shares required to mint when creating a pool
(define-read-only (get-minimum-total-shares)
  (ok (var-get minimum-total-shares))
)

;; Get minimum shares required to burn when creating a pool
(define-read-only (get-minimum-burnt-shares)
  (ok (var-get minimum-burnt-shares))
)

;; Get public pool creation status
(define-read-only (get-public-pool-creation)
  (ok (var-get public-pool-creation))
)

;; > quotes <

;; get-dy

;; get-dx

;; get-dlp

;; Add a bin step to the bin-steps list
(define-public (add-bin-step (step uint))
  (let (
    (bin-steps-list (var-get bin-steps))
    (caller tx-sender)
  )
    ;; Assert caller is an admin and step is greater than 0
    (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
    (asserts! (> step u0) ERR_INVALID_AMOUNT)

    ;; Assert new bin step is not in bin-steps-list
    (asserts! (is-none (index-of bin-steps-list step)) ERR_ALREADY_BIN_STEP)
    
    ;; Add bin step to list with max length of 1000
    (var-set bin-steps (unwrap! (as-max-len? (append bin-steps-list step) u1000) ERR_BIN_STEP_LIMIT_REACHED))
    
    ;; Print function data and return true
    (print {action: "add-bin-step", caller: caller, data: {step: step}})
    (ok true)
  )
)

;; Set minimum shares required to mint and burn when creating a pool
(define-public (set-minimum-shares (min-total uint) (min-burnt uint))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and amounts are greater than 0
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (and (> min-total u0) (> min-burnt u0)) ERR_INVALID_AMOUNT)
      
      ;; Assert that min-total is greater than min-burnt
      (asserts! (> min-total min-burnt) ERR_INVALID_MIN_BURNT_SHARES)

      ;; Update minimum-total-shares and minimum-burnt-shares
      (var-set minimum-total-shares min-total)
      (var-set minimum-burnt-shares min-burnt)

      ;; Print function data and return true
      (print {
        action: "set-minimum-shares",
        caller: caller,
        data: {
          min-total: min-total,
          min-burnt: min-burnt
        }
      })
      (ok true)
    )
  )
)

;; Enable or disable public pool creation
(define-public (set-public-pool-creation (status bool))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)

      ;; Set public-pool-creation to status
      (var-set public-pool-creation status)

      ;; Print function data and return true
      (print {action: "set-public-pool-creation", caller: caller, data: {status: status}})
      (ok true)
    )
  )
)

;; Set pool uri for a pool
(define-public (set-pool-uri (pool-trait <dlmm-pool-trait>) (uri (string-ascii 256)))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Assert that uri length is greater than 0
      (asserts! (> (len uri) u0) ERR_INVALID_POOL_URI)
      
      ;; Set pool uri for pool
      (try! (contract-call? pool-trait set-pool-uri uri))
      
      ;; Print function data and return true
      (print {
        action: "set-pool-uri",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          uri: uri
        }
      })
      (ok true)
    )
  )
)

;; Set pool status for a pool
(define-public (set-pool-status (pool-trait <dlmm-pool-trait>) (status bool))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (pool-map-data (unwrap! (map-get? pools (get pool-id pool-data)) ERR_NO_POOL_DATA))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Set pool status for pool
      (map-set pools (get pool-id pool-data) (merge pool-map-data {status: status}))
      
      ;; Print function data and return true
      (print {
        action: "set-pool-status",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          status: status
        }
      })
      (ok true)
    )
  )
)

;; Set variable fees manager for a pool
(define-public (set-variable-fees-manager (pool-trait <dlmm-pool-trait>) (manager principal))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (freeze-variable-fees-manager (get freeze-variable-fees-manager pool-data))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Assert that variable fees manager is not frozen
      (asserts! (not freeze-variable-fees-manager) ERR_VARIABLE_FEES_MANAGER_FROZEN)

      ;; Assert that address is standard principal
      (asserts! (is-standard manager) ERR_INVALID_PRINCIPAL) 
      
      ;; Set variable fees manager for pool
      (try! (contract-call? pool-trait set-variable-fees-manager manager))
      
      ;; Print function data and return true
      (print {
        action: "set-variable-fees-manager",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          manager: manager
        }
      })
      (ok true)
    )
  )
)

;; Set fee address for a pool
(define-public (set-fee-address (pool-trait <dlmm-pool-trait>) (address principal))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Assert that address is standard principal
      (asserts! (is-standard address) ERR_INVALID_PRINCIPAL)
      
      ;; Set fee address for pool
      (try! (contract-call? pool-trait set-fee-address address))
      
      ;; Print function data and return true
      (print {
        action: "set-fee-address",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          address: address
        }
      })
      (ok true)
    )
  )
)

;; Set variable fees for a pool
(define-public (set-variable-fees (pool-trait <dlmm-pool-trait>) (x-fee uint) (y-fee uint))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (variable-fees-manager (get variable-fees-manager pool-data))
    (freeze-variable-fees-manager (get freeze-variable-fees-manager pool-data))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin or variable fees manager and pool is created and valid
      (asserts! (or (is-some (index-of (var-get admins) caller)) (is-eq variable-fees-manager caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)

      ;; Assert that caller is variable fees manager if variable fees manager is frozen
      (asserts! (or (is-eq variable-fees-manager caller) (not freeze-variable-fees-manager)) ERR_NOT_AUTHORIZED)

      ;; Assert x-fee and y-fee are less than maximum BPS
      (asserts! (and (< x-fee BPS) (< y-fee BPS)) ERR_INVALID_FEE)

      ;; Set variable fees for pool
      (try! (contract-call? pool-trait set-variable-fees x-fee y-fee))

      ;; Print function data and return true
      (print {
        action: "set-variable-fees",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          x-fee: x-fee,
          y-fee: y-fee
        }
      })
      (ok true)
    )
  )
)

;; Set x fees for a pool
(define-public (set-x-fees (pool-trait <dlmm-pool-trait>) (protocol-fee uint) (provider-fee uint))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Assert protocol-fee and provider-fee is less than maximum BPS
      (asserts! (< (+ protocol-fee provider-fee) BPS) ERR_INVALID_FEE)
      
      ;; Set x fees for pool
      (try! (contract-call? pool-trait set-x-fees protocol-fee provider-fee))
      
      ;; Print function data and return true
      (print {
        action: "set-x-fees",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          protocol-fee: protocol-fee,
          provider-fee: provider-fee
        }
      })
      (ok true)
    )
  )
)

;; Set y fees for a pool
(define-public (set-y-fees (pool-trait <dlmm-pool-trait>) (protocol-fee uint) (provider-fee uint))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Assert protocol-fee and provider-fee is less than maximum BPS
      (asserts! (< (+ protocol-fee provider-fee) BPS) ERR_INVALID_FEE)
      
      ;; Set y fees for pool
      (try! (contract-call? pool-trait set-y-fees protocol-fee provider-fee))
      
      ;; Print function data and return true
      (print {
        action: "set-y-fees",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          protocol-fee: protocol-fee,
          provider-fee: provider-fee
        }
      })
      (ok true)
    )
  )
)

;; Set variable fees cooldown for a pool
(define-public (set-variable-fees-cooldown (pool-trait <dlmm-pool-trait>) (cooldown uint))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Set variable fees cooldown for pool
      (try! (contract-call? pool-trait set-variable-fees-cooldown cooldown))
      
      ;; Print function data and return true
      (print {
        action: "set-variable-fees-cooldown",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait),
          cooldown: cooldown
        }
      })
      (ok true)
    )
  )
)

;; Set freeze variable fees manager for a pool
(define-public (set-freeze-variable-fees-manager (pool-trait <dlmm-pool-trait>))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (freeze-variable-fees-manager (get freeze-variable-fees-manager pool-data))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)
      
      ;; Assert that variable fees manager is not frozen
      (asserts! (not freeze-variable-fees-manager) ERR_VARIABLE_FEES_MANAGER_FROZEN)

      ;; Set freeze variable fees manager for pool
      (try! (contract-call? pool-trait set-freeze-variable-fees-manager))
      
      ;; Print function data and return true
      (print {
        action: "set-freeze-variable-fees-manager",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait)
        }
      })
      (ok true)
    )
  )
)

;; Reset variable fees for a pool
(define-public (reset-variable-fees (pool-trait <dlmm-pool-trait>))
  (let (
    ;; Gather all pool data
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (last-variable-fees-update (get last-variable-fees-update pool-data))
    (variable-fees-cooldown (get variable-fees-cooldown pool-data))
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and pool is created and valid
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL)
      (asserts! (is-eq (get pool-created pool-data) true) ERR_POOL_NOT_CREATED)

      ;; Assert that variable fees cooldown period has passed
      (asserts! (>= stacks-block-height (+ last-variable-fees-update variable-fees-cooldown)) ERR_VARIABLE_FEES_COOLDOWN)

      ;; Reset variable fees for pool
      (try! (contract-call? pool-trait set-variable-fees u0 u0))
      
      ;; Print function data and return true
      (print {
        action: "reset-variable-fees",
        caller: caller,
        data: {
          pool-id: (get pool-id pool-data),
          pool-name: (get pool-name pool-data),
          pool-contract: (contract-of pool-trait)
        }
      })
      (ok true)
    )
  )
)

;; create-pool

(define-public (swap-x-for-y
  (pool-trait <dlmm-pool-trait>)
  (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
  (bin-id uint) (x-amount uint)
  )
  (let (
    ;; Gather all pool data and check if pool is valid
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (pool-validity-check (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL))
    (pool-contract (contract-of pool-trait))
    (fee-address (get fee-address pool-data))
    (x-token (get x-token pool-data))
    (y-token (get y-token pool-data))
    (x-balance (get x-balance pool-data))
    (y-balance (get y-balance pool-data))
    (active-price u0) ;;(get active-price pool-data))
    (active-bin-id (get active-bin-id pool-data))
    (bin-step (get bin-step pool-data))
    (protocol-fee (get x-protocol-fee pool-data))
    (provider-fee (get x-provider-fee pool-data))
    (variable-fee (get x-variable-fee pool-data))

    ;; Get balances at active bin
    (bin-balances (try! (contract-call? pool-trait get-bin-balances bin-id)))
    (bin-x-balance (get x-balance bin-balances))
    (bin-y-balance (get y-balance bin-balances))

    ;; Calculate fees on x-amount and dx
    (x-amount-fees-protocol (/ (* x-amount protocol-fee) BPS))
    (x-amount-fees-provider (/ (* x-amount provider-fee) BPS))
    (x-amount-fees-variable (/ (* x-amount variable-fee) BPS))
    (x-amount-fees-total (+ x-amount-fees-protocol x-amount-fees-provider x-amount-fees-variable))
    (dx (- x-amount x-amount-fees-total))

    ;; Calculate bin price and dy
    (bin-price u0)
    (dy u0)

    ;; Update bin and overall pool balances
    (updated-bin-x-balance (+ bin-x-balance dx x-amount-fees-provider x-amount-fees-variable))
    (updated-bin-y-balance (- bin-y-balance dy))
    (updated-bin-data {id: bin-id, x-balance: updated-bin-x-balance, y-balance: updated-bin-y-balance})
    (updated-pool-data {x-balance: (+ x-balance dx x-amount-fees-provider x-amount-fees-variable), y-balance: (- y-balance dx)})
    (caller tx-sender)
  )
    (begin
      ;; Assert that pool-status is true and correct token traits are used
      (asserts! (is-eq (is-enabled-pool (get pool-id pool-data)) true) ERR_POOL_DISABLED)
      (asserts! (is-eq (contract-of x-token-trait) x-token) ERR_INVALID_X_TOKEN)
      (asserts! (is-eq (contract-of y-token-trait) y-token) ERR_INVALID_Y_TOKEN)
      
      ;; Assert that x-amount is greater than 0
      (asserts! (> x-amount u0) ERR_INVALID_AMOUNT)

      ;; Assert that bin-x-balance and bin-y-balance are greater than 0
      (asserts! (and (> bin-x-balance u0) (> bin-y-balance u0)) ERR_NOT_ACTIVE_BIN)

      ;; Transfer dx + x-amount-fees-provider + x-amount-fees-variable from caller to pool-contract
      (try! (contract-call? x-token-trait transfer (+ dx x-amount-fees-provider x-amount-fees-variable) caller pool-contract none))

      ;; Transfer dx y tokens from pool-contract to caller
      (try! (contract-call? pool-trait pool-transfer y-token-trait dx caller))

      ;; Transfer x-amount-fees-protocol x tokens from caller to fee-address
      (if (> x-amount-fees-protocol u0)
        (try! (contract-call? x-token-trait transfer x-amount-fees-protocol caller fee-address none))
        false
      )

      ;; Update bin balances
      (try! (contract-call? pool-trait update-bin-balances updated-bin-data updated-pool-data))

      ;; Set active bin id
      ;;(if (and (> bin-x-balance u0) (> bin-y-balance u0))
      ;;  (try! (contract-call? pool-trait set-active-bin-id bin-id))
      ;;  (if (> bin-y-balance u0)
      ;;    (try! (contract-call? pool-trait set-active-bin-id (+ bin-id u1)))
      ;;    (try! (contract-call? pool-trait set-active-bin-id (- bin-id u1)))
      ;;  )
      ;;)

      ;; Print swap data and return number of y tokens the caller received
      (print 0x)
      (ok dy)
    )
  )
)

;; swap-y-for-x

;; add-liquidity

;; withdraw-liquidity

;; Add an admin to the admins list
(define-public (add-admin (admin principal))
  (let (
    (admins-list (var-get admins))
    (caller tx-sender)
  )
    ;; Assert caller is an existing admin and new admin is not in admins-list
    (asserts! (is-some (index-of admins-list caller)) ERR_NOT_AUTHORIZED)
    (asserts! (is-none (index-of admins-list admin)) ERR_ALREADY_ADMIN)
    
    ;; Add admin to list with max length of 5
    (var-set admins (unwrap! (as-max-len? (append admins-list admin) u5) ERR_ADMIN_LIMIT_REACHED))
    
    ;; Print add admin data and return true
    (print {action: "add-admin", caller: caller, data: {admin: admin}})
    (ok true)
  )
)

;; Remove an admin from the admins list
(define-public (remove-admin (admin principal))
  (let (
    (admins-list (var-get admins))
    (caller tx-sender)
  )
    ;; Assert caller is an existing admin and admin to remove is in admins-list
    (asserts! (is-some (index-of admins-list caller)) ERR_NOT_AUTHORIZED)
    (asserts! (is-some (index-of admins-list admin)) ERR_ADMIN_NOT_IN_LIST)

    ;; Assert contract deployer cannot be removed
    (asserts! (not (is-eq admin CONTRACT_DEPLOYER)) ERR_CANNOT_REMOVE_CONTRACT_DEPLOYER)

    ;; Set admin-helper to admin to remove and filter admins-list to remove admin
    (var-set admin-helper admin)
    (var-set admins (filter admin-not-removable admins-list))

    ;; Print remove admin data and return true
    (print {action: "remove-admin", caller: caller, data: {admin: admin}})
    (ok true)
  )
)

;; Set pool uri for multiple pools
(define-public (set-pool-uri-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (uris (list 120 (string-ascii 256)))
  )
  (ok (map set-pool-uri pool-traits uris))
)

;; Set pool status for multiple pools
(define-public (set-pool-status-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (statuses (list 120 bool))
  )
  (ok (map set-pool-status pool-traits statuses))
)

;; Set variable fees manager for multiple pools
(define-public (set-variable-fees-manager-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (managers (list 120 principal))
  )
  (ok (map set-variable-fees-manager pool-traits managers))
)

;; Set fee address for multiple pools
(define-public (set-fee-address-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (addresses (list 120 principal))
  )
  (ok (map set-fee-address pool-traits addresses))
)

;; Set variable fees for multiple pools
(define-public (set-variable-fees-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (x-fees (list 120 uint))
    (y-fees (list 120 uint))
  )
  (ok (map set-variable-fees pool-traits x-fees y-fees))
)

;; Set x fees for multiple pools
(define-public (set-x-fees-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (protocol-fees (list 120 uint))
    (provider-fees (list 120 uint))
  )
  (ok (map set-x-fees pool-traits protocol-fees provider-fees))
)

;; Set y fees for multiple pools
(define-public (set-y-fees-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (protocol-fees (list 120 uint))
    (provider-fees (list 120 uint))
  )
  (ok (map set-y-fees pool-traits protocol-fees provider-fees))
)

;; Set variable fees cooldown for multiple pools
(define-public (set-variable-fees-cooldown-multi
    (pool-traits (list 120 <dlmm-pool-trait>))
    (cooldowns (list 120 uint))
  )
  (ok (map set-variable-fees-cooldown pool-traits cooldowns))
)

;; Set freeze variable fees manager for multiple pools
(define-public (set-freeze-variable-fees-manager-multi (pool-traits (list 120 <dlmm-pool-trait>)))
  (ok (map set-freeze-variable-fees-manager pool-traits))
)

;; Reset variable fees for multiple pools
(define-public (reset-variable-fees-multi (pool-traits (list 120 <dlmm-pool-trait>)))
  (ok (map reset-variable-fees pool-traits))
)

;; Helper function for removing an admin
(define-private (admin-not-removable (admin principal))
  (not (is-eq admin (var-get admin-helper)))
)

;; Create pool symbol using x token and y token symbols
(define-private (create-symbol (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>))
  (let (
    ;; Get x token and y token symbols
    (x-symbol (unwrap-panic (contract-call? x-token-trait get-symbol)))
    (y-symbol (unwrap-panic (contract-call? y-token-trait get-symbol)))
    
    ;; Truncate symbols if length exceeds 14
    (x-truncated 
      (if (> (len x-symbol) u14)
        (unwrap-panic (slice? x-symbol u0 u14))
        x-symbol
      )
    )
    (y-truncated
      (if (> (len y-symbol) u14)
        (unwrap-panic (slice? y-symbol u0 u14))
        y-symbol
      )
    )
  )
    ;; Return pool symbol with max length of 29
    (as-max-len? (concat x-truncated (concat "-" y-truncated)) u29)
  )
)

;; Check if a pool is valid
(define-private (is-valid-pool (id uint) (contract principal))
  (let (
    (pool-data (unwrap! (map-get? pools id) false))
  )
    (is-eq contract (get pool-contract pool-data))
  )
)

;; Check if a pool is enabled
(define-private (is-enabled-pool (id uint))
  (let (
    (pool-data (unwrap! (map-get? pools id) false))
  )
    (is-eq true (get status pool-data))
  )
)
