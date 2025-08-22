;; dlmm-staking-sbtc-usdc-v-1-1

;; Implement DLMM staking trait
(impl-trait .dlmm-staking-trait-v-1-1.dlmm-staking-trait)

;; Error constants
(define-constant ERR_NOT_AUTHORIZED (err u4001))
(define-constant ERR_INVALID_AMOUNT (err u4002))
(define-constant ERR_INVALID_PRINCIPAL (err u4003))
(define-constant ERR_ALREADY_ADMIN (err u4004))
(define-constant ERR_ADMIN_LIMIT_REACHED (err u4005))
(define-constant ERR_ADMIN_NOT_IN_LIST (err u4006))
(define-constant ERR_CANNOT_REMOVE_CONTRACT_DEPLOYER (err u4007))
(define-constant ERR_STAKING_DISABLED (err u4008))
(define-constant ERR_EARLY_UNSTAKE_DISABLED (err u4009))
(define-constant ERR_TOKEN_TRANSFER_FAILED (err u4010))
(define-constant ERR_INVALID_MIN_STAKING_DURATION (err u4011))
(define-constant ERR_MINIMUM_STAKING_DURATION_HASNT_PASSED (err u4012))
(define-constant ERR_MINIMUM_STAKING_DURATION_PASSED (err u4013))
(define-constant ERR_BINS_STAKED_OVERFLOW (err u4014))
(define-constant ERR_NO_USER_DATA (err u4015))
(define-constant ERR_NO_USER_LP_STAKED_AT_BIN_DATA (err u4016))
(define-constant ERR_NO_ACTIVE_BIN_DATA (err u4017))
(define-constant ERR_NO_LP_TO_UNSTAKE (err u4018))
(define-constant ERR_NO_EARLY_LP_TO_UNSTAKE (err u4019))
(define-constant ERR_INVALID_FEE (err u4020))

;; Contract deployer address
(define-constant CONTRACT_DEPLOYER tx-sender)

;; Number of bins per pool and center bin ID as unsigned ints
(define-constant NUM_OF_BINS u1001)
(define-constant CENTER_BIN_ID (/ NUM_OF_BINS u2))

;; Minimum and maximum bin IDs as signed ints
(define-constant MIN_BIN_ID -500)
(define-constant MAX_BIN_ID 500)

;; Maximum BPS
(define-constant FEE_SCALE_BPS u10000)
(define-constant REWARD_SCALE_BPS u1000000)

;; Admins list and helper var used to remove admins
(define-data-var admins (list 5 principal) (list tx-sender))
(define-data-var admin-helper principal tx-sender)

;; Helper value used for removing a bin-id from the bins-staked list
(define-data-var helper-value uint u0)

;; Staking and early unstake statuses
(define-data-var staking-status bool true)
(define-data-var early-unstake-status bool true)

;; Fee address and fee for early unstake
(define-data-var early-unstake-fee-address principal tx-sender)
(define-data-var early-unstake-fee uint u50)

;; Minimum staking duration in blocks
(define-data-var minimum-staking-duration uint u1)

;; Total amount of LP tokens staked
(define-data-var total-lp-staked uint u0)

;; Reward emitted per block
(define-data-var reward-per-block uint u0)

;; Fee applied to rewards per bin distance
(define-data-var bin-distance-fee uint u0)

;; Global cumulative reward-index
(define-data-var reward-index uint u0)

;; Last block height the reward-index was updated
(define-data-var last-reward-index-update uint u0)

;; Define user-data map
(define-map user-data principal {
  bins-staked: (list 1001 uint),
  lp-staked: uint,
  reward-bin-id: int,
  reward-index: uint,
  last-stake-height: uint
})

;; Define user-lp-staked-at-bin map
(define-map user-lp-staked-at-bin {user: principal, bin-id: uint} uint)

;; Get admins list
(define-read-only (get-admins)
  (ok (var-get admins))
)

;; Get admin helper var
(define-read-only (get-admin-helper)
  (ok (var-get admin-helper))
)

;; Get helper value var
(define-read-only (get-helper-value)
  (ok (var-get helper-value))
)

