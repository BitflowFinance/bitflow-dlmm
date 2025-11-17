# Rounding Differences Analysis Report

**Date:** 2025-11-17  
**Test Run:** 200 transactions  
**Swaps Analyzed:** 43

## How to Recreate This Analysis

### 1. Run the Fuzz Test

**For 200 transactions (initial analysis):**
```bash
cd .bitflow-dlmm/clarity
source ~/.nvm/nvm.sh
nvm use 20
FUZZ_SIZE=200 npm test -- tests/dlmm-core-comprehensive-fuzz.test.ts --run
```

**For 1000 transactions (adversarial analysis):**
```bash
cd .bitflow-dlmm/clarity
source ~/.nvm/nvm.sh
nvm use 20
FUZZ_SIZE=1000 npm test -- tests/dlmm-core-comprehensive-fuzz.test.ts --run
```

**Note:** The test maintains state between transactions (compounds), so each transaction builds on the previous state. This is critical for testing cumulative rounding effects.

### 2. Run the Analysis Script

```bash
npx tsx scripts/analyze-rounding-differences.ts
```

### 3. View Results

Results are saved in `logs/fuzz-test-results/`:
- `rounding-differences-*.json` - Raw rounding difference data
- `rounding-analysis-*.json` - Categorized analysis report
- `rounding-analysis-summary.md` - Human-readable summary
- `adversarial-analysis-*.json` - **NEW:** Adversarial analysis with rounding bias, balance conservation, and cumulative pool value leakage

## Key Findings

### Rounding Direction Verification

**Contract Formulas:**
- `max-x-amount` (swap-x-for-y, line 1260): Uses **CEILING** rounding
  - Formula: `(/ (+ (* y-balance PRICE_SCALE_BPS) (- bin-price u1)) bin-price)`
  
- `max-y-amount` (swap-y-for-x, line 1405): Uses **CEILING** rounding
  - Formula: `(/ (+ (* x-balance bin-price) (- PRICE_SCALE_BPS u1)) PRICE_SCALE_BPS)`

**Other calculations:** Use standard FLOOR rounding (integer division)

### Overall Statistics

- **Total swaps analyzed:** 43
- **Mean float diff:** 76.40 tokens
- **Max float diff:** 400 tokens
- **Mean float % diff:** 0.0017%
- **Max float % diff:** 0.0732%
- **Zero diff count:** 26 (60.5%)
- **Small diff (<0.1%):** 43 (100.0%)
- **Integer diff = 0:** 43 (100.0%) ✅

### Pattern Identified

**When Rounding Differences ARE Detected:**
- ✅ Small input amounts (<100K tokens) - Mean 0.0183%, Max 0.0732%
- ✅ Low balance conditions (<1M tokens)
- ✅ swap-x-for-y function (more than swap-y-for-x)
- ✅ Medium output amounts

**When Rounding Differences are NOT Detected (or very small):**
- ✅ Large input amounts (>10M tokens)
- ✅ High balance conditions (>100M tokens)
- ✅ swap-y-for-x function
- ✅ Very large output amounts

### Worst Case

**Tx 116 (swap-x-for-y):**
- Input: 1,635 tokens
- Output: 268,996 tokens
- Float diff: 197 tokens (0.0732%)
- Conditions: Small input, low balance, active bin
- Expected (float): 268,799 tokens
- Actual (contract): 268,996 tokens
- **Contract gives MORE than ideal float math** (197 tokens more)

### Acceptability Assessment

**✅ All Rounding Differences are ACCEPTABLE:**
- Maximum difference: 0.0732% (well below 1% threshold)
- Mean difference: 0.0017% (negligible)
- All differences are expected due to integer division
- No systematic bias detected in initial analysis
- Economic impact is negligible for individual swaps

## Test Configuration

The test uses:
- Enhanced amount generation with varied percentages:
  - 20% very small (<0.1% of max)
  - 30% small (0.1-1% of max)
  - 30% medium (1-10% of max)
  - 20% large (10-30% of max)
- Minimum swap amount: 100 tokens (lowered from 10,000)
- All swaps use active bin (as required by contract)

## Files Generated

1. `rounding-differences-*.json` - Raw rounding difference data for all swaps
2. `rounding-analysis-*.json` - Categorized analysis with statistics
3. `rounding-analysis-summary.md` - Complete summary document
4. `adversarial-analysis-*.json` - **NEW:** Adversarial analysis including:
   - Rounding bias per swap (does rounding favor pool or users?)
   - Balance conservation checks (X and Y balances)
   - Pool value leakage tracking (cumulative impact)
   - Statistics on bias direction and total leakage

## Adversarial Analysis Features

The test now tracks:
- **Rounding Bias**: Whether each swap's rounding favors the pool or users
- **Balance Conservation**: Verifies X and Y balances are correctly updated
- **Pool Value Leakage**: Tracks if pool value changes match expected fees
- **Cumulative Impact**: Sums up all leakage over many transactions

This helps answer:
- Can an attacker exploit rounding through many small swaps?
- Does rounding cause value to leak from the pool over time?
- Are balance equations correctly maintained?
- What's the maximum cumulative impact?

