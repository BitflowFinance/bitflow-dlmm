# Current Test Suite Inventory (as of today)

## Summary

- Total unit / integration tests: 243
- Total fuzz / property-based tests: 5
- Total runnable fuzz targets / property files: 5
- Estimated combined coverage confidence: High

## 1. Regular Tests (Clarinet / unit / integration)

| File | Type | What it tests | # of individual checks |
|------|------|---------------|-------------------------|
| tests/core/swap.test.ts | Unit | DLMM Core swap functions (X-for-Y, Y-for-X, edge cases, error handling) | 16 |
| tests/core/liquidity.test.ts | Unit | DLMM Core liquidity functions (add, withdraw, move, edge cases) | 24 |
| tests/core/fees.test.ts | Unit | Fee management (protocol fees, variable fees, fee claiming, fee bounds) | 30 |
| tests/core/settings.test.ts | Unit | Core contract settings (admin management, bin steps, pool creation, getters) | 32 |
| tests/core/migration.test.ts | Unit | Core migration functions (migration address, cooldown, execution) | 17 |
| tests/routers/liquidity-router.test.ts | Integration | Liquidity router (bulk add/withdraw, multiple bins, edge cases) | 25 |
| tests/routers/swap-router.test.ts | Integration | Swap router (bulk swaps, unfavorable bins, edge cases) | 19 |
| tests/helpers/swap-calculations.test.ts | Unit | Swap calculation helper functions (fee calculation, swap math, edge cases) | 18 |
| tests/helpers/swap-calculations-edge-cases.test.ts | Unit | Edge cases for swap calculations (large values, zero reserves, precision) | 19 |
| tests/helpers/swap-calculations-concrete-example.test.ts | Unit | Concrete examples matching Python pricing.py calculations | 8 |
| tests/helpers/swap-calculations-validation-logic.test.ts | Unit | Validation logic for swap calculations (exploit detection, rounding) | 9 |
| tests/helpers/swap-calculations-validation-test.ts | Unit | Validation test scenarios (pre-capped inputs, float vs integer math) | 6 |
| tests/helpers/swap-calculations-verification.test.ts | Unit | Verification of swap calculation helpers against existing fuzz tests | 9 |
| tests/helpers/multi-bin-quote-estimation.test.ts | Unit | Multi-bin swap estimation (bin discovery, multi-bin calculations) | 11 |

## 2. Fuzz Tests / Invariant Tests

### Clarity-level properties (Rendezvous / similar)

| File | Invariant name | Category | Importance |
|------|----------------|----------|------------|
| fuzz/properties/invariants.ts | checkSwapXForYInvariants | Swap | Critical |
| fuzz/properties/invariants.ts | checkSwapYForXInvariants | Swap | Critical |
| fuzz/properties/invariants.ts | checkAddLiquidityInvariants | Liquidity | Critical |
| fuzz/properties/invariants.ts | checkWithdrawLiquidityInvariants | Liquidity | Critical |
| fuzz/properties/invariants.ts | checkMoveLiquidityInvariants | Liquidity | High |
| fuzz/properties/invariants.ts | checkCreatePoolInvariants | Pool Creation | High |

### Harness-level fuzz targets (Rust / TS / etc.)

| Target name | Language | Input type | What it fuzzes | Current corpus size |
|-------------|----------|------------|----------------|---------------------|
| comprehensive.test.ts | TypeScript | Random transaction sequences (swaps, liquidity ops, migrations) | All DLMM operations with invariant checking | 1 seed (default: 100 transactions) |
| quote-engine-validation.test.ts | TypeScript | Random swap amounts and directions (single-bin and multi-bin) | Swap calculations vs production quote engine (supports --multi-bin flag for 50% multi-bin swaps) | 1 seed (default: 100 transactions) |
| bin-traversal.test.ts | TypeScript | Bin traversal sequences (0 → -500 → 500 → 0) | Bin edge cases and traversal logic | 1 seed (default: 100 transactions) |
| zero-fee-exploit.test.ts | TypeScript | Random swaps with zero fees | Rounding exploits in zero-fee scenarios | 1 seed (default: 100 transactions) |
| basic.test.ts | TypeScript | Simple randomized operations | Basic fuzzing with simple operations | 1 seed (default: 100 transactions) |

## 3. Key Invariants Currently Enforced

- [Critical] LP supply remains unchanged during swaps
- [Critical] Bin balance changes match expected amounts (X increases, Y decreases for X-for-Y swaps)
- [Critical] User balance changes match contract return values exactly
- [Critical] Protocol fees accumulate correctly and never decrease
- [Critical] No negative balances (bins, users, LP supply)
- [Critical] Contract swap output never exceeds quote engine maximum (exploit prevention)
- [High] LP supply increases on add-liquidity
- [High] LP supply decreases on withdraw-liquidity
- [High] LP tokens minted >= minDlp on add-liquidity
- [High] X/Y amounts received >= minXAmount/minYAmount on withdraw-liquidity
- [High] Source bin LP supply decreases and destination bin increases on move-liquidity
- [High] Pool is created with valid ID and initial liquidity on create-pool

## 4. Gaps / Missing Critical Invariants (your expert opinion)

- [Missing] Reentrancy protection verification (no reentrancy guards explicitly tested)
- [Missing] Integer overflow/underflow protection on u128 arithmetic (Clarity has built-in overflow protection, but edge cases not explicitly fuzzed)
- [Missing] Access control invariants (admin-only functions, role-based permissions)
- [Missing] Time-based invariants (cooldown periods, migration execution time windows)
- [Missing] Pool state consistency across multiple pools (only single pool tested)
- [Missing] Cross-bin invariant verification (total pool value conservation across all bins)
- [Missing] Fee calculation precision invariants (very small fee amounts, rounding edge cases)
- [Missing] Multi-bin swap invariant verification in comprehensive fuzz test (quote-engine test has multi-bin mode, but comprehensive test doesn't use it)
- [Missing] Liquidity migration invariants (moving liquidity across large bin ranges)
- [Missing] Pool creation parameter validation (invalid token pairs, duplicate pools)

## 5. One-liner to run everything

```bash
cd clarity && npm run test:all
```

