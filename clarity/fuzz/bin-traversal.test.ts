import {
  alice,
  bob,
  dlmmCore,
  sbtcUsdcPool,
  mockSbtcToken,
  mockUsdcToken,
  setupTestEnvironment,
  getSbtcUsdcPoolLpBalance,
} from "../tests/helpers/helpers";

import { describe, it, expect, beforeEach } from 'vitest';
import { txOk, rovOk } from '@clarigen/test';
import { LogManager, DirectionType, MIN_BIN_ID, MAX_BIN_ID, CENTER_BIN_ID } from './utils';

interface BinBalances {
  xBalance: bigint;
  yBalance: bigint;
}

interface LiquidityAmounts {
  xAmount: bigint;
  yAmount: bigint;
}

class TestConfig {
  static readonly TRAVERSAL_PATH = [0n, -500n, 500n, 0n];
  
  static readonly SWAPS_PER_BIN = 5;
  static readonly ADD_LIQUIDITY_PER_BIN = 3;
  static readonly WITHDRAW_LIQUIDITY_PER_BIN = 3;
  static readonly MOVE_LIQUIDITY_PER_BIN = 3;
  
  static readonly SWAP_BIN_BALANCE_PERCENT = 15; // 15%
  static readonly ADD_LIQUIDITY_USER_BALANCE_PERCENT = 10; // 10%
  static readonly WITHDRAW_LP_PERCENT = 40; // 30-50%
  static readonly MOVE_LP_PERCENT = 30; // 20-40%
  
  static readonly MIN_SWAP_AMOUNT = 10000n;
  static readonly MIN_ADD_LIQUIDITY_AMOUNT = 1000n;
  static readonly MIN_WITHDRAW_AMOUNT = 100n;
  static readonly MIN_MOVE_AMOUNT = 100n;
  static readonly MIN_DLP = 1n;
  
  static readonly MAX_CROSS_BIN_ATTEMPTS = 200;
  
  static readonly MAX_LIQUIDITY_FEE = 1000000n;

  static readonly TIMEOUT = 600000;
}

class PoolStateManager {
  static getActiveBinId(): bigint {
    return rovOk(sbtcUsdcPool.getActiveBinId());
  }

  static getBinBalances(binId: bigint): BinBalances {
    const unsignedBinId = rovOk(dlmmCore.getUnsignedBinId(binId));
    try {
      const balances = rovOk(sbtcUsdcPool.getBinBalances(unsignedBinId));
      return { xBalance: balances.xBalance, yBalance: balances.yBalance };
    } catch {
      return { xBalance: 0n, yBalance: 0n };
    }
  }

  static getUserTokenBalance(user: string, tokenContract: any): bigint {
    return rovOk(tokenContract.getBalance(user)) as bigint;
  }

  static getUserLpBalance(user: string, binId: bigint): bigint {
    try {
      return getSbtcUsdcPoolLpBalance(binId, user);
    } catch {
      return 0n;
    }
  }
}

class AmountGenerator {
  static generateSwapAmount(binId: bigint, direction: DirectionType, user: string): bigint | null {
    const balances = PoolStateManager.getBinBalances(binId);
    const userXBalance = PoolStateManager.getUserTokenBalance(user, mockSbtcToken);
    const userYBalance = PoolStateManager.getUserTokenBalance(user, mockUsdcToken);

    if (direction === 'x-for-y') {
      if (balances.yBalance === 0n || userXBalance === 0n) return null;
      const maxFromBin = (balances.yBalance * BigInt(TestConfig.SWAP_BIN_BALANCE_PERCENT)) / 100n;
      const maxAmount = maxFromBin < userXBalance ? maxFromBin : userXBalance;
      return maxAmount < TestConfig.MIN_SWAP_AMOUNT ? null : maxAmount;
    } else {
      if (balances.xBalance === 0n || userYBalance === 0n) return null;
      const maxFromBin = (balances.xBalance * BigInt(TestConfig.SWAP_BIN_BALANCE_PERCENT)) / 100n;
      const maxAmount = maxFromBin < userYBalance ? maxFromBin : userYBalance;
      return maxAmount < TestConfig.MIN_SWAP_AMOUNT ? null : maxAmount;
    }
  }

  static generateAddLiquidityAmounts(binId: bigint, user: string): LiquidityAmounts | null {
    const activeBinId = PoolStateManager.getActiveBinId();
    const userXBalance = PoolStateManager.getUserTokenBalance(user, mockSbtcToken);
    const userYBalance = PoolStateManager.getUserTokenBalance(user, mockUsdcToken);

    if (binId < activeBinId) {
      // y only
      if (userYBalance === 0n) return null;
      const yAmount = (userYBalance * BigInt(TestConfig.ADD_LIQUIDITY_USER_BALANCE_PERCENT)) / 100n;
      return yAmount < TestConfig.MIN_ADD_LIQUIDITY_AMOUNT ? null : { xAmount: 0n, yAmount };
    } else if (binId === activeBinId) {
      // both x & y
      if (userXBalance === 0n || userYBalance === 0n) return null;
      const xAmount = (userXBalance * BigInt(TestConfig.ADD_LIQUIDITY_USER_BALANCE_PERCENT)) / 100n;
      const yAmount = (userYBalance * BigInt(TestConfig.ADD_LIQUIDITY_USER_BALANCE_PERCENT)) / 100n;
      return (xAmount < TestConfig.MIN_ADD_LIQUIDITY_AMOUNT || yAmount < TestConfig.MIN_ADD_LIQUIDITY_AMOUNT) 
        ? null 
        : { xAmount, yAmount };
    } else {
      // x only
      if (userXBalance === 0n) return null;
      const xAmount = (userXBalance * BigInt(TestConfig.ADD_LIQUIDITY_USER_BALANCE_PERCENT)) / 100n;
      return xAmount < TestConfig.MIN_ADD_LIQUIDITY_AMOUNT ? null : { xAmount, yAmount: 0n };
    }
  }

  static generateWithdrawAmount(binId: bigint, user: string): bigint | null {
    const lpBalance = PoolStateManager.getUserLpBalance(user, binId);
    if (lpBalance === 0n) return null;
    const amount = (lpBalance * BigInt(TestConfig.WITHDRAW_LP_PERCENT)) / 100n;
    return amount < TestConfig.MIN_WITHDRAW_AMOUNT ? null : amount;
  }

  static generateMoveAmount(sourceBinId: bigint, user: string): bigint | null {
    const lpBalance = PoolStateManager.getUserLpBalance(user, sourceBinId);
    if (lpBalance === 0n) return null;
    const amount = (lpBalance * BigInt(TestConfig.MOVE_LP_PERCENT)) / 100n;
    return amount < TestConfig.MIN_MOVE_AMOUNT ? null : amount;
  }
}

class OperationExecutor {
  static executeSwap(binId: bigint, direction: DirectionType, amount: bigint, user: string): void {
    if (direction === 'x-for-y') {
      txOk(dlmmCore.swapXForY(
        sbtcUsdcPool.identifier,
        mockSbtcToken.identifier,
        mockUsdcToken.identifier,
        Number(binId),
        amount
      ), user);
    } else {
      txOk(dlmmCore.swapYForX(
        sbtcUsdcPool.identifier,
        mockSbtcToken.identifier,
        mockUsdcToken.identifier,
        Number(binId),
        amount
      ), user);
    }
  }

  static executeAddLiquidity(binId: bigint, amounts: LiquidityAmounts, user: string): void {
    txOk(dlmmCore.addLiquidity(
      sbtcUsdcPool.identifier,
      mockSbtcToken.identifier,
      mockUsdcToken.identifier,
      Number(binId),
      amounts.xAmount,
      amounts.yAmount,
      TestConfig.MIN_DLP,
      TestConfig.MAX_LIQUIDITY_FEE,
      TestConfig.MAX_LIQUIDITY_FEE
    ), user);
  }

  static executeWithdrawLiquidity(binId: bigint, amount: bigint, user: string): void {
    txOk(dlmmCore.withdrawLiquidity(
      sbtcUsdcPool.identifier,
      mockSbtcToken.identifier,
      mockUsdcToken.identifier,
      Number(binId),
      amount,
      0n, // minXAmount
      0n  // minYAmount
    ), user);
  }

  /**
   * Execute move liquidity operation
   */
  static executeMoveLiquidity(fromBinId: bigint, toBinId: bigint, amount: bigint, user: string): void {
    txOk(dlmmCore.moveLiquidity(
      sbtcUsdcPool.identifier,
      mockSbtcToken.identifier,
      mockUsdcToken.identifier,
      Number(fromBinId),
      Number(toBinId),
      amount,
      TestConfig.MIN_DLP,
      TestConfig.MAX_LIQUIDITY_FEE,
      TestConfig.MAX_LIQUIDITY_FEE
    ), user);
  }
}

class BinOperationsHandler {
  static performSwaps(binId: bigint, count: number, orchestrator: LogManager): void {
    orchestrator.log(`Performing ${count} swaps in bin ${binId}`);
    
    for (let j = 0; j < count; j++) {
      const direction: DirectionType = j % 2 === 0 ? 'x-for-y' : 'y-for-x';
      const user = j % 2 === 0 ? alice : bob;
      const amount = AmountGenerator.generateSwapAmount(binId, direction, user);
      
      if (!amount) {
        orchestrator.log(`Skipping swap ${j + 1} - insufficient balance`);
        continue;
      }
      
      try {
        OperationExecutor.executeSwap(binId, direction, amount, user);
        orchestrator.log(` Swap ${j + 1}: ${direction} with amount ${amount}`);
        orchestrator.incrementStat('successfulSwap');
      } catch (error: any) {
        orchestrator.logError(`Swap failed at bin ${binId}`, { binId, direction, amount, error });
        orchestrator.recordResult({ type: 'error', operation: 'swap', binId, error: String(error) });
        orchestrator.incrementStat('failedSwap');
      }
    }
  }

  static performAddLiquidity(binId: bigint, count: number, orchestrator: LogManager): void {
    orchestrator.log(`Performing ${count} add liquidity operations in bin ${binId}`);
    
    for (let j = 0; j < count; j++) {
      const user = j % 2 === 0 ? alice : bob;
      const amounts = AmountGenerator.generateAddLiquidityAmounts(binId, user);
      
      if (!amounts) {
        orchestrator.log(`Skipping add liquidity ${j + 1} - insufficient balance`);
        continue;
      }
      
      try {
        OperationExecutor.executeAddLiquidity(binId, amounts, user);
        orchestrator.log(`  Add liquidity ${j + 1}: x=${amounts.xAmount}, y=${amounts.yAmount}`);
        orchestrator.incrementStat('successfulAddLiquidity');
      } catch (error: any) {
        orchestrator.logError(`Add liquidity failed at bin ${binId}`, { binId, amounts, error });
        orchestrator.recordResult({ type: 'error', operation: 'addLiquidity', binId, error: String(error) });
        orchestrator.incrementStat('failedAddLiquidity');
      }
    }
  }

  static performWithdrawLiquidity(binId: bigint, count: number, orchestrator: LogManager): void {
    orchestrator.log(`Performing ${count} remove liquidity operations in bin ${binId}`);
    
    for (let j = 0; j < count; j++) {
      const user = j % 2 === 0 ? alice : bob;
      const amount = AmountGenerator.generateWithdrawAmount(binId, user);
      
      if (!amount) {
        orchestrator.log(`Skipping remove liquidity ${j + 1} - no LP tokens`);
        continue;
      }
      
      try {
        OperationExecutor.executeWithdrawLiquidity(binId, amount, user);
        orchestrator.log(`  Remove liquidity ${j + 1}: ${amount} LP tokens`);
        orchestrator.incrementStat('successfulWithdrawLiquidity');
      } catch (error: any) {
        orchestrator.logError(`Withdraw liquidity failed at bin ${binId}`, { binId, amount, error });
        orchestrator.recordResult({ type: 'error', operation: 'withdrawLiquidity', binId, error: String(error) });
        orchestrator.incrementStat('failedWithdrawLiquidity');
      }
    }
  }

  static performMoveLiquidity(binId: bigint, count: number, orchestrator: LogManager): void {
    orchestrator.log(`Performing ${count} move liquidity operations from bin ${binId}`);
    
    for (let j = 0; j < count; j++) {
      const user = j % 2 === 0 ? alice : bob;
      const amount = AmountGenerator.generateMoveAmount(binId, user);
      
      if (!amount) {
        orchestrator.log(`Skipping move liquidity ${j + 1} - no LP tokens`);
        continue;
      }
      
      // Determine target bin
      const targetBin = binId === MIN_BIN_ID 
        ? binId + 1n 
        : binId === MAX_BIN_ID
        ? binId - 1n
        : binId + (j % 2 === 0 ? 1n : -1n);
      
      if (targetBin < MIN_BIN_ID || targetBin > MAX_BIN_ID) {
        orchestrator.log(`Skipping move liquidity ${j + 1} - target bin ${targetBin} out of range`);
        continue;
      }
      
      try {
        OperationExecutor.executeMoveLiquidity(binId, targetBin, amount, user);
        orchestrator.log(`  Move liquidity ${j + 1}: ${amount} LP tokens from ${binId} to ${targetBin}`);
        orchestrator.incrementStat('successfulMoveLiquidity');
      } catch (error: any) {
        orchestrator.logError(`Move liquidity failed from bin ${binId} to ${targetBin}`, { binId, targetBin, amount, error });
        orchestrator.recordResult({ type: 'error', operation: 'moveLiquidity', binId, error: String(error) });
        orchestrator.incrementStat('failedMoveLiquidity');
      }
    }
  }

  static processAllOperations(binId: bigint, orchestrator: LogManager): void {
    this.performSwaps(binId, TestConfig.SWAPS_PER_BIN, orchestrator);
    this.performAddLiquidity(binId, TestConfig.ADD_LIQUIDITY_PER_BIN, orchestrator);
    this.performWithdrawLiquidity(binId, TestConfig.WITHDRAW_LIQUIDITY_PER_BIN, orchestrator);
    this.performMoveLiquidity(binId, TestConfig.MOVE_LIQUIDITY_PER_BIN, orchestrator);
    orchestrator.log(`Completed operations in bin ${binId}`);
  }
}

class BinTraversalHandler {
  static swapToCrossBin(targetBinId: bigint, orchestrator: LogManager): boolean {
    const activeBinId = PoolStateManager.getActiveBinId();
    
    if (activeBinId === targetBinId) {
      return true; // at target
    }

    orchestrator.log(`Swapping to cross from bin ${activeBinId} to bin ${targetBinId}`);

    const direction: DirectionType = targetBinId > activeBinId ? 'x-for-y' : 'y-for-x';
    let attempts = 0;

    while (PoolStateManager.getActiveBinId() !== targetBinId && attempts < TestConfig.MAX_CROSS_BIN_ATTEMPTS) {
      attempts++;
      const currentBinId = PoolStateManager.getActiveBinId();
      
      // correct direction sanity
      const currentDirection: DirectionType = targetBinId > currentBinId ? 'x-for-y' : 'y-for-x';
      if (currentDirection !== direction) {
        orchestrator.log(`DirectionType changed at bin ${currentBinId}, target is ${targetBinId}`);
        break;
      }
      
      const amount = AmountGenerator.generateSwapAmount(currentBinId, currentDirection, alice);
      
      if (!amount) {
        // try adding liquidity to continue
        if (this.tryAddLiquidityForTraversal(currentBinId, alice, orchestrator)) {
          continue;
        }
        break;
      }

      try {
        OperationExecutor.executeSwap(currentBinId, currentDirection, amount, alice);
        const newBinId = PoolStateManager.getActiveBinId();
        orchestrator.log(`Swap ${currentDirection}: ${amount} at bin ${currentBinId} -> new bin ${newBinId}`);
      } catch (error: any) {
        orchestrator.logError(`Cross-bin swap failed`, { currentBinId, direction: currentDirection, amount, error });
        continue;
      }
    }

    const finalBinId = PoolStateManager.getActiveBinId();
    if (finalBinId === targetBinId) {
      orchestrator.log(`Successfully reached target bin ${targetBinId}`);
      return true;
    } else {
      orchestrator.log(`Reached bin ${finalBinId} instead of target ${targetBinId} after ${attempts} attempts`);
      return false;
    }
  }

  private static tryAddLiquidityForTraversal(binId: bigint, user: string, orchestrator: LogManager): boolean {
    orchestrator.log(`Cannot generate swap amount at bin ${binId} - attempting to add liquidity`);
    const amounts = AmountGenerator.generateAddLiquidityAmounts(binId, user);
    
    if (!amounts) return false;
    
    try {
      OperationExecutor.executeAddLiquidity(binId, amounts, user);
      orchestrator.log(`Added liquidity to bin ${binId} to continue traversal`);
      return true;
    } catch (e) {
      orchestrator.log(`Failed to add liquidity at bin ${binId}`);
      return false;
    }
  }
}

class TestOrchestrator {
  private orchestrator: LogManager;

  constructor(orchestrator: LogManager) {
    this.orchestrator = orchestrator;
  }

  processBin(targetBinId: bigint, isFirstBin: boolean): void {
    this.orchestrator.log(`\n=== Processing bin ${targetBinId} ===`);
    
    // Traverse to target bin
    if (!isFirstBin) {
      const success = BinTraversalHandler.swapToCrossBin(targetBinId, this.orchestrator);
      if (!success) {
        this.orchestrator.log(`Failed to reach bin ${targetBinId}`);
        return;
      }
    }
    
    const currentBinId = PoolStateManager.getActiveBinId();
    expect(currentBinId).toBe(targetBinId);
    
    // Perform all operations in this bin
    BinOperationsHandler.processAllOperations(currentBinId, this.orchestrator);
  }

  executeTraversalPath(traversalPath: bigint[]): void {
    for (let i = 0; i < traversalPath.length; i++) {
      this.processBin(traversalPath[i], i === 0);
    }
  }

  recenterPool(): bigint {
    let finalBinId = PoolStateManager.getActiveBinId();
    
    if (finalBinId !== CENTER_BIN_ID) {
      this.orchestrator.log(`\nAttempting to return to bin 0 from bin ${finalBinId}`);
      const success = BinTraversalHandler.swapToCrossBin(CENTER_BIN_ID, this.orchestrator);
      if (!success) {
        this.orchestrator.incrementStat('failedReturnToCenter');
      }
      finalBinId = PoolStateManager.getActiveBinId();
    }
    
    return finalBinId;
  }

  finish(finalBinId: bigint): void {
    this.orchestrator.log(`\nFinal bin ID: ${finalBinId}`);
    this.orchestrator.finish();

    expect(this.orchestrator.stats.failed).toBe(0);
  }
}

describe('DLMM Core Bin Traversal Fuzz Test', () => {

  beforeEach(() => {
    setupTestEnvironment();
  });

  it('should traverse bins: 0 => -500 => 500 => 0 with operations in each bin', async () => {
    const orchestrator = new LogManager('bin-traversal');
    orchestrator.log('Starting bin traversal fuzz test');
    
    const testOrchestrator = new TestOrchestrator(orchestrator);
    
    // execute traversal path
    testOrchestrator.executeTraversalPath(TestConfig.TRAVERSAL_PATH);
    
    // attempt to return to center
    const finalBinId = testOrchestrator.recenterPool();
    
    // log final summary
    testOrchestrator.finish(finalBinId);    
  }, TestConfig.TIMEOUT);
});
