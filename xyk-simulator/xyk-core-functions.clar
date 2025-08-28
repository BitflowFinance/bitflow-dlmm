;; xyk-core-v-1-2

;; Use XYK pool trait and SIP 010 trait
(use-trait xyk-pool-trait .xyk-pool-trait-v-1-2.xyk-pool-trait)
(use-trait sip-010-trait .sip-010-trait-ft-standard-v-1-1.sip-010-trait)

;; Error constants
(define-constant ERR_NOT_AUTHORIZED (err u1001))
(define-constant ERR_INVALID_AMOUNT (err u1002))
(define-constant ERR_INVALID_PRINCIPAL (err u1003))
(define-constant ERR_ALREADY_ADMIN (err u1004))
(define-constant ERR_ADMIN_LIMIT_REACHED (err u1005))
(define-constant ERR_ADMIN_NOT_IN_LIST (err u1006))
(define-constant ERR_CANNOT_REMOVE_CONTRACT_DEPLOYER (err u1007))
(define-constant ERR_NO_POOL_DATA (err u1008))
(define-constant ERR_POOL_NOT_CREATED (err u1009))
(define-constant ERR_POOL_DISABLED (err u1010))
(define-constant ERR_POOL_ALREADY_CREATED (err u1011))
(define-constant ERR_INVALID_POOL (err u1012))
(define-constant ERR_INVALID_POOL_URI (err u1013))
(define-constant ERR_INVALID_POOL_SYMBOL (err u1014))
(define-constant ERR_INVALID_POOL_NAME (err u1015))
(define-constant ERR_MATCHING_TOKEN_CONTRACTS (err u1016))
(define-constant ERR_INVALID_X_TOKEN (err u1017))
(define-constant ERR_INVALID_Y_TOKEN (err u1018))
(define-constant ERR_MINIMUM_X_AMOUNT (err u1019))
(define-constant ERR_MINIMUM_Y_AMOUNT (err u1020))
(define-constant ERR_MINIMUM_LP_AMOUNT (err u1021))
(define-constant ERR_INVALID_FEE (err u1022))
(define-constant ERR_MINIMUM_BURN_AMOUNT (err u1023))
(define-constant ERR_INVALID_MIN_BURNT_SHARES (err u1024))

;; Contract deployer address
(define-constant CONTRACT_DEPLOYER tx-sender)

;; Maximum BPS
(define-constant BPS u10000)

;; Admins list and helper var used to remove admins
(define-data-var admins (list 5 principal) (list tx-sender))
(define-data-var admin-helper principal tx-sender)

;; ID of last created pool
(define-data-var last-pool-id uint u0)

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
    pool-contract: principal
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