;; Get staking status
(define-read-only (get-staking-status)
  (ok (var-get staking-status))
)

;; Get early unstake status
(define-read-only (get-early-unstake-status)
  (ok (var-get early-unstake-status))
)

;; Get early unstake fee address
(define-read-only (get-early-unstake-fee-address)
  (ok (var-get early-unstake-fee-address))
)

;; Get early unstake fee
(define-read-only (get-early-unstake-fee)
  (ok (var-get early-unstake-fee))
)

;; Get total LP staked
(define-read-only (get-total-lp-staked)
  (ok (var-get total-lp-staked))
)

;; Get reward emitted per block
(define-read-only (get-reward-per-block)
  (ok (var-get reward-per-block))
)

;; Get bin distance fee
(define-read-only (get-bin-distance-fee)
  (ok (var-get bin-distance-fee))
)

;; Get reward index
(define-read-only (get-reward-index)
  (ok (var-get reward-index))
)

;; Get last reward index update
(define-read-only (get-last-reward-index-update)
  (ok (var-get last-reward-index-update))
)

;; Get user data
(define-read-only (get-user (user principal))
  (ok (map-get? user-data user))
)

;; Get LP tokens staked by a user at a bin
(define-read-only (get-user-lp-staked-at-bin (user principal) (bin-id uint))
  (ok (map-get? user-lp-staked-at-bin {user: user, bin-id: bin-id}))
)

;; Get reward bin ID for a user
(define-read-only (get-reward-bin-id (user principal))
  (let (
    (current-user-data (unwrap! (map-get? user-data user) ERR_NO_USER_DATA))
    (current-user-bins-staked (get bins-staked current-user-data))
    (bins-staked-check (asserts! (> (len current-user-bins-staked) u0) (ok 0)))
    (weight-data (fold fold-calculate-bin-weights current-user-bins-staked {total-bin-weight: u0, total-lp-weight: u0, user: user}))
    (total-bin-weight (get total-bin-weight weight-data))
    (total-lp-weight (get total-lp-weight weight-data))
    (reward-bin-id (if (> total-lp-weight u0)
                       (/ (+ total-bin-weight (/ total-lp-weight u2)) total-lp-weight)
                       u0))
    (signed-reward-bin-id (- (to-int reward-bin-id) (to-int CENTER_BIN_ID)))
  )
    ;; Return reward-bin-id as signed int
    (ok (if (< signed-reward-bin-id MIN_BIN_ID)
        MIN_BIN_ID
        (if (> signed-reward-bin-id MAX_BIN_ID) MAX_BIN_ID signed-reward-bin-id)))
  )
)

;; Get the updated reward index
(define-read-only (get-updated-reward-index)
  (let (
    (current-total-lp-staked (var-get total-lp-staked))
    (current-reward-index (var-get reward-index))
    (current-last-reward-index-update (var-get last-reward-index-update))
  )
    ;; Get updated reward-index if current-total-lp-staked is greater than 0 and stacks-block-height is greater than current-last-reward-index-update
    (if (and (> current-total-lp-staked u0) (> stacks-block-height current-last-reward-index-update))
      (let (
        (blocks-since-last-update (- stacks-block-height current-last-reward-index-update))
        (rewards-to-distribute (* (var-get reward-per-block) blocks-since-last-update))
        (reward-index-delta (/ (* rewards-to-distribute REWARD_SCALE_BPS) current-total-lp-staked))
      )
        (ok (+ current-reward-index reward-index-delta))
      )
      (ok current-reward-index)
    )
  )
)

;; Get unclaimed rewards for a user
(define-read-only (get-unclaimed-rewards (user principal))
  (let (
    (current-user-data (unwrap! (map-get? user-data user) ERR_NO_USER_DATA))
    (reward-index-delta (- (unwrap-panic (get-updated-reward-index)) (get reward-index current-user-data)))
    (active-bin-id (unwrap! (contract-call? .dlmm-pool-sbtc-usdc-v-1-1 get-active-bin-id) ERR_NO_ACTIVE_BIN_DATA))
    (bin-distance (abs-int (- active-bin-id (get reward-bin-id current-user-data))))
    (unclaimed-rewards (/ (* (get lp-staked current-user-data) reward-index-delta) REWARD_SCALE_BPS))
    (unclaimed-rewards-distance-fee (/ (* unclaimed-rewards (* bin-distance (var-get bin-distance-fee))) FEE_SCALE_BPS))
  )
    ;; Return unclaimed-rewards after subtracting unclaimed-rewards-distance-fee
    (ok (if (> unclaimed-rewards unclaimed-rewards-distance-fee)
            (- unclaimed-rewards unclaimed-rewards-distance-fee)
            u0))
  )
)

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

;; Enable or disable staking
(define-public (set-staking-status (status bool))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)

      ;; Set staking-status to status
      (var-set staking-status status)

      ;; Print function data and return true
      (print {action: "set-staking-status", caller: caller, data: {status: status}})
      (ok true)
    )
  )
)

;; Enable or disable early unstaking
(define-public (set-early-unstake-status (status bool))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)

      ;; Set early-unstake-status to status
      (var-set early-unstake-status status)

      ;; Print function data and return true
      (print {action: "set-early-unstake-status", caller: caller, data: {status: status}})
      (ok true)
    )
  )
)

;; Set early unstake fee address
(define-public (set-early-unstake-fee-address (address principal))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and address is standard principal
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (is-standard address) ERR_INVALID_PRINCIPAL)

      ;; Set early-unstake-fee-address to address
      (var-set early-unstake-fee-address address)

      ;; Print function data and return true
      (print {action: "set-early-unstake-fee-address", caller: caller, data: {address: address}})
      (ok true)
    )
  )
)

;; Set early unstake fee
(define-public (set-early-unstake-fee (fee uint))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and fee is less than maximum FEE_SCALE_BPS
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (< fee FEE_SCALE_BPS) ERR_INVALID_FEE)

      ;; Set early-unstake-fee to fee
      (var-set early-unstake-fee fee)

      ;; Print function data and return true
      (print {action: "set-early-unstake-fee", caller: caller, data: {fee: fee}})
      (ok true)
    )
  )
)

;; Set the minimum staking duration in blocks
(define-public (set-minimum-staking-duration (duration uint))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and duration is greater than 0
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (> duration u0) ERR_INVALID_MIN_STAKING_DURATION)

      ;; Set minimum-staking-duration to duration
      (var-set minimum-staking-duration duration)

      ;; Print function data and return true
      (print {action: "set-minimum-staking-duration", caller: caller, data: {duration: duration}})
      (ok true)
    )
  )
)

;; Set reward emitted per block
(define-public (set-reward-per-block (reward uint))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      
      ;; Set reward-per-block to reward
      (var-set reward-per-block reward)
      
      ;; Print function data and return true
      (print {action: "set-reward-per-block", caller: caller, data: {reward: reward}})
      (ok true)
    )
  )
)

;; Set bin distance fee
(define-public (set-bin-distance-fee (fee uint))
  (let (
    (caller tx-sender)
  )
    (begin
      ;; Assert caller is an admin and fee is less than maximum FEE_SCALE_BPS
      (asserts! (is-some (index-of (var-get admins) caller)) ERR_NOT_AUTHORIZED)
      (asserts! (< fee FEE_SCALE_BPS) ERR_INVALID_FEE)

      ;; Set bin-distance-fee to fee
      (var-set bin-distance-fee fee)

      ;; Print function data and return true
      (print {action: "set-bin-distance-fee", caller: caller, data: {fee: fee}})
      (ok true)
    )
  )
)

