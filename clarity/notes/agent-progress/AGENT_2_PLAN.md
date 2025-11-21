# Agent 2: Withdraw-Liquidity Rounding Checks - Implementation Plan

**Status**: ✅ Complete - Lessons Learned Applied  
**Created**: 2025-01-27  
**Agent**: Agent 2  
**Todo**: `extend-withdraw-liquidity-rounding`

## Executive Summary

Add comprehensive float comparison for `withdraw-liquidity` X/Y amount calculation in the `checkRoundingErrors()` function, following the exact pattern established by swap rounding checks.

## Context

### Current State
- **Location**: `tests/dlmm-core-comprehensive-fuzz.test.ts`, lines 1894-1922 (original), lines 2513-2931 (implemented)
- **Reference**: See swap rounding checks at lines 1274-1540 for the pattern to follow

### Contract Formula
From `dlmm-core-v-1-1.clar` lines 1719-1720:
```clarity
(x-amount (/ (* amount x-balance) bin-shares))
(y-amount (/ (* amount y-balance) bin-shares))
```

## Implementation Plan

### Phase 1: Understand Contract Logic
- Review contract code for withdraw-liquidity
- Understand formula: proportional withdrawal based on LP burned
- Note: No fees for withdraw-liquidity (unlike swaps)

### Phase 2: Implement Float Math Calculation
- Calculate expected X and Y amounts using float math
- Formula: `xOut = (lpBurned * xBalance) / totalSupply`
- Formula: `yOut = (lpBurned * yBalance) / totalSupply`

### Phase 3: Add Rounding Checks
- CHECK 1: Exact Integer Match (verify test logic matches contract)
- CHECK 2: Rounding Error Detection (compare to ideal float math)
- Adversarial Analysis: Rounding Bias and Balance Conservation
- CRITICAL EXPLOIT CHECK: User-favored bias detection

### Phase 4: Testing
- Run comprehensive fuzz test
- Verify no calculation mismatches
- Verify no exploits detected
- Verify rounding differences are logged

## Key Implementation Details

- Both X and Y amounts tracked separately
- No fees for withdraw-liquidity
- All lessons learned applied (integer vs float separation, adversarial exploit detection)
- See `TODO-extend-withdraw-liquidity-rounding.md` for detailed progress

## Progress File

See `TODO-extend-withdraw-liquidity-rounding.md` for detailed progress and findings.