;; Get DY
(define-public (get-dy
    (pool-trait <xyk-pool-trait>)
    (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
    (x-amount uint)
    )
    (let (
    ;; Gather all pool data and check if pool is valid
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (pool-validity-check (asserts! (is-valid-pool (get pool-id pool-data) (contract-of pool-trait)) ERR_INVALID_POOL))
    (x-token (get x-token pool-data))
    (y-token (get y-token pool-data))
    (x-balance (get x-balance pool-data))
    (y-balance (get y-balance pool-data))
    (protocol-fee (get x-protocol-fee pool-data))
    (provider-fee (get x-provider-fee pool-data))
    
    ;; Calculate fees and perform AMM calculations
    (x-amount-fees-protocol (/ (* x-amount protocol-fee) BPS))
    (x-amount-fees-provider (/ (* x-amount provider-fee) BPS))
    (x-amount-fees-total (+ x-amount-fees-protocol x-amount-fees-provider))
    (dx (- x-amount x-amount-fees-total))
    (updated-x-balance (+ x-balance dx))
    (dy (/ (* y-balance dx) updated-x-balance))
    )
    (begin
        ;; Assert that pool-status is true and correct token traits are used
        (asserts! (is-eq (get pool-status pool-data) true) ERR_POOL_DISABLED)
        (asserts! (is-eq (contract-of x-token-trait) x-token) ERR_INVALID_X_TOKEN)
        (asserts! (is-eq (contract-of y-token-trait) y-token) ERR_INVALID_Y_TOKEN)
        
        ;; Assert that x-amount is greater than 0
        (asserts! (> x-amount u0) ERR_INVALID_AMOUNT)

        ;; Return number of y tokens the caller would receive
        (ok dy)
    )
    )
)

;; Swap x token for y token via a pool
(define-public (swap-x-for-y
    (pool-trait <xyk-pool-trait>)
    (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
    (x-amount uint) (min-dy uint)
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
    (protocol-fee (get x-protocol-fee pool-data))
    (provider-fee (get x-provider-fee pool-data))
    
    ;; Calculate fees and perform AMM calculations
    (x-amount-fees-protocol (/ (* x-amount protocol-fee) BPS))
    (x-amount-fees-provider (/ (* x-amount provider-fee) BPS))
    (x-amount-fees-total (+ x-amount-fees-protocol x-amount-fees-provider))
    (dx (- x-amount x-amount-fees-total))
    (updated-x-balance (+ x-balance dx))
    (dy (/ (* y-balance dx) updated-x-balance))
    (updated-y-balance (- y-balance dy))
    (caller tx-sender)
    )
    (begin
        ;; Assert that pool-status is true and correct token traits are used
        (asserts! (is-eq (get pool-status pool-data) true) ERR_POOL_DISABLED)
        (asserts! (is-eq (contract-of x-token-trait) x-token) ERR_INVALID_X_TOKEN)
        (asserts! (is-eq (contract-of y-token-trait) y-token) ERR_INVALID_Y_TOKEN)
        
        ;; Assert that x-amount is greater than 0
        (asserts! (> x-amount u0) ERR_INVALID_AMOUNT)

        ;; Assert that min-dy is greater than 0 and dy is greater than or equal to min-dy
        (asserts! (> min-dy u0) ERR_INVALID_AMOUNT)
        (asserts! (>= dy min-dy) ERR_MINIMUM_Y_AMOUNT)
        
        ;; Transfer dx + x-amount-fees-provider x tokens from caller to pool-contract
        (try! (contract-call? x-token-trait transfer (+ dx x-amount-fees-provider) caller pool-contract none))
        
        ;; Transfer dy y tokens from pool-contract to caller
        (try! (contract-call? pool-trait pool-transfer y-token-trait dy caller))
        
        ;; Transfer x-amount-fees-protocol x tokens from caller to fee-address
        (if (> x-amount-fees-protocol u0)
        (try! (contract-call? x-token-trait transfer x-amount-fees-protocol caller fee-address none))
        false
        )

        ;; Update pool balances
        (try! (contract-call? pool-trait update-pool-balances (+ updated-x-balance x-amount-fees-provider) updated-y-balance))
        
        ;; Print swap data and return number of y tokens the caller received
        (print {
        action: "swap-x-for-y",
        caller: caller,
        data: {
            pool-id: (get pool-id pool-data),
            pool-name: (get pool-name pool-data),
            pool-contract: pool-contract,
            x-token: x-token,
            y-token: y-token,
            x-amount: x-amount,
            x-amount-fees-protocol: x-amount-fees-protocol,
            x-amount-fees-provider: x-amount-fees-provider,
            dy: dy,
            min-dy: min-dy
        }
        })
        (ok dy)
    )
    )
)

;; Create a new pool
(define-public (create-pool 
    (pool-trait <xyk-pool-trait>)
    (x-token-trait <sip-010-trait>) (y-token-trait <sip-010-trait>)
    (x-amount uint) (y-amount uint)
    (burn-amount uint)
    (x-protocol-fee uint) (x-provider-fee uint)
    (y-protocol-fee uint) (y-provider-fee uint)
    (fee-address principal) (uri (string-utf8 256)) (status bool)
    )
    (let (
    ;; Gather all pool data and pool contract
    (pool-data (unwrap! (contract-call? pool-trait get-pool) ERR_NO_POOL_DATA))
    (pool-contract (contract-of pool-trait))
    
    ;; Get pool ID and create pool symbol and name 
    (new-pool-id (+ (var-get last-pool-id) u1))
    (symbol (unwrap! (create-symbol x-token-trait y-token-trait) ERR_INVALID_POOL_SYMBOL))
    (name (concat symbol "-LP"))
    (x-token-contract (contract-of x-token-trait))
    (y-token-contract (contract-of y-token-trait))

    ;; Calculate total shares
    (total-shares (sqrti (* x-amount y-amount)))
    (min-burnt-shares (var-get minimum-burnt-shares))
    (caller tx-sender)
    )
    (begin
        ;; Assert that caller is an admin or public-pool-creation is true
        (asserts! (or (is-some (index-of (var-get admins) caller)) (var-get public-pool-creation)) ERR_NOT_AUTHORIZED)
        
        ;; Assert that pool is not created
        (asserts! (is-eq (get pool-created pool-data) false) ERR_POOL_ALREADY_CREATED)

        ;; Assert that x-token-contract and y-token-contract are not matching
        (asserts! (not (is-eq x-token-contract y-token-contract)) ERR_MATCHING_TOKEN_CONTRACTS)

        ;; Assert that addresses are standard principals
        (asserts! (is-standard x-token-contract) ERR_INVALID_PRINCIPAL)
        (asserts! (is-standard y-token-contract) ERR_INVALID_PRINCIPAL)
        (asserts! (is-standard fee-address) ERR_INVALID_PRINCIPAL)

        ;; Assert that x and y amount is greater than 0
        (asserts! (and (> x-amount u0) (> y-amount u0)) ERR_INVALID_AMOUNT)

        ;; Assert that total shares minted meets minimum total shares required
        (asserts! (>= total-shares (var-get minimum-total-shares)) ERR_MINIMUM_LP_AMOUNT)

        ;; Assert that burn amount meets minimum shares required to burn
        (asserts! (>= burn-amount min-burnt-shares) ERR_MINIMUM_BURN_AMOUNT)

        ;; Assert that total shares is greater than or equal to 0 after subtracting burn amount
        (asserts! (>= (- total-shares burn-amount) u0) ERR_MINIMUM_LP_AMOUNT)

        ;; Assert that length of pool uri, symbol, and name is greater than 0
        (asserts! (> (len uri) u0) ERR_INVALID_POOL_URI)
        (asserts! (> (len symbol) u0) ERR_INVALID_POOL_SYMBOL)
        (asserts! (> (len name) u0) ERR_INVALID_POOL_NAME)

        ;; Assert that fees are less than maximum BPS
        (asserts! (< (+ x-protocol-fee x-provider-fee) BPS) ERR_INVALID_FEE)
        (asserts! (< (+ y-protocol-fee y-provider-fee) BPS) ERR_INVALID_FEE)

        ;; Create pool and set fees
        (try! (contract-call? pool-trait create-pool x-token-contract y-token-contract fee-address caller new-pool-id name symbol uri status))
        (try! (contract-call? pool-trait set-x-fees x-protocol-fee x-provider-fee))
        (try! (contract-call? pool-trait set-y-fees y-protocol-fee y-provider-fee))

        ;; Update ID of last created pool and add pool to pools map
        (var-set last-pool-id new-pool-id)
        (map-set pools new-pool-id {id: new-pool-id, name: name, symbol: symbol, pool-contract: pool-contract})
        
        ;; Transfer x-amount x tokens and y-amount y tokens from caller to pool-contract
        (try! (contract-call? x-token-trait transfer x-amount caller pool-contract none))
        (try! (contract-call? y-token-trait transfer y-amount caller pool-contract none))

        ;; Update pool balances
        (try! (contract-call? pool-trait update-pool-balances x-amount y-amount))

        ;; Mint LP tokens to caller 
        (try! (contract-call? pool-trait pool-mint (- total-shares burn-amount) caller))

        ;; Mint burn amount LP tokens to pool-contract
        (try! (contract-call? pool-trait pool-mint burn-amount pool-contract))

        ;; Print create pool data and return true
        (print {
        action: "create-pool",
        caller: caller,
        data: {
            pool-id: new-pool-id,
            pool-name: name,
            pool-contract: pool-contract,
            x-token: x-token-contract,
            y-token: y-token-contract,
            x-protocol-fee: x-protocol-fee,
            x-provider-fee: x-provider-fee,
            y-protocol-fee: y-protocol-fee,
            y-provider-fee: y-provider-fee,
            x-amount: x-amount,
            y-amount: y-amount,
            burn-amount: burn-amount,
            total-shares: total-shares,
            pool-symbol: symbol,
            pool-uri: uri,
            pool-status: status,
            creation-height: burn-block-height,
            fee-address: fee-address
        }
        })
        (ok true)
    )
    )
)