;; Stake LP tokens for a bin
(define-public (stake-lp-tokens (bin-id int) (amount uint))
  (let (
    (caller tx-sender)
    (unsigned-bin-id (to-uint (+ bin-id (to-int CENTER_BIN_ID))))
    (current-user-data (map-get? user-data caller))
    (current-user-lp-staked-at-bin (default-to u0 (map-get? user-lp-staked-at-bin {user: caller, bin-id: unsigned-bin-id})))
    (current-user-bins-staked (default-to (list ) (get bins-staked current-user-data)))
    (updated-user-bins-staked (if (is-none (index-of current-user-bins-staked unsigned-bin-id))
                                  (unwrap! (as-max-len? (concat current-user-bins-staked (list unsigned-bin-id)) u1001) ERR_BINS_STAKED_OVERFLOW)
                                  current-user-bins-staked))
    (updated-user-lp-staked (+ (default-to u0 (get lp-staked current-user-data)) amount))
    (updated-total-lp-staked (+ (var-get total-lp-staked) amount))
  )
    (begin
      ;; Assert staking-status is true and amount is greater than 0
      (asserts! (var-get staking-status) ERR_STAKING_DISABLED)
      (asserts! (> amount u0) ERR_INVALID_AMOUNT)

      ;; Update reward-index
      (unwrap-panic (update-reward-index))

      ;; Claim any rewards
      (if (is-some current-user-data)
          (try! (claim-rewards))
          false)

      ;; Update total LP staked
      (var-set total-lp-staked updated-total-lp-staked)

      ;; Update reward-index now that total-lp-staked is updated
      (unwrap-panic (update-reward-index))

      ;; Update user-data mapping
      (map-set user-data caller {
        bins-staked: updated-user-bins-staked,
        lp-staked: updated-user-lp-staked,
        reward-bin-id: (default-to 0 (get reward-bin-id current-user-data)),
        reward-index: (var-get reward-index),
        last-stake-height: stacks-block-height
      })

      ;; Update user-lp-staked-at-bin mapping
      (map-set user-lp-staked-at-bin {user: caller, bin-id: unsigned-bin-id} (+ current-user-lp-staked-at-bin amount))

      ;; Update reward bin ID for user
      (try! (update-reward-bin-id caller))

      ;; Transfer amount LP tokens from caller to contract
      (try! (transfer-lp-token unsigned-bin-id amount caller (as-contract tx-sender)))

      ;; Print function data and return true
      (print {
        action: "stake-lp-tokens",
        caller: caller,
        data: {
          bin-id: bin-id,
          amount: amount,
          user-bins-staked: updated-user-bins-staked,
          user-lp-staked: updated-user-lp-staked,
          total-lp-staked: updated-total-lp-staked
        }
      })
      (ok true)
    )
  )
)

;; Unstake LP tokens for a bin
(define-public (unstake-lp-tokens (bin-id int))
  (let (
    (caller tx-sender)
    (unsigned-bin-id (to-uint (+ bin-id (to-int CENTER_BIN_ID))))
    (current-user-data (unwrap! (map-get? user-data caller) ERR_NO_USER_DATA))
    (lp-to-unstake (unwrap! (map-get? user-lp-staked-at-bin {user: caller, bin-id: unsigned-bin-id}) ERR_NO_USER_LP_STAKED_AT_BIN_DATA))
    (helper-value-unsigned-bin-id (var-set helper-value unsigned-bin-id))
    (updated-user-bins-staked (filter filter-values-eq-helper-value (get bins-staked current-user-data)))
    (updated-user-lp-staked (- (get lp-staked current-user-data) lp-to-unstake))
    (updated-total-lp-staked (- (var-get total-lp-staked) lp-to-unstake))
  )
    (begin
      ;; Assert lp-to-unstake is greater than 0 and minimum staking duration has passed
      (asserts! (> lp-to-unstake u0) ERR_NO_LP_TO_UNSTAKE)
      (asserts! (>= (- stacks-block-height (get last-stake-height current-user-data)) (var-get minimum-staking-duration)) ERR_MINIMUM_STAKING_DURATION_HASNT_PASSED)

      ;; Update reward-index
      (unwrap-panic (update-reward-index))
      
      ;; Claim any rewards
      (try! (claim-rewards))

      ;; Update total LP staked
      (var-set total-lp-staked updated-total-lp-staked)

      ;; Update reward-index now that total-lp-staked is updated
      (unwrap-panic (update-reward-index))

      ;; Update user-data mapping
      (map-set user-data caller (merge current-user-data {
        bins-staked: updated-user-bins-staked,
        lp-staked: updated-user-lp-staked,
        reward-index: (var-get reward-index)
      }))

      ;; Delete entry in user-lp-staked-at-bin mapping
      (map-delete user-lp-staked-at-bin {user: caller, bin-id: unsigned-bin-id})

      ;; Update reward bin ID for user
      (try! (update-reward-bin-id caller))

      ;; Transfer lp-to-unstake LP tokens from contract to caller
      (try! (as-contract (transfer-lp-token unsigned-bin-id lp-to-unstake tx-sender caller)))

      ;; Print function data and return true
      (print {
        action: "unstake-lp-tokens",
        caller: caller,
        data: {
          bin-id: bin-id,
          lp-to-unstake: lp-to-unstake,
          user-bins-staked: updated-user-bins-staked,
          user-lp-staked: updated-user-lp-staked,
          total-lp-staked: updated-total-lp-staked
        }
      })
      (ok true)
    )
  )
)

;; Early unstake LP tokens for a bin
(define-public (early-unstake-lp-tokens (bin-id int))
  (let (
    (caller tx-sender)
    (unsigned-bin-id (to-uint (+ bin-id (to-int CENTER_BIN_ID))))
    (current-user-data (unwrap! (map-get? user-data caller) ERR_NO_USER_DATA))
    (lp-to-unstake (unwrap! (map-get? user-lp-staked-at-bin {user: caller, bin-id: unsigned-bin-id}) ERR_NO_USER_LP_STAKED_AT_BIN_DATA))
    (lp-to-unstake-fees (/ (* lp-to-unstake (var-get early-unstake-fee)) FEE_SCALE_BPS))
    (lp-to-unstake-user (- lp-to-unstake lp-to-unstake-fees))
    (helper-value-unsigned-bin-id (var-set helper-value unsigned-bin-id))
    (updated-user-bins-staked (filter filter-values-eq-helper-value (get bins-staked current-user-data)))
    (updated-user-lp-staked (- (get lp-staked current-user-data) lp-to-unstake))
    (updated-total-lp-staked (- (var-get total-lp-staked) lp-to-unstake))
  )
    (begin
      ;; Assert early-unstake-status is true
      (asserts! (var-get early-unstake-status) ERR_EARLY_UNSTAKE_DISABLED)

      ;; Assert lp-to-unstake is greater than 0 and minimum staking duration hasn't passed
      (asserts! (> lp-to-unstake u0) ERR_NO_EARLY_LP_TO_UNSTAKE)
      (asserts! (< (- stacks-block-height (get last-stake-height current-user-data)) (var-get minimum-staking-duration)) ERR_MINIMUM_STAKING_DURATION_PASSED)

      ;; Update reward-index
      (unwrap-panic (update-reward-index))
      
      ;; Claim any rewards
      (try! (claim-rewards))

      ;; Update total LP staked
      (var-set total-lp-staked updated-total-lp-staked)

      ;; Update reward-index now that total-lp-staked is updated
      (unwrap-panic (update-reward-index))

      ;; Update user-data mapping
      (map-set user-data caller (merge current-user-data {
        bins-staked: updated-user-bins-staked,
        lp-staked: updated-user-lp-staked,
        reward-index: (var-get reward-index)
      }))

      ;; Delete entry in user-lp-staked-at-bin mapping
      (map-delete user-lp-staked-at-bin {user: caller, bin-id: unsigned-bin-id})

      ;; Update reward bin ID for user
      (try! (update-reward-bin-id caller))

      ;; Transfer lp-to-unstake-user LP tokens from contract to caller
      (try! (as-contract (transfer-lp-token unsigned-bin-id lp-to-unstake-user tx-sender caller)))

      ;; Transfer lp-to-unstake-fees LP tokens from contract to early-unstake-fee-address
      (if (> lp-to-unstake-fees u0)
        (try! (as-contract (transfer-lp-token unsigned-bin-id lp-to-unstake-fees tx-sender (var-get early-unstake-fee-address))))
        false)

      ;; Print function data and return true
      (print {
        action: "early-unstake-lp-tokens",
        caller: caller,
        data: {
          bin-id: bin-id,
          lp-to-unstake: lp-to-unstake,
          user-bins-staked: updated-user-bins-staked,
          user-lp-staked: updated-user-lp-staked,
          total-lp-staked: updated-total-lp-staked
        }
      })
      (ok true)
    )
  )
)

;; Claim any unclaimed rewards
(define-public (claim-rewards)
  (let (
    (caller tx-sender)
    (current-user-data (unwrap! (map-get? user-data caller) ERR_NO_USER_DATA))
    (unclaimed-rewards (try! (get-unclaimed-rewards caller)))
  )
    ;; Claim rewards if unclaimed-rewards is greater than 0
    (if (> unclaimed-rewards u0)
      (begin
        ;; Update reward-index
        (unwrap-panic (update-reward-index))

        ;; Transfer unclaimed-rewards rewards token from contract to caller
        (try! (as-contract (transfer-reward-token unclaimed-rewards tx-sender caller)))
        
        ;; Update user-data mapping
        (map-set user-data caller (merge current-user-data {
          reward-index: (var-get reward-index)
        }))

        ;; Print function data and return true
        (print {action: "claim-rewards", caller: caller, data: {unclaimed-rewards: unclaimed-rewards}})
        (ok true)
      )
      (ok true))
  )
)

;; Update global reward index
(define-public (update-reward-index)
  (let (
    (updated-reward-index (unwrap-panic (get-updated-reward-index)))
    (caller tx-sender)
  )
    ;; Update reward index if stacks-block-height is greater than last-reward-index-update
    (if (> stacks-block-height (var-get last-reward-index-update))
        (begin
          ;; Set reward-index to updated-reward-index
          (var-set reward-index updated-reward-index)

          ;; Set last-reward-index-update to stacks-block-height
          (var-set last-reward-index-update stacks-block-height)
          
          ;; Print function data and return true
          (print {action: "update-reward-index", caller: caller, data: {updated-reward-index: updated-reward-index}})
          (ok true)
        )
        (ok true))
  )
)

;; Update reward bin ID for a user
(define-private (update-reward-bin-id (user principal))
  (let (
    (current-user-data (unwrap! (map-get? user-data user) ERR_NO_USER_DATA))
    (updated-reward-bin-id (try! (get-reward-bin-id user)))
    (caller tx-sender)
  )
    (begin
      ;; Update user-data mapping
      (map-set user-data user (merge current-user-data {
        reward-bin-id: updated-reward-bin-id
      }))

      ;; Print function data and return true
      (print {action: "update-reward-bin-id", caller: caller, data: {user: user, updated-reward-bin-id: updated-reward-bin-id}})
      (ok true)
    )
  )
)

;; Helper function for removing an admin
(define-private (admin-not-removable (admin principal))
  (not (is-eq admin (var-get admin-helper)))
)

;; Filter function for removing a bin-id from the bins-staked list
(define-private (filter-values-eq-helper-value (value uint))
  (not (is-eq value (var-get helper-value)))
)

;; Get absolute value of a signed int as uint
(define-private (abs-int (value int))
  (to-uint (if (>= value 0) value (- value)))
)

;; Fold function to calculate bin weights
(define-private (fold-calculate-bin-weights (bin-id uint) (weight-data {total-bin-weight: uint, total-lp-weight: uint, user: principal}))
  (let (
    (user (get user weight-data))
    (lp-staked-at-bin (default-to u0 (map-get? user-lp-staked-at-bin {user: user, bin-id: bin-id})))
  )
    (if (> lp-staked-at-bin u0)
        {total-bin-weight: (+ (get total-bin-weight weight-data) (* lp-staked-at-bin bin-id)), total-lp-weight: (+ (get total-lp-weight weight-data) lp-staked-at-bin), user: user}
        weight-data)
  )
)

;; Transfer LP token
(define-private (transfer-lp-token (bin-id uint) (amount uint) (sender principal) (recipient principal))
  (ok (unwrap! (contract-call? .dlmm-pool-sbtc-usdc-v-1-1 transfer
               bin-id amount sender recipient) ERR_TOKEN_TRANSFER_FAILED))
)

;; Transfer reward token
(define-private (transfer-reward-token (amount uint) (sender principal) (recipient principal))
  (ok (unwrap! (contract-call? .token-stx-v-1-1 transfer
               amount sender recipient none) ERR_TOKEN_TRANSFER_FAILED))
)