# TODO: Extend Move-Liquidity Rounding Checks

**Status**: In Progress - Test Running  
**Assigned To**: Agent 3  
**Started**: 2025-01-XX  
**Last Updated**: 2025-01-XX

## Context

Add float comparison for `move-liquidity` LP token calculation in the `checkRoundingErrors()` function, following the exact pattern established by swap rounding checks.

**Key Files**:
- `tests/dlmm-core-comprehensive-fuzz.test.ts` - Main test file
- Location: After line 2297 (after withdraw-liquidity section)
- Reference: Swap checks at lines 1274-1851

## Progress

### Completed
- ✅ Reviewed all lessons learned
- ✅ Updated plan with critical lessons (BigInt usage, exploit detection)
- ✅ Started 10,000 transaction fuzz test

### In Progress
- ⏳ 10,000 transaction test running (started ~3:19 AM, expected ~5.5 hours)
- ⏳ Waiting for test completion to analyze logs

### Pending
- ⏳ Implement move-liquidity rounding checks
- ⏳ Analyze test logs for violations and rounding differences
- ⏳ Document findings

## Test Execution Status

**10,000 Transaction Test**: Running
- **Command**: `FUZZ_SIZE=10000 npm run test-simple -- tests/dlmm-core-comprehensive-fuzz.test.ts`
- **Process IDs**: 45456 (running 1:08), 47262 (running 0:25)
- **Timeout**: 6 hours (21600000ms)
- **Expected Duration**: ~5.5 hours (10,000 transactions × 2 seconds = 20,000 seconds)
- **Status**: Running in background
- **Results Location**: `logs/fuzz-test-results/`

**Latest 100-Transaction Test Results** (from 2025-11-18T07-58-54-615Z):
- Total Transactions: 84 successful
- Calculation Mismatches: 12 (test logic errors)
- Rounding Errors: 6 (all critical, user-favored bias in swap-x-for-y)
- All rounding errors are user-favored (user received MORE than float math suggests)
- Errors range from 100-300 tokens difference (0.0000% - very small but still exploits)

## Key Lessons Applied

1. **Adversarial Exploit Detection**: Fail immediately if user receives MORE than float math suggests (even 1 token)
2. **Integer vs Float Math Separation**: Use BigInt for ALL integer math replication
3. **No Tolerance**: Integer matches must be exact (0 difference)

## Next Steps

1. Wait for 10K test to complete
2. Analyze logs for:
   - Total violations
   - Rounding differences
   - User-favored vs pool-favored bias
   - Move-liquidity specific issues (once implemented)
3. Implement move-liquidity rounding checks following the plan
4. Re-run test to verify implementation

## Blockers

None - test is running as expected.

