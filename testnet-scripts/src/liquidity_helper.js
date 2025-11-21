// liquidity_helper.js

require('dotenv').config();

const {
  makeContractCall,
  broadcastTransaction,
  uintCV,
  intCV,
  callReadOnlyFunction,
  principalCV,
  tupleCV,
  listCV,
  contractPrincipalCV,
  PostConditionMode,
  FungibleConditionCode,
  NonFungibleConditionCode,
  makeStandardFungiblePostCondition,
  makeContractFungiblePostCondition,
  makeStandardNonFungiblePostCondition,
  createAssetInfo,
  AnchorMode,
  getNonce,
} = require('@stacks/transactions');
const { StacksMainnet, StacksTestnet } = require('@stacks/network');
const { sample, random } = require('lodash');

const BFF_API_URL = process.env.BFF_API_URL;
const STACKS_PUBLIC_KEY = process.env.STACKS_PUBLIC_KEY;
const STACKS_PRIVATE_KEY = process.env.STACKS_PRIVATE_KEY;
const STACKS_API_URL = process.env.STACKS_API_URL;
const STACKS_NODE_URL = process.env.STACKS_NODE_URL;
const STACKS_NODE_KEY = process.env.STACKS_NODE_KEY;
const STACKS_NETWORK_VERSION = process.env.STACKS_NETWORK_VERSION;
const TRANSACTIONS_TO_BROADCAST = parseInt(process.env.TRANSACTIONS_TO_BROADCAST, 10);
const TRANSACTION_FEE_RATE = parseInt(process.env.TRANSACTION_FEE_RATE, 10);
const TRANSACTION_INTERVAL_MS = parseInt(process.env.TRANSACTION_INTERVAL_MS, 10);
const POOL_COOLDOWN_MS = parseInt(process.env.POOL_COOLDOWN_MS || process.env.PAIR_COOLDOWN_MS, 10);
const MIN_BALANCE_PERCENT = parseFloat(process.env.MIN_BALANCE_PERCENT, 10);
const MAX_BALANCE_PERCENT = parseFloat(process.env.MAX_BALANCE_PERCENT, 10);
const MIN_LIQUIDITY_BINS = parseInt(process.env.MIN_LIQUIDITY_BINS, 10);
const MAX_LIQUIDITY_BINS = parseInt(process.env.MAX_LIQUIDITY_BINS, 10);
const MIN_WITHDRAWAL_PERCENT = parseFloat(process.env.MIN_WITHDRAWAL_PERCENT, 10);
const MAX_WITHDRAWAL_PERCENT = parseFloat(process.env.MAX_WITHDRAWAL_PERCENT, 10);
const SLIPPAGE_TOLERANCE = parseInt(process.env.SLIPPAGE_TOLERANCE, 10);
const USE_MIN_RECEIVED = process.env.USE_MIN_RECEIVED === 'true';
const USE_POST_CONDITIONS = process.env.USE_POST_CONDITIONS === 'true';
const ALLOW_ALL_TOKENS = process.env.ALLOW_ALL_TOKENS === 'true';
const DEBUG_MODE = process.env.DEBUG_MODE === 'true';

const LIQUIDITY_ROUTER_CONTRACT = 'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.dlmm-liquidity-router-v-0-1';

const PRICE_SCALE_BPS = 1e8;
const FEE_SCALE_BPS = 1e4;
const CENTER_BIN_ID = 500;

// Allowed tokens and their per-transaction maximums (do not scale)
const ALLOWED_TOKENS = {
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tstx-v-0-2': 30000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tdog-v-0-2': 300000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tusdc-v-0-2': 30000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tusdh-v-0-1': 3000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tbtc-v-0-2': 0.03
};

let POOLS = [];

const poolCooldowns = new Map();

const mergeRequestHeaders = (base, extra) => {
  if (!base) return extra;

  if (typeof Headers !== 'undefined' && base instanceof Headers) {
    const headers = new Headers(base);
    Object.entries(extra).forEach(([key, value]) => headers.set(key, value));
    return headers;
  };

  if (Array.isArray(base)) {
    const headers = new Headers(base);
    Object.entries(extra).forEach(([key, value]) => headers.set(key, value));
    return headers;
  };

  return { ...(base), ...extra };
};

const getStacksNetwork = (useDefault = false) => {
  const isMainnet = String(STACKS_NETWORK_VERSION || 'mainnet').toLowerCase() === 'mainnet';

  const defaultUrl = isMainnet
    ? 'https://api.mainnet.hiro.so'
    : 'https://api.testnet.hiro.so';
  const url = STACKS_NODE_URL && !useDefault ? STACKS_NODE_URL : defaultUrl;

  const fetchFn = STACKS_NODE_KEY
    ? (input, init) => {
        const headers = mergeRequestHeaders(init && init.headers, { 'X-API-Key': STACKS_NODE_KEY });
        return fetch(input, { ...(init || {}), headers });
      }
    : undefined;

  return isMainnet
    ? new StacksMainnet({ url, fetchFn })
    : new StacksTestnet({ url, fetchFn });
};

const stacksNetwork = getStacksNetwork();

const parseContract = (contract) => {
  const [address, name] = contract.split('.');
  return { address, name };
};

const getSignedBinId = (unsignedBinId) => {
  return unsignedBinId - CENTER_BIN_ID;
};

const getTokenBalance = async (tokenContract, stacksAddress) => {
  const { address, name } = parseContract(tokenContract);
  const response = await callReadOnlyFunction({
    contractAddress: address,
    contractName: name,
    functionName: 'get-balance',
    functionArgs: [principalCV(stacksAddress)],
    network: stacksNetwork,
    senderAddress: stacksAddress,
  });

  return Number(response.value.value);
};

const getSTXBalance = async (stacksAddress) => {
  const response = await fetch(`${STACKS_API_URL}/extended/v1/address/${stacksAddress}/stx`);
  
  if (!response.ok) throw new Error(`STX balance returned ${response.status} with message: ${await response.text()}`);
  
  const data = await response.json();

  if (!data.balance) throw new Error(`STX balance error: No balance found`);

  return Number(data.balance);
};

const isPoolOnCooldown = (poolId) => {
  const lastActionTime = poolCooldowns.get(poolId);
  
  if (!lastActionTime) return false;
  
  const elapsed = Date.now() - lastActionTime;
  return elapsed < POOL_COOLDOWN_MS;
};

const setPoolCooldown = (poolId) => {
  poolCooldowns.set(poolId, Date.now());
};

const getPools = async () => {
  const response = await fetch(BFF_API_URL + '/app/v1/pools', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) throw new Error(`Pools returned ${response.status} with message: ${await response.text()}`);
  
  const data = await response.json();
  
  if (!data.data || !Array.isArray(data.data)) throw new Error('Invalid pools response format');

  const tokenDecimals = new Map();
  data.data.forEach(pool => {
    if (pool.tokens?.tokenX?.decimals && pool.tokens?.tokenX?.contract) {
      const decimals = Number(pool.tokens.tokenX.decimals);
      if (decimals > 0) tokenDecimals.set(pool.tokens.tokenX.contract, decimals);
    };
    if (pool.tokens?.tokenY?.decimals && pool.tokens?.tokenY?.contract) {
      const decimals = Number(pool.tokens.tokenY.decimals);
      if (decimals > 0) tokenDecimals.set(pool.tokens.tokenY.contract, decimals);
    };
  });

  for (const tokenContract in ALLOWED_TOKENS) {
    const decimals = tokenDecimals.get(tokenContract);
    if (decimals && decimals > 0) ALLOWED_TOKENS[tokenContract] = Math.round(ALLOWED_TOKENS[tokenContract] * Math.pow(10, decimals));
  };

  const filteredPools = data.data.filter(pool => {
    const isDLMM = pool.types?.includes('DLMM') || false;
    const isActive = pool.poolStatus === true;
    const tokenX = pool.tokens?.tokenX?.contract;
    const tokenY = pool.tokens?.tokenY?.contract;
    
    if (!isDLMM || !isActive || !tokenX || !tokenY || pool.poolId !== 'dlmm_7') return false;
    
    if (ALLOW_ALL_TOKENS) return true;
    
    const hasTokenX = ALLOWED_TOKENS.hasOwnProperty(tokenX);
    const hasTokenY = ALLOWED_TOKENS.hasOwnProperty(tokenY);
    
    return hasTokenX && hasTokenY;
  });

  return filteredPools.map(pool => ({
    poolId: pool.poolId,
    poolContract: pool.poolContract,
    tokenX: pool.tokens.tokenX.contract,
    tokenY: pool.tokens.tokenY.contract,
    tokenXDecimals: pool.tokens.tokenX.decimals,
    tokenYDecimals: pool.tokens.tokenY.decimals,
    activeBinId: null,
    xProtocolFee: pool.xProtocolFee,
    xProviderFee: pool.xProviderFee,
    xVariableFee: pool.xVariableFee,
    yProtocolFee: pool.yProtocolFee,
    yProviderFee: pool.yProviderFee,
    yVariableFee: pool.yVariableFee,
  }));
};

const getPoolBins = async (poolId) => {
  const response = await fetch(BFF_API_URL + `/quotes/v1/bins/${poolId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) throw new Error(`Pool bins returned ${response.status} with message: ${await response.text()}`);
  
  const data = await response.json();
  
  return data;
};

const getUserPositionBins = async (userAddress, poolId) => {
  const response = await fetch(BFF_API_URL + `/app/v1/users/${userAddress}/positions/${poolId}/bins`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    if (response.status === 404) return { bins: [] };
    throw new Error(`User position bins returned ${response.status} with message: ${await response.text()}`);
  };

  const data = await response.json();

  return data;
};

const getTokenAssetName = async (tokenContract) => {
  const response = await fetch(BFF_API_URL + '/quotes/v1/tokens', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) throw new Error(`Tokens returned ${response.status} with message: ${await response.text()}`);

  const data = await response.json();

  const token = data.tokens?.find(t => t.contract_address === tokenContract);

  if (!token) throw new Error(`Token not found: ${tokenContract}`);

  return token.asset_name;
};

const calculateMinDlpForBin = (bin, poolFees, slippageTolerance = 1) => {
  if (!USE_MIN_RECEIVED) return 1;

  const {
    isActiveBin,
    binPrice,
    reserveX,
    reserveY,
    binShares,
    xAmount,
    yAmount
  } = bin;
  
  const {
    xProtocolFee,
    xProviderFee,
    xVariableFee,
    yProtocolFee,
    yProviderFee,
    yVariableFee
  } = poolFees;
  
  const minimumBinShares = 10000;
  const minimumBurntShares = 1000;
  
  const yAmountScaled = yAmount * PRICE_SCALE_BPS;
  const reserveYScaled = reserveY * PRICE_SCALE_BPS;
  
  const addLiquidityValue = binPrice * xAmount + yAmountScaled;
  const binLiquidityValue = binPrice * reserveX + reserveYScaled;

  const dlp = binShares === 0 || binLiquidityValue === 0
    ? Math.sqrt(addLiquidityValue)
    : (addLiquidityValue * binShares) / binLiquidityValue;

  let xAmountFeesLiquidity = 0;
  let yAmountFeesLiquidity = 0;

  if (isActiveBin && dlp > 0) {
    const xLiquidityFee = xProtocolFee + xProviderFee + xVariableFee;
    const yLiquidityFee = yProtocolFee + yProviderFee + yVariableFee;
    
    const xAmountWithdrawable = (dlp * (reserveX + xAmount)) / (binShares + dlp);
    const yAmountWithdrawable = (dlp * (reserveY + yAmount)) / (binShares + dlp);
    
    const maxXAmountFeesLiquidity = yAmountWithdrawable > yAmount && xAmount > xAmountWithdrawable
      ? ((xAmount - xAmountWithdrawable) * xLiquidityFee) / FEE_SCALE_BPS
      : 0;
    
    const maxYAmountFeesLiquidity = xAmountWithdrawable > xAmount && yAmount > yAmountWithdrawable
      ? ((yAmount - yAmountWithdrawable) * yLiquidityFee) / FEE_SCALE_BPS
      : 0;

    xAmountFeesLiquidity = xAmount > maxXAmountFeesLiquidity ? maxXAmountFeesLiquidity : xAmount;
    yAmountFeesLiquidity = yAmount > maxYAmountFeesLiquidity ? maxYAmountFeesLiquidity : yAmount;
  };
  
  const xAmountPostFees = xAmount - xAmountFeesLiquidity;
  const yAmountPostFees = yAmount - yAmountFeesLiquidity;
  const yAmountPostFeesScaled = yAmountPostFees * PRICE_SCALE_BPS;

  const reserveXPostFees = reserveX + xAmountFeesLiquidity;
  const reserveYPostFeesScaled = (reserveY + yAmountFeesLiquidity) * PRICE_SCALE_BPS;
  
  const addLiquidityValuePostFees = binPrice * xAmountPostFees + yAmountPostFeesScaled;
  const binLiquidityValuePostFees = binPrice * reserveXPostFees + reserveYPostFeesScaled;
  
  let dlpPostFees;
  if (binShares === 0) {
    const intendedDlp = Math.sqrt(addLiquidityValuePostFees);
    dlpPostFees = intendedDlp >= minimumBinShares ? intendedDlp - minimumBurntShares : 0;
  } else if (binLiquidityValuePostFees === 0) {
    dlpPostFees = Math.sqrt(addLiquidityValuePostFees);
  } else {
    dlpPostFees = (addLiquidityValuePostFees * binShares) / binLiquidityValuePostFees;
  };
  
  const minDlp = Math.floor(dlpPostFees * (1 - slippageTolerance / 1e2));

  return {
    minDlp,
    xAmountFeesLiquidity: Math.ceil(xAmountFeesLiquidity),
    yAmountFeesLiquidity: Math.ceil(yAmountFeesLiquidity)
  };
};

const prepareBinsForAdd = (poolBins, userPositions, activeBinId, binsToAdd) => {
  const userPositionBinsMap = new Map(
    (Array.isArray(userPositions?.bins)
      ? userPositions.bins
      : []).map(bin => [Number(bin.bin_id), bin])
  );
  
  return binsToAdd.map(addBin => {
    const poolBin = poolBins.bins?.find(b => b.bin_id === addBin.binId);
    
    if (!poolBin) throw new Error(`Bin ${addBin.binId} not found in pool`);
    
    if (addBin.binId < activeBinId && addBin.xAmount > 0) {
      throw new Error('Only yToken can be added to bins below the active bin');
    };
    
    if (addBin.binId > activeBinId && addBin.yAmount > 0) {
      throw new Error('Only xToken can be added to bins above the active bin');
    };
    
    if (addBin.binId === activeBinId && addBin.xAmount === 0 && addBin.yAmount === 0) {
      throw new Error('Active bin requires at least one token amount to be greater than 0');
    };

    return {
      isActiveBin: addBin.binId === activeBinId,
      binId: addBin.binId,
      xAmount: Math.floor(addBin.xAmount),
      yAmount: Math.floor(addBin.yAmount),
      binPrice: Number(poolBin.price),
      reserveX: Number(poolBin.reserve_x),
      reserveY: Number(poolBin.reserve_y),
      binShares: Number(poolBin.liquidity ?? 0),
      userLiquidity: userPositionBinsMap.get(addBin.binId)?.userLiquidity || 0,
      hasEverAddedToBin: userPositionBinsMap.has(addBin.binId)
    };
  });
};

const executeAddLiquidity = async (pool, preparedBins) => {
  const routerContractAddress = LIQUIDITY_ROUTER_CONTRACT.split('.')[0];
  const routerContractName = LIQUIDITY_ROUTER_CONTRACT.split('.')[1];
  
  const poolContractAddress = pool.poolContract.split('.')[0];
  const poolContractName = pool.poolContract.split('.')[1];
  
  const xTokenContractAddress = pool.tokenX.split('.')[0];
  const xTokenContractName = pool.tokenX.split('.')[1];
  const tokenXAssetName = await getTokenAssetName(pool.tokenX);
  const tokenXAssetInfo = createAssetInfo(xTokenContractAddress, xTokenContractName, tokenXAssetName);
  
  const yTokenContractAddress = pool.tokenY.split('.')[0];
  const yTokenContractName = pool.tokenY.split('.')[1];
  const tokenYAssetName = await getTokenAssetName(pool.tokenY);
  const tokenYAssetInfo = createAssetInfo(yTokenContractAddress, yTokenContractName, tokenYAssetName);

  const poolFees = {
    xProtocolFee: pool.xProtocolFee,
    xProviderFee: pool.xProviderFee,
    xVariableFee: pool.xVariableFee,
    yProtocolFee: pool.yProtocolFee,
    yProviderFee: pool.yProviderFee,
    yVariableFee: pool.yVariableFee
  };

  const binAddPositions = preparedBins.map(bin => {
    const { minDlp, xAmountFeesLiquidity, yAmountFeesLiquidity } = calculateMinDlpForBin(bin, poolFees, SLIPPAGE_TOLERANCE);
    const maxXLiquidityFee = Math.ceil(xAmountFeesLiquidity * (1 + SLIPPAGE_TOLERANCE / 1e2));
    const maxYLiquidityFee = Math.ceil(yAmountFeesLiquidity * (1 + SLIPPAGE_TOLERANCE / 1e2));

    const xAmount = Math.floor(bin.xAmount);
    const yAmount = Math.floor(bin.yAmount);
    const minDlpInt = Math.floor(minDlp);

    return tupleCV({
      'pool-trait': principalCV(pool.poolContract),
      'x-token-trait': principalCV(pool.tokenX),
      'y-token-trait': principalCV(pool.tokenY),
      'bin-id': intCV(getSignedBinId(bin.binId)),
      'x-amount': uintCV(xAmount),
      'y-amount': uintCV(yAmount),
      'min-dlp': uintCV(minDlpInt),
      'max-x-liquidity-fee': uintCV(maxXLiquidityFee),
      'max-y-liquidity-fee': uintCV(maxYLiquidityFee)
    });
  });

  const totalXAmount = preparedBins.reduce((sum, bin) => sum + bin.xAmount, 0);
  const totalYAmount = preparedBins.reduce((sum, bin) => sum + bin.yAmount, 0);

  const postConditions = [];

  postConditions.push(
    makeStandardFungiblePostCondition(
      STACKS_PUBLIC_KEY,
      FungibleConditionCode.LessEqual,
      totalXAmount.toString(),
      tokenXAssetInfo
    )
  );

  postConditions.push(
    makeStandardFungiblePostCondition(
      STACKS_PUBLIC_KEY,
      FungibleConditionCode.LessEqual,
      totalYAmount.toString(),
      tokenYAssetInfo
    )
  );

  preparedBins.forEach(bin => {
    if (bin.hasEverAddedToBin) {
      postConditions.push(
        makeStandardNonFungiblePostCondition(
          STACKS_PUBLIC_KEY,
          NonFungibleConditionCode.Sends,
          createAssetInfo(poolContractAddress, poolContractName, 'pool-token-id'),
          tupleCV({
            'token-id': uintCV(bin.binId),
            'owner': principalCV(STACKS_PUBLIC_KEY)
          })
        )
      );
    };
  });

  const txOptions = {
    contractAddress: routerContractAddress,
    contractName: routerContractName,
    functionName: 'add-liquidity-multi',
    functionArgs: [listCV(binAddPositions)],
    senderKey: STACKS_PRIVATE_KEY,
    network: stacksNetwork,
    fee: TRANSACTION_FEE_RATE,
    postConditions: USE_POST_CONDITIONS ? postConditions : [],
    postConditionMode: USE_POST_CONDITIONS ? PostConditionMode.Deny : PostConditionMode.Allow,
    anchorMode: 3
  };

  return txOptions;
};

const calculateBinWithdrawalAmounts = (bin, withdrawalPercentage, slippageTolerance = 1, activeBinId = null) => {
  if (withdrawalPercentage < 0 || withdrawalPercentage > 100) throw new Error('withdrawalPercentage must be between 0 and 100');
  if (bin.userLiquidity === 0 || bin.liquidity === 0) return { liquidityToRemove: 0, minXAmount: 0, minYAmount: 0 };
  const percentageDecimal = withdrawalPercentage / 1e2;
  const liquidityToRemove = Math.floor(bin.userLiquidity * percentageDecimal);
  const percentageOfBin = liquidityToRemove / bin.liquidity;

  let minXAmount = 0;
  let minYAmount = 0;

  if (USE_MIN_RECEIVED) {
    const slippageMultiplier = 1 - (slippageTolerance / 1e2);
    minXAmount = Math.floor(bin.reserveX * percentageOfBin * slippageMultiplier);
    minYAmount = Math.floor(bin.reserveY * percentageOfBin * slippageMultiplier);
  };

  if (!USE_MIN_RECEIVED || (minXAmount === 0 && minYAmount === 0)) {
    if (activeBinId !== null) {
      if (bin.binId > activeBinId) {
        minXAmount = 1;
        minYAmount = 0;
      } else if (bin.binId < activeBinId) {
        minXAmount = 0;
        minYAmount = 1;
      } else {
        if (bin.reserveX > 0 && bin.reserveY > 0) {
          minXAmount = bin.reserveX >= bin.reserveY ? 1 : 0;
          minYAmount = bin.reserveY >= bin.reserveX ? 1 : 0;
        } else if (bin.reserveX > 0) {
          minXAmount = 1;
          minYAmount = 0;
        } else if (bin.reserveY > 0) {
          minXAmount = 0;
          minYAmount = 1;
        } else {
          minXAmount = 1;
          minYAmount = 1;
        };
      };
    } else {
      minXAmount = 1;
      minYAmount = 1;
    };
  };

  return {
    liquidityToRemove,
    minXAmount,
    minYAmount
  };
};

const prepareBinsForWithdraw = (poolBins, userPositions, withdrawalPercentage, activeBinId = null) => {
  const userPositionBinsMap = new Map(
    (Array.isArray(userPositions?.bins)
      ? userPositions.bins
      : []).map(bin => [bin.bin_id, bin]));

  return userPositions.bins
    .filter(bin => bin.userLiquidity > 0)
    .map(bin => {
      const binId = Number(bin.bin_id);
      const poolBin = poolBins.bins?.find(b => b.bin_id === binId);
      
      if (!poolBin) throw new Error(`Bin ${binId} not found in pool`);

      return {
        binId,
        userLiquidity: bin.userLiquidity,
        liquidity: Number(poolBin.liquidity),
        reserveX: Number(poolBin.reserve_x),
        reserveY: Number(poolBin.reserve_y),
        withdrawalPercentage,
        activeBinId,
        hasEverAddedToBin: userPositionBinsMap.has(bin.bin_id)
      };
    });
};

const executeWithdrawLiquidity = async (pool, preparedBins) => {
  const routerContractAddress = LIQUIDITY_ROUTER_CONTRACT.split('.')[0];
  const routerContractName = LIQUIDITY_ROUTER_CONTRACT.split('.')[1];
  
  const poolContractAddress = pool.poolContract.split('.')[0];
  const poolContractName = pool.poolContract.split('.')[1];
  const poolContractAssetName = 'pool-token';
  const poolContractAssetInfo = createAssetInfo(poolContractAddress, poolContractName, poolContractAssetName);
  
  const xTokenContractAddress = pool.tokenX.split('.')[0];
  const xTokenContractName = pool.tokenX.split('.')[1];
  const tokenXAssetName = await getTokenAssetName(pool.tokenX);
  const tokenXAssetInfo = createAssetInfo(xTokenContractAddress, xTokenContractName, tokenXAssetName);
  
  const yTokenContractAddress = pool.tokenY.split('.')[0];
  const yTokenContractName = pool.tokenY.split('.')[1];
  const tokenYAssetName = await getTokenAssetName(pool.tokenY);
  const tokenYAssetInfo = createAssetInfo(yTokenContractAddress, yTokenContractName, tokenYAssetName);

  const { binWithdrawalPositions, totalLiquidityRemoved, totalMinXAmount, totalMinYAmount } = preparedBins.reduce(
    (acc, bin) => {
      const amounts = calculateBinWithdrawalAmounts(bin, bin.withdrawalPercentage, SLIPPAGE_TOLERANCE, bin.activeBinId);
      
      return {
        binWithdrawalPositions: [
          ...acc.binWithdrawalPositions,
          tupleCV({
            'pool-trait': principalCV(pool.poolContract),
            'x-token-trait': principalCV(pool.tokenX),
            'y-token-trait': principalCV(pool.tokenY),
            'bin-id': intCV(getSignedBinId(bin.binId)),
            'amount': uintCV(amounts.liquidityToRemove),
            'min-x-amount': uintCV(amounts.minXAmount),
            'min-y-amount': uintCV(amounts.minYAmount)
          })
        ],
        totalLiquidityRemoved: acc.totalLiquidityRemoved + amounts.liquidityToRemove,
        totalMinXAmount: acc.totalMinXAmount + amounts.minXAmount,
        totalMinYAmount: acc.totalMinYAmount + amounts.minYAmount
      };
    },
    { binWithdrawalPositions: [], totalLiquidityRemoved: 0, totalMinXAmount: 0, totalMinYAmount: 0 }
  );

  const postConditions = [];

  postConditions.push(
    makeStandardFungiblePostCondition(
      STACKS_PUBLIC_KEY,
      FungibleConditionCode.Equal,
      totalLiquidityRemoved.toString(),
      poolContractAssetInfo
    )
  );

  postConditions.push(
    makeContractFungiblePostCondition(
      poolContractAddress,
      poolContractName,
      FungibleConditionCode.GreaterEqual,
      totalMinXAmount.toString(),
      tokenXAssetInfo
    )
  );

  postConditions.push(
    makeContractFungiblePostCondition(
      poolContractAddress,
      poolContractName,
      FungibleConditionCode.GreaterEqual,
      totalMinYAmount.toString(),
      tokenYAssetInfo
    )
  );

  preparedBins.forEach(bin => {
    if (bin.hasEverAddedToBin) {
      postConditions.push(
        makeStandardNonFungiblePostCondition(
          STACKS_PUBLIC_KEY,
          NonFungibleConditionCode.Sends,
          createAssetInfo(
            poolContractAddress,
            poolContractName,
            'pool-token-id'
          ),
          tupleCV({
            'token-id': uintCV(bin.binId),
            'owner': principalCV(STACKS_PUBLIC_KEY)
          })
        )
      );
    };
  });

  const txOptions = {
    contractAddress: routerContractAddress,
    contractName: routerContractName,
    functionName: 'withdraw-liquidity-multi',
    functionArgs: [listCV(binWithdrawalPositions)],
    senderKey: STACKS_PRIVATE_KEY,
    network: stacksNetwork,
    fee: TRANSACTION_FEE_RATE,
    postConditions: USE_POST_CONDITIONS ? postConditions : [],
    postConditionMode: USE_POST_CONDITIONS ? PostConditionMode.Deny : PostConditionMode.Allow,
    anchorMode: 3
  };

  return txOptions;
};

const executeRandomAddLiquidity = async () => {
  const availablePools = POOLS.filter(pool => !isPoolOnCooldown(pool.poolId));
  
  if (availablePools.length === 0) return console.log(`Skipping add liquidity: All pools are on cooldown`);

  const pool = sample(availablePools);

  const stxBalance = await getSTXBalance(STACKS_PUBLIC_KEY);
  if (stxBalance - TRANSACTION_FEE_RATE <= 0) return console.log(`Skipping add liquidity: Insufficient STX balance for transaction fees`);

  console.log(`Fetching pool bins for pool ${pool.poolId}...`);
  const poolBins = await getPoolBins(pool.poolId);

  if (!poolBins.bins || poolBins.bins.length === 0) return console.log(`Skipping add liquidity: No bins found for pool ${pool.poolId}`);

  console.log(`Fetching user position bins for pool ${pool.poolId}...`);
  const userPositions = await getUserPositionBins(STACKS_PUBLIC_KEY, pool.poolId);

  const activeBinId = poolBins.active_bin_id;
  if (!activeBinId) return console.log(`Skipping add liquidity: No active bin ID found`);

  const tokenXBalance = await getTokenBalance(pool.tokenX, STACKS_PUBLIC_KEY);
  const tokenYBalance = await getTokenBalance(pool.tokenY, STACKS_PUBLIC_KEY);

  if (tokenXBalance === 0 && tokenYBalance === 0) return console.log(`Skipping add liquidity: No token balances for pool ${pool.poolId}`);

  const numBinsToAdd = random(MIN_LIQUIDITY_BINS, Math.min(MAX_LIQUIDITY_BINS, poolBins.bins.length));
  const availableBins = poolBins.bins.filter(bin => {
    const binId = bin.bin_id;
    if (binId > activeBinId) return tokenXBalance > 0;
    if (binId < activeBinId) return tokenYBalance > 0;
    return tokenXBalance > 0 || tokenYBalance > 0;
  });

  if (availableBins.length === 0) return console.log(`Skipping add liquidity: No suitable bins for available balances`);

  const selectedBins = [];
  for (let i = 0; i < Math.min(numBinsToAdd, availableBins.length); i++) {
    const bin = sample(availableBins.filter(b => !selectedBins.find(sb => sb.bin_id === b.bin_id)));
    if (bin) selectedBins.push(bin);
  };

  if (selectedBins.length === 0) return console.log(`Skipping add liquidity: Could not select bins`);

  const binsToAdd = selectedBins.map(bin => {
    const binId = bin.bin_id;
    let xAmount = 0;
    let yAmount = 0;

    if (binId > activeBinId) {
      const randomPercent = MIN_BALANCE_PERCENT + Math.random() * (MAX_BALANCE_PERCENT - MIN_BALANCE_PERCENT);
      xAmount = Math.floor(tokenXBalance * (randomPercent / 100));
    } else if (binId < activeBinId) {
      const randomPercent = MIN_BALANCE_PERCENT + Math.random() * (MAX_BALANCE_PERCENT - MIN_BALANCE_PERCENT);
      yAmount = Math.floor(tokenYBalance * (randomPercent / 100));
    } else {
      const randomPercent = MIN_BALANCE_PERCENT + Math.random() * (MAX_BALANCE_PERCENT - MIN_BALANCE_PERCENT);
      if (Math.random() < 0.5 && tokenXBalance > 0) {
        xAmount = Math.floor(tokenXBalance * (randomPercent / 100));
      };
      if (Math.random() < 0.5 && tokenYBalance > 0) {
        yAmount = Math.floor(tokenYBalance * (randomPercent / 100));
      };
      if (xAmount === 0 && yAmount === 0) {
        if (tokenXBalance > 0) {
          xAmount = Math.floor(tokenXBalance * (randomPercent / 100));
        } else if (tokenYBalance > 0) {
          yAmount = Math.floor(tokenYBalance * (randomPercent / 100));
        };
      };
    };

    return {
      binId,
      xAmount,
      yAmount
    };
  }).filter(bin => bin.xAmount > 0 || bin.yAmount > 0);

  const totalXAmount = binsToAdd.reduce((sum, bin) => sum + bin.xAmount, 0);
  const totalYAmount = binsToAdd.reduce((sum, bin) => sum + bin.yAmount, 0);

  const tokenXMaxAmount = ALLOWED_TOKENS[pool.tokenX];
  const tokenYMaxAmount = ALLOWED_TOKENS[pool.tokenY];

  let xScaleFactor = 1;
  let yScaleFactor = 1;

  if (tokenXMaxAmount && totalXAmount > tokenXMaxAmount) xScaleFactor = tokenXMaxAmount / totalXAmount;
  if (tokenYMaxAmount && totalYAmount > tokenYMaxAmount) yScaleFactor = tokenYMaxAmount / totalYAmount;

  const scaledBinsToAdd = binsToAdd.map(bin => ({
    binId: bin.binId,
    xAmount: Math.floor(bin.xAmount * xScaleFactor),
    yAmount: Math.floor(bin.yAmount * yScaleFactor)
  })).filter(bin => bin.xAmount > 0 || bin.yAmount > 0);

  if (scaledBinsToAdd.length === 0) return console.log(`Skipping add liquidity: No valid bins to add`);

  console.log(`Preparing ${scaledBinsToAdd.length} bin(s) for add liquidity...`);
  const preparedBins = prepareBinsForAdd(poolBins, userPositions, activeBinId, scaledBinsToAdd);

  if (DEBUG_MODE) {
    const finalTotalXAmount = preparedBins.reduce((sum, b) => sum + b.xAmount, 0);
    const finalTotalYAmount = preparedBins.reduce((sum, b) => sum + b.yAmount, 0);
    const wasXAmountCapped = tokenXMaxAmount && totalXAmount > tokenXMaxAmount;
    const wasYAmountCapped = tokenYMaxAmount && totalYAmount > tokenYMaxAmount;
    
    const debugInfo = {
      poolId: pool.poolId,
      poolContract: pool.poolContract,
      routerContract: LIQUIDITY_ROUTER_CONTRACT,
      functionName: 'add-liquidity-multi',
      tokenX: pool.tokenX,
      tokenY: pool.tokenY,
      tokenXBalance,
      tokenYBalance,
      activeBinId,
      binsToAdd: scaledBinsToAdd.length,
      totalXAmount: finalTotalXAmount,
      totalYAmount: finalTotalYAmount,
      originalTotalXAmount: totalXAmount,
      originalTotalYAmount: totalYAmount,
      wasXAmountCapped,
      wasYAmountCapped,
      tokenXMaxAmount: tokenXMaxAmount || 'unlimited',
      tokenYMaxAmount: tokenYMaxAmount || 'unlimited',
      preparedBins: preparedBins.map(bin => ({
        binId: bin.binId,
        xAmount: bin.xAmount,
        yAmount: bin.yAmount,
        isActiveBin: bin.isActiveBin
      })),
      fee: TRANSACTION_FEE_RATE,
      slippageTolerance: SLIPPAGE_TOLERANCE,
      postConditionsCount: USE_POST_CONDITIONS ? (2 + preparedBins.filter(b => b.hasEverAddedToBin).length) : 0,
      usePostConditions: USE_POST_CONDITIONS
    };
    return console.log('Add liquidity prepared (debug mode):', debugInfo);
  };

  console.log(`Executing add liquidity for ${preparedBins.length} bin(s)...`);
  const txOptions = await executeAddLiquidity(pool, preparedBins);

  let currentNonce = await getNonce(STACKS_PUBLIC_KEY, stacksNetwork);

  for (let i = 0; i < TRANSACTIONS_TO_BROADCAST; i++) {
    const transaction = await makeContractCall({
      ...txOptions,
      nonce: currentNonce + BigInt(i)
    });
    
    const broadcastResponse = await broadcastTransaction(transaction, stacksNetwork);

    if (broadcastResponse.error) throw new Error(`Broadcast failed for transaction ${i + 1}/${TRANSACTIONS_TO_BROADCAST}: ${broadcastResponse.reason} (${broadcastResponse.reason_data})`);

    const totalXAmount = preparedBins.reduce((sum, b) => sum + b.xAmount, 0);
    const totalYAmount = preparedBins.reduce((sum, b) => sum + b.yAmount, 0);
    const postConditionsCount = USE_POST_CONDITIONS ? (2 + preparedBins.filter(b => b.hasEverAddedToBin).length) : 0;

    console.log(`Add liquidity executed (${i + 1}/${TRANSACTIONS_TO_BROADCAST}):`, {
      txId: broadcastResponse.txid,
      nonce: (currentNonce + BigInt(i)).toString(),
      fee: TRANSACTION_FEE_RATE,
      routerContract: LIQUIDITY_ROUTER_CONTRACT,
      functionName: 'add-liquidity-multi',
      poolId: pool.poolId,
      poolContract: pool.poolContract,
      tokenX: pool.tokenX,
      tokenY: pool.tokenY,
      bins: preparedBins.length,
      totalXAmount,
      totalYAmount,
      postConditionsCount,
      usePostConditions: USE_POST_CONDITIONS
    });
  };

  setPoolCooldown(pool.poolId);
};

const executeRandomWithdrawLiquidity = async () => {
  const availablePools = POOLS.filter(pool => !isPoolOnCooldown(pool.poolId));
  
  if (availablePools.length === 0) return console.log(`Skipping withdraw liquidity: All pools are on cooldown`);

  const pool = sample(availablePools);

  const stxBalance = await getSTXBalance(STACKS_PUBLIC_KEY);
  if (stxBalance - TRANSACTION_FEE_RATE <= 0) return console.log(`Skipping withdraw liquidity: Insufficient STX balance for transaction fees`);

  console.log(`Fetching pool bins for pool ${pool.poolId}...`);
  
  const poolBins = await getPoolBins(pool.poolId);
  
  const activeBinId = poolBins.active_bin_id || pool.activeBinId;
  if (!activeBinId) return console.log(`Skipping withdraw liquidity: No active bin ID found`);

  console.log(`Fetching user position bins for pool ${pool.poolId}...`);
  const userPositions = await getUserPositionBins(STACKS_PUBLIC_KEY, pool.poolId);

  if (!userPositions.bins || userPositions.bins.length === 0) return console.log(`Skipping withdraw liquidity: No positions found for pool ${pool.poolId}`);

  const binsWithLiquidity = userPositions.bins.filter(bin => bin.userLiquidity > 0);
  
  if (binsWithLiquidity.length === 0) return console.log(`Skipping withdraw liquidity: No bins with liquidity for pool ${pool.poolId}`);

  const withdrawalPercentage = random(MIN_WITHDRAWAL_PERCENT, MAX_WITHDRAWAL_PERCENT);
  const numBinsToWithdraw = random(MIN_LIQUIDITY_BINS, Math.min(MAX_LIQUIDITY_BINS, binsWithLiquidity.length));

  const selectedBins = [];
  for (let i = 0; i < numBinsToWithdraw; i++) {
    const bin = sample(binsWithLiquidity.filter(b => !selectedBins.find(sb => sb.bin_id === b.bin_id)));
    if (bin) selectedBins.push(bin);
  };

  if (selectedBins.length === 0) return console.log(`Skipping withdraw liquidity: Could not select bins`);

  console.log(`Preparing ${selectedBins.length} bin(s) for withdraw liquidity (${withdrawalPercentage}%)...`);
  const preparedBins = prepareBinsForWithdraw(poolBins, { bins: selectedBins }, withdrawalPercentage, activeBinId);

  if (preparedBins.length === 0) return console.log(`Skipping withdraw liquidity: No valid bins to withdraw`);

  if (DEBUG_MODE) {
    const totalLiquidityRemoved = preparedBins.reduce((sum, bin) => {
      const amounts = calculateBinWithdrawalAmounts(bin, bin.withdrawalPercentage, SLIPPAGE_TOLERANCE, bin.activeBinId);
      return sum + amounts.liquidityToRemove;
    }, 0);
    const postConditionsCount = USE_POST_CONDITIONS ? (3 + preparedBins.filter(b => b.hasEverAddedToBin).length) : 0;

    const debugInfo = {
      poolId: pool.poolId,
      poolContract: pool.poolContract,
      routerContract: LIQUIDITY_ROUTER_CONTRACT,
      functionName: 'withdraw-liquidity-multi',
      tokenX: pool.tokenX,
      tokenY: pool.tokenY,
      binsToWithdraw: preparedBins.length,
      withdrawalPercentage,
      totalLiquidityRemoved,
      preparedBins: preparedBins.map(b => ({
        binId: b.binId,
        userLiquidity: b.userLiquidity,
        liquidityToRemove: calculateBinWithdrawalAmounts(b, b.withdrawalPercentage, SLIPPAGE_TOLERANCE, b.activeBinId).liquidityToRemove
      })),
      fee: TRANSACTION_FEE_RATE,
      slippageTolerance: SLIPPAGE_TOLERANCE,
      postConditionsCount,
      usePostConditions: USE_POST_CONDITIONS
    };
    return console.log('Withdraw liquidity prepared (debug mode):', debugInfo);
  };

  console.log(`Executing withdraw liquidity for ${preparedBins.length} bin(s)...`);
  const txOptions = await executeWithdrawLiquidity(pool, preparedBins);

  const totalLiquidityRemoved = preparedBins.reduce((sum, bin) => {
    const amounts = calculateBinWithdrawalAmounts(bin, bin.withdrawalPercentage, SLIPPAGE_TOLERANCE, bin.activeBinId);
    return sum + amounts.liquidityToRemove;
  }, 0);

  let currentNonce = await getNonce(STACKS_PUBLIC_KEY, stacksNetwork);

  for (let i = 0; i < TRANSACTIONS_TO_BROADCAST; i++) {
    const transaction = await makeContractCall({
      ...txOptions,
      nonce: currentNonce + BigInt(i)
    });
    
    const broadcastResponse = await broadcastTransaction(transaction, stacksNetwork);

    if (broadcastResponse.error) throw new Error(`Broadcast failed for transaction ${i + 1}/${TRANSACTIONS_TO_BROADCAST}: ${broadcastResponse.reason} (${broadcastResponse.reason_data})`);

    const postConditionsCount = USE_POST_CONDITIONS ? (3 + preparedBins.filter(b => b.hasEverAddedToBin).length) : 0;

    console.log(`Withdraw liquidity executed (${i + 1}/${TRANSACTIONS_TO_BROADCAST}):`, {
      txId: broadcastResponse.txid,
      nonce: (currentNonce + BigInt(i)).toString(),
      fee: TRANSACTION_FEE_RATE,
      routerContract: LIQUIDITY_ROUTER_CONTRACT,
      functionName: 'withdraw-liquidity-multi',
      poolId: pool.poolId,
      poolContract: pool.poolContract,
      tokenX: pool.tokenX,
      tokenY: pool.tokenY,
      bins: preparedBins.length,
      withdrawalPercentage,
      totalLiquidityRemoved,
      postConditionsCount,
      usePostConditions: USE_POST_CONDITIONS
    });
  };

  setPoolCooldown(pool.poolId);
};

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const mainLoop = async () => {
  console.log('');
  console.log('Starting HODLMM liquidity helper...');
  
  try {
    console.log('Fetching HODLMM pools...');

    POOLS = await getPools();
    if (POOLS.length === 0) throw new Error(`No pools found. ${ALLOW_ALL_TOKENS ? 'Check network connection' : 'Check ALLOWED_TOKENS configuration'}`);
  } catch (error) {
    console.error(`Error fetching pools: ${error.message}`);
    throw error;
  };

  console.log('');
  console.log(`Pools: ${POOLS.length}`);
  console.log(`Public key: ${STACKS_PUBLIC_KEY}`);
  console.log(`Stacks network version: ${STACKS_NETWORK_VERSION.charAt(0).toUpperCase() + STACKS_NETWORK_VERSION.slice(1)}`);
  console.log(`Transactions to broadcast: ${TRANSACTIONS_TO_BROADCAST}`);
  console.log(`Transaction fee rate: ${TRANSACTION_FEE_RATE} uSTX`);
  console.log(`Transaction interval: ${TRANSACTION_INTERVAL_MS}ms`);
  console.log(`Pool cooldown: ${POOL_COOLDOWN_MS}ms`);
  console.log(`Balance percent range: ${MIN_BALANCE_PERCENT}% - ${MAX_BALANCE_PERCENT}%`);
  console.log(`Bins per transaction range: ${MIN_LIQUIDITY_BINS} - ${MAX_LIQUIDITY_BINS} bins`);
  console.log(`Withdrawal percent range: ${MIN_WITHDRAWAL_PERCENT}% - ${MAX_WITHDRAWAL_PERCENT}%`);
  console.log(`Slippage tolerance: ${SLIPPAGE_TOLERANCE}%`);
  console.log(`Min received: ${USE_MIN_RECEIVED ? 'Enabled' : 'Disabled'}`);
  console.log(`Post conditions: ${USE_POST_CONDITIONS ? 'Enabled' : 'Disabled'}`);
  console.log(`Allow all tokens: ${ALLOW_ALL_TOKENS ? 'Enabled' : 'Disabled'}`);
  console.log(`Debug mode: ${DEBUG_MODE ? 'Enabled' : 'Disabled'}`);

  while (true) {
    try {
      console.log('');
      if (Math.random() < 0.5) {
        await executeRandomAddLiquidity();
      } else {
        await executeRandomWithdrawLiquidity();
      };
    } catch (error) {
      console.error('Error executing liquidity transaction:', error.message);
      if (error.stack) {
        console.error(error.stack);
      };
    };
    await delay(TRANSACTION_INTERVAL_MS);
  };
};

mainLoop();