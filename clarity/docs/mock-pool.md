
# mock-pool

[`mock-pool.clar`](..\contracts\mocks\mock-pool.clar)

Minimal Mock Pool Contract

This contract provides the bare minimum implementation needed for testing

**Public functions:**

- [`set-revert`](#set-revert)
- [`set-pool-created`](#set-pool-created)
- [`set-active-bin-id-public`](#set-active-bin-id-public)
- [`set-tokens`](#set-tokens)
- [`set-active-bin-id`](#set-active-bin-id)
- [`update-bin-balances`](#update-bin-balances)
- [`pool-mint`](#pool-mint)
- [`pool-burn`](#pool-burn)
- [`pool-transfer`](#pool-transfer)
- [`create-pool`](#create-pool)
- [`transfer`](#transfer)
- [`transfer-memo`](#transfer-memo)
- [`transfer-many`](#transfer-many)
- [`transfer-many-memo`](#transfer-many-memo)
- [`set-pool-uri`](#set-pool-uri)
- [`set-variable-fees-manager`](#set-variable-fees-manager)
- [`set-fee-address`](#set-fee-address)
- [`set-x-fees`](#set-x-fees)
- [`set-y-fees`](#set-y-fees)
- [`set-variable-fees`](#set-variable-fees)
- [`set-variable-fees-cooldown`](#set-variable-fees-cooldown)
- [`set-freeze-variable-fees-manager`](#set-freeze-variable-fees-manager)
- [`set-dynamic-config`](#set-dynamic-config)

**Read-only functions:**

- [`get-name`](#get-name)
- [`get-symbol`](#get-symbol)
- [`get-decimals`](#get-decimals)
- [`get-token-uri`](#get-token-uri)
- [`get-total-supply`](#get-total-supply)
- [`get-overall-supply`](#get-overall-supply)
- [`get-balance`](#get-balance)
- [`get-overall-balance`](#get-overall-balance)
- [`get-pool`](#get-pool)
- [`get-pool-for-swap`](#get-pool-for-swap)
- [`get-pool-for-liquidity`](#get-pool-for-liquidity)
- [`get-active-bin-id`](#get-active-bin-id)
- [`get-bin-balances`](#get-bin-balances)
- [`get-user-bins`](#get-user-bins)

**Private functions:**



**Maps**

- [`balances-at-bin`](#balances-at-bin)
- [`user-balance-at-bin`](#user-balance-at-bin)
- [`user-bins`](#user-bins)

**Variables**

- [`revert`](#revert)
- [`pool-created`](#pool-created)
- [`active-bin-id`](#active-bin-id)
- [`bin-step`](#bin-step)
- [`x-token`](#x-token)
- [`y-token`](#y-token)

**Constants**

- [`ERR_NOT_AUTHORIZED_SIP_013`](#err_not_authorized_sip_013)
- [`ERR_INVALID_AMOUNT_SIP_013`](#err_invalid_amount_sip_013)
- [`ERR_INVALID_PRINCIPAL_SIP_013`](#err_invalid_principal_sip_013)
- [`ERR_NOT_AUTHORIZED`](#err_not_authorized)
- [`ERR_INVALID_AMOUNT`](#err_invalid_amount)
- [`CORE_ADDRESS`](#core_address)


## Functions

### set-revert

[View in file](..\contracts\mocks\mock-pool.clar#L38)

`(define-public (set-revert ((flag bool)) (response bool none))`

Public setters - anyone can call these for testing

<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-revert (flag bool))
  (ok (var-set revert flag)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| flag | bool |

### set-pool-created

[View in file](..\contracts\mocks\mock-pool.clar#L41)

`(define-public (set-pool-created ((created bool)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-pool-created (created bool))
  (ok (var-set pool-created created)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| created | bool |

### set-active-bin-id-public

[View in file](..\contracts\mocks\mock-pool.clar#L44)

`(define-public (set-active-bin-id-public ((id int)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-active-bin-id-public (id int))
  (ok (var-set active-bin-id id)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| id | int |

### set-tokens

[View in file](..\contracts\mocks\mock-pool.clar#L47)

`(define-public (set-tokens ((x-token-addr principal) (y-token-addr principal)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-tokens (x-token-addr principal) (y-token-addr principal))
  (begin
    (var-set x-token x-token-addr)
    (var-set y-token y-token-addr)
    (ok true)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| x-token-addr | principal |
| y-token-addr | principal |

### get-name

[View in file](..\contracts\mocks\mock-pool.clar#L54)

`(define-read-only (get-name () (response (string-ascii 9) none))`

SIP 013 functions - minimal implementations

<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-name)
  (ok "Mock Pool"))
```
</details>




### get-symbol

[View in file](..\contracts\mocks\mock-pool.clar#L57)

`(define-read-only (get-symbol () (response (string-ascii 4) none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-symbol)
  (ok "MOCK"))
```
</details>




### get-decimals

[View in file](..\contracts\mocks\mock-pool.clar#L60)

`(define-read-only (get-decimals ((token-id uint)) (response uint none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-decimals (token-id uint))
  (ok u6))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-id | uint |

### get-token-uri

[View in file](..\contracts\mocks\mock-pool.clar#L63)

`(define-read-only (get-token-uri ((token-id uint)) (response (optional (string-ascii 17)) none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-token-uri (token-id uint))
  (ok (some "https://mock.pool")))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-id | uint |

### get-total-supply

[View in file](..\contracts\mocks\mock-pool.clar#L66)

`(define-read-only (get-total-supply ((token-id uint)) (response uint none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-total-supply (token-id uint))
  (ok (default-to u0 (get bin-shares (map-get? balances-at-bin token-id)))))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-id | uint |

### get-overall-supply

[View in file](..\contracts\mocks\mock-pool.clar#L69)

`(define-read-only (get-overall-supply () (response uint none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-overall-supply)
  (ok (ft-get-supply pool-token)))
```
</details>




### get-balance

[View in file](..\contracts\mocks\mock-pool.clar#L72)

`(define-read-only (get-balance ((token-id uint) (user principal)) (response uint none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-balance (token-id uint) (user principal))
  (ok (default-to u0 (map-get? user-balance-at-bin {id: token-id, user: user}))))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-id | uint |
| user | principal |

### get-overall-balance

[View in file](..\contracts\mocks\mock-pool.clar#L75)

`(define-read-only (get-overall-balance ((user principal)) (response uint none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-overall-balance (user principal))
  (ok (ft-get-balance pool-token user)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| user | principal |

### get-pool

[View in file](..\contracts\mocks\mock-pool.clar#L79)

`(define-read-only (get-pool () (response (tuple (active-bin-id int) (bin-change-count uint) (bin-step uint) (core-address principal) (creation-height uint) (dynamic-config (buff 0)) (fee-address principal) (freeze-variable-fees-manager bool) (initial-price uint) (last-variable-fees-update uint) (pool-created bool) (pool-id uint) (pool-name (string-ascii 9)) (pool-symbol (string-ascii 4)) (pool-token principal) (pool-uri (string-ascii 17)) (variable-fees-cooldown uint) (variable-fees-manager principal) (x-protocol-fee uint) (x-provider-fee uint) (x-token principal) (x-variable-fee uint) (y-protocol-fee uint) (y-provider-fee uint) (y-token principal) (y-variable-fee uint)) uint))`

Core pool functions

<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-pool)
  (begin
    (asserts! (not (var-get revert)) (err u42))
    (ok {
      pool-id: u1,
      pool-name: "Mock Pool",
      pool-symbol: "MOCK",
      pool-uri: "https://mock.pool",
      pool-created: (var-get pool-created),
      creation-height: u1,
      core-address: CORE_ADDRESS,
      variable-fees-manager: tx-sender,
      fee-address: tx-sender,
      x-token: (var-get x-token),
      y-token: (var-get y-token),
      pool-token: (as-contract tx-sender),
      bin-step: (var-get bin-step),
      initial-price: u50000000,
      active-bin-id: (var-get active-bin-id),
      x-protocol-fee: u1000,
      x-provider-fee: u3000,
      x-variable-fee: u0,
      y-protocol-fee: u1000,
      y-provider-fee: u3000,
      y-variable-fee: u0,
      bin-change-count: u0,
      last-variable-fees-update: u0,
      variable-fees-cooldown: u900,
      freeze-variable-fees-manager: false,
      dynamic-config: 0x
    })))
```
</details>




### get-pool-for-swap

[View in file](..\contracts\mocks\mock-pool.clar#L111)

`(define-read-only (get-pool-for-swap ((is-x-for-y bool)) (response (tuple (active-bin-id int) (bin-step uint) (fee-address principal) (initial-price uint) (pool-id uint) (pool-name (string-ascii 9)) (protocol-fee uint) (provider-fee uint) (variable-fee uint) (x-token principal) (y-token principal)) uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-pool-for-swap (is-x-for-y bool))
  (begin
    (asserts! (not (var-get revert)) (err u42))
    (ok {
      pool-id: u1,
      pool-name: "Mock Pool",
      fee-address: tx-sender,
      x-token: (var-get x-token),
      y-token: (var-get y-token),
      bin-step: (var-get bin-step),
      initial-price: u50000000,
      active-bin-id: (var-get active-bin-id),
      protocol-fee: u1000,
      provider-fee: u3000,
      variable-fee: u0
    })))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| is-x-for-y | bool |

### get-pool-for-liquidity

[View in file](..\contracts\mocks\mock-pool.clar#L128)

`(define-read-only (get-pool-for-liquidity () (response (tuple (active-bin-id int) (bin-step uint) (initial-price uint) (pool-id uint) (pool-name (string-ascii 9)) (x-protocol-fee uint) (x-provider-fee uint) (x-token principal) (x-variable-fee uint) (y-protocol-fee uint) (y-provider-fee uint) (y-token principal) (y-variable-fee uint)) uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-pool-for-liquidity)
  (begin
    (asserts! (not (var-get revert)) (err u42))
    (ok {
      pool-id: u1,
      pool-name: "Mock Pool",
      x-token: (var-get x-token),
      y-token: (var-get y-token),
      bin-step: (var-get bin-step),
      initial-price: u50000000,
      active-bin-id: (var-get active-bin-id),
      x-protocol-fee: u1000,
      x-provider-fee: u3000,
      x-variable-fee: u0,
      y-protocol-fee: u1000,
      y-provider-fee: u3000,
      y-variable-fee: u0
    })))
```
</details>




### get-active-bin-id

[View in file](..\contracts\mocks\mock-pool.clar#L147)

`(define-read-only (get-active-bin-id () (response int uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-active-bin-id)
  (begin
    (asserts! (not (var-get revert)) (err u42))
    (ok (var-get active-bin-id))))
```
</details>




### get-bin-balances

[View in file](..\contracts\mocks\mock-pool.clar#L152)

`(define-read-only (get-bin-balances ((id uint)) (response (tuple (bin-shares uint) (x-balance uint) (y-balance uint)) none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-bin-balances (id uint))
  (ok (default-to {x-balance: u0, y-balance: u0, bin-shares: u0} (map-get? balances-at-bin id))))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| id | uint |

### get-user-bins

[View in file](..\contracts\mocks\mock-pool.clar#L155)

`(define-read-only (get-user-bins ((user principal)) (response (list 1001 uint) none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-read-only (get-user-bins (user principal))
  (ok (default-to (list) (map-get? user-bins user))))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| user | principal |

### set-active-bin-id

[View in file](..\contracts\mocks\mock-pool.clar#L159)

`(define-public (set-active-bin-id ((id int)) (response bool uint))`

Core-only functions (kept minimal but functional)

<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-active-bin-id (id int))
  (begin
    (asserts! (is-eq contract-caller CORE_ADDRESS) ERR_NOT_AUTHORIZED)
    (var-set active-bin-id id)
    (ok true)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| id | int |

### update-bin-balances

[View in file](..\contracts\mocks\mock-pool.clar#L165)

`(define-public (update-bin-balances ((bin-id uint) (x-balance uint) (y-balance uint)) (response bool uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (update-bin-balances (bin-id uint) (x-balance uint) (y-balance uint))
  (begin
    (asserts! (is-eq contract-caller CORE_ADDRESS) ERR_NOT_AUTHORIZED)
    (map-set balances-at-bin bin-id {x-balance: x-balance, y-balance: y-balance, bin-shares: (default-to u0 (get bin-shares (map-get? balances-at-bin bin-id)))})
    (ok true)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| bin-id | uint |
| x-balance | uint |
| y-balance | uint |

### pool-mint

[View in file](..\contracts\mocks\mock-pool.clar#L171)

`(define-public (pool-mint ((id uint) (amount uint) (user principal)) (response bool uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (pool-mint (id uint) (amount uint) (user principal))
  (begin
    (asserts! (is-eq contract-caller CORE_ADDRESS) ERR_NOT_AUTHORIZED)
    (try! (ft-mint? pool-token amount user))
    (map-set user-balance-at-bin {id: id, user: user} (+ (default-to u0 (map-get? user-balance-at-bin {id: id, user: user})) amount))
    (map-set balances-at-bin id (merge (default-to {x-balance: u0, y-balance: u0, bin-shares: u0} (map-get? balances-at-bin id)) {bin-shares: (+ (default-to u0 (get bin-shares (map-get? balances-at-bin id))) amount)}))
    (ok true)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| id | uint |
| amount | uint |
| user | principal |

### pool-burn

[View in file](..\contracts\mocks\mock-pool.clar#L179)

`(define-public (pool-burn ((id uint) (amount uint) (user principal)) (response bool uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (pool-burn (id uint) (amount uint) (user principal))
  (begin
    (asserts! (is-eq contract-caller CORE_ADDRESS) ERR_NOT_AUTHORIZED)
    (try! (ft-burn? pool-token amount user))
    (map-set user-balance-at-bin {id: id, user: user} (- (default-to u0 (map-get? user-balance-at-bin {id: id, user: user})) amount))
    (map-set balances-at-bin id (merge (default-to {x-balance: u0, y-balance: u0, bin-shares: u0} (map-get? balances-at-bin id)) {bin-shares: (- (default-to u0 (get bin-shares (map-get? balances-at-bin id))) amount)}))
    (ok true)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| id | uint |
| amount | uint |
| user | principal |

### pool-transfer

[View in file](..\contracts\mocks\mock-pool.clar#L187)

`(define-public (pool-transfer ((token-trait trait_reference) (amount uint) (recipient principal)) (response bool uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (pool-transfer (token-trait <sip-010-trait>) (amount uint) (recipient principal))
  (begin
    (asserts! (is-eq contract-caller CORE_ADDRESS) ERR_NOT_AUTHORIZED)
    (as-contract (contract-call? token-trait transfer amount tx-sender recipient none))))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-trait | trait_reference |
| amount | uint |
| recipient | principal |

### create-pool

[View in file](..\contracts\mocks\mock-pool.clar#L192)

`(define-public (create-pool ((x-token-contract principal) (y-token-contract principal) (variable-fees-mgr principal) (fee-addr principal) (core-caller principal) (active-bin int) (step uint) (price uint) (id uint) (name (string-ascii 32)) (symbol (string-ascii 32)) (uri (string-ascii 256))) (response bool uint))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (create-pool
    (x-token-contract principal) (y-token-contract principal)
    (variable-fees-mgr principal) (fee-addr principal) (core-caller principal)
    (active-bin int) (step uint) (price uint)
    (id uint) (name (string-ascii 32)) (symbol (string-ascii 32)) (uri (string-ascii 256)))
  (begin
    (asserts! (is-eq contract-caller CORE_ADDRESS) ERR_NOT_AUTHORIZED)
    (var-set pool-created true)
    (var-set x-token x-token-contract)
    (var-set y-token y-token-contract)
    (var-set active-bin-id active-bin)
    (var-set bin-step step)
    (ok true)))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| x-token-contract | principal |
| y-token-contract | principal |
| variable-fees-mgr | principal |
| fee-addr | principal |
| core-caller | principal |
| active-bin | int |
| step | uint |
| price | uint |
| id | uint |
| name | (string-ascii 32) |
| symbol | (string-ascii 32) |
| uri | (string-ascii 256) |

### transfer

[View in file](..\contracts\mocks\mock-pool.clar#L207)

`(define-public (transfer ((token-id uint) (amount uint) (sender principal) (recipient principal)) (response bool none))`

Stub functions for SIP 013 compliance

<details>
  <summary>Source code:</summary>

```clarity
(define-public (transfer (token-id uint) (amount uint) (sender principal) (recipient principal))
  (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-id | uint |
| amount | uint |
| sender | principal |
| recipient | principal |

### transfer-memo

[View in file](..\contracts\mocks\mock-pool.clar#L210)

`(define-public (transfer-memo ((token-id uint) (amount uint) (sender principal) (recipient principal) (memo (buff 34))) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (transfer-memo (token-id uint) (amount uint) (sender principal) (recipient principal) (memo (buff 34)))
  (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| token-id | uint |
| amount | uint |
| sender | principal |
| recipient | principal |
| memo | (buff 34) |

### transfer-many

[View in file](..\contracts\mocks\mock-pool.clar#L213)

`(define-public (transfer-many ((transfers (list 200 (tuple (amount uint) (recipient principal) (sender principal) (token-id uint))))) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (transfer-many (transfers (list 200 {token-id: uint, amount: uint, sender: principal, recipient: principal})))
  (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| transfers | (list 200 (tuple (amount uint) (recipient principal) (sender principal) (token-id uint))) |

### transfer-many-memo

[View in file](..\contracts\mocks\mock-pool.clar#L216)

`(define-public (transfer-many-memo ((transfers (list 200 (tuple (amount uint) (memo (buff 34)) (recipient principal) (sender principal) (token-id uint))))) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (transfer-many-memo (transfers (list 200 {token-id: uint, amount: uint, sender: principal, recipient: principal, memo: (buff 34)})))
  (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| transfers | (list 200 (tuple (amount uint) (memo (buff 34)) (recipient principal) (sender principal) (token-id uint))) |

### set-pool-uri

[View in file](..\contracts\mocks\mock-pool.clar#L220)

`(define-public (set-pool-uri ((uri (string-ascii 256))) (response bool none))`

Stub functions for other core functions

<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-pool-uri (uri (string-ascii 256))) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| uri | (string-ascii 256) |

### set-variable-fees-manager

[View in file](..\contracts\mocks\mock-pool.clar#L221)

`(define-public (set-variable-fees-manager ((manager principal)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-variable-fees-manager (manager principal)) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| manager | principal |

### set-fee-address

[View in file](..\contracts\mocks\mock-pool.clar#L222)

`(define-public (set-fee-address ((address principal)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-fee-address (address principal)) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| address | principal |

### set-x-fees

[View in file](..\contracts\mocks\mock-pool.clar#L223)

`(define-public (set-x-fees ((protocol-fee uint) (provider-fee uint)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-x-fees (protocol-fee uint) (provider-fee uint)) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| protocol-fee | uint |
| provider-fee | uint |

### set-y-fees

[View in file](..\contracts\mocks\mock-pool.clar#L224)

`(define-public (set-y-fees ((protocol-fee uint) (provider-fee uint)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-y-fees (protocol-fee uint) (provider-fee uint)) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| protocol-fee | uint |
| provider-fee | uint |

### set-variable-fees

[View in file](..\contracts\mocks\mock-pool.clar#L225)

`(define-public (set-variable-fees ((x-fee uint) (y-fee uint)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-variable-fees (x-fee uint) (y-fee uint)) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| x-fee | uint |
| y-fee | uint |

### set-variable-fees-cooldown

[View in file](..\contracts\mocks\mock-pool.clar#L226)

`(define-public (set-variable-fees-cooldown ((cooldown uint)) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-variable-fees-cooldown (cooldown uint)) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| cooldown | uint |

### set-freeze-variable-fees-manager

[View in file](..\contracts\mocks\mock-pool.clar#L227)

`(define-public (set-freeze-variable-fees-manager () (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-freeze-variable-fees-manager) (ok true))
```
</details>




### set-dynamic-config

[View in file](..\contracts\mocks\mock-pool.clar#L228)

`(define-public (set-dynamic-config ((config (buff 4096))) (response bool none))`



<details>
  <summary>Source code:</summary>

```clarity
(define-public (set-dynamic-config (config (buff 4096))) (ok true))
```
</details>


**Parameters:**

| Name | Type | 
| --- | --- | 
| config | (buff 4096) |

## Maps

### balances-at-bin

Minimal maps

```clarity
(define-map balances-at-bin uint {x-balance: uint, y-balance: uint, bin-shares: uint})
```

[View in file](..\contracts\mocks\mock-pool.clar#L33)

### user-balance-at-bin



```clarity
(define-map user-balance-at-bin {id: uint, user: principal} uint)
```

[View in file](..\contracts\mocks\mock-pool.clar#L34)

### user-bins



```clarity
(define-map user-bins principal (list 1001 uint))
```

[View in file](..\contracts\mocks\mock-pool.clar#L35)

## Variables

### revert

bool

Minimal state variables - settable by anyone for testing

```clarity
(define-data-var revert bool false)
```

[View in file](..\contracts\mocks\mock-pool.clar#L25)

### pool-created

bool



```clarity
(define-data-var pool-created bool false)
```

[View in file](..\contracts\mocks\mock-pool.clar#L26)

### active-bin-id

int



```clarity
(define-data-var active-bin-id int 0)
```

[View in file](..\contracts\mocks\mock-pool.clar#L27)

### bin-step

uint



```clarity
(define-data-var bin-step uint u25)
```

[View in file](..\contracts\mocks\mock-pool.clar#L28)

### x-token

principal



```clarity
(define-data-var x-token principal tx-sender)
```

[View in file](..\contracts\mocks\mock-pool.clar#L29)

### y-token

principal



```clarity
(define-data-var y-token principal tx-sender)
```

[View in file](..\contracts\mocks\mock-pool.clar#L30)

## Constants

### ERR_NOT_AUTHORIZED_SIP_013



Minimal error constants

```clarity
(define-constant ERR_NOT_AUTHORIZED_SIP_013 (err u4))
```

[View in file](..\contracts\mocks\mock-pool.clar#L15)

### ERR_INVALID_AMOUNT_SIP_013





```clarity
(define-constant ERR_INVALID_AMOUNT_SIP_013 (err u1))
```

[View in file](..\contracts\mocks\mock-pool.clar#L16)

### ERR_INVALID_PRINCIPAL_SIP_013





```clarity
(define-constant ERR_INVALID_PRINCIPAL_SIP_013 (err u5))
```

[View in file](..\contracts\mocks\mock-pool.clar#L17)

### ERR_NOT_AUTHORIZED





```clarity
(define-constant ERR_NOT_AUTHORIZED (err u3001))
```

[View in file](..\contracts\mocks\mock-pool.clar#L18)

### ERR_INVALID_AMOUNT





```clarity
(define-constant ERR_INVALID_AMOUNT (err u3002))
```

[View in file](..\contracts\mocks\mock-pool.clar#L19)

### CORE_ADDRESS



Core address

```clarity
(define-constant CORE_ADDRESS .dlmm-core-v-1-1)
```

[View in file](..\contracts\mocks\mock-pool.clar#L22)
  