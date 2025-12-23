// swap_helper.js

const envPath = process.argv[2] || '.env';
require('dotenv').config({ path: envPath });

const {
  makeContractCall,
  broadcastTransaction,
  uintCV,
  intCV,
  callReadOnlyFunction,
  principalCV,
  trueCV,
  falseCV,
  tupleCV,
  listCV,
  PostConditionMode,
  FungibleConditionCode,
  makeStandardFungiblePostCondition,
  makeContractFungiblePostCondition,
  createAssetInfo,
  getNonce,
} = require('@stacks/transactions');
const { StacksMainnet, StacksTestnet } = require('@stacks/network');
const { sample } = require('lodash');

const BFF_API_URL = process.env.BFF_API_URL;
const STACKS_PUBLIC_KEY = process.env.STACKS_PUBLIC_KEY;
const STACKS_PRIVATE_KEY = process.env.STACKS_PRIVATE_KEY;
const STACKS_API_URL = process.env.STACKS_API_URL;
const STACKS_NODE_URL = process.env.STACKS_NODE_URL;
const STACKS_NODE_KEY = process.env.STACKS_NODE_KEY;
const STACKS_NETWORK_VERSION = process.env.STACKS_NETWORK_VERSION;
const CUSTOM_SWAP_ROUTER_CONTRACT = process.env.CUSTOM_SWAP_ROUTER_CONTRACT;
const TRANSACTIONS_TO_BROADCAST = parseInt(process.env.TRANSACTIONS_TO_BROADCAST, 10);
const TRANSACTION_FEE_RATE = parseInt(process.env.TRANSACTION_FEE_RATE, 10);
const TRANSACTION_INTERVAL_MS = parseInt(process.env.TRANSACTION_INTERVAL_MS, 10);
const POOL_COOLDOWN_MS = parseInt(process.env.POOL_COOLDOWN_MS, 10);
const MAX_PENDING_TRANSACTIONS = parseInt(process.env.MAX_PENDING_TRANSACTIONS, 10);
const MIN_BALANCE_PERCENT = parseFloat(process.env.MIN_BALANCE_PERCENT, 10);
const MAX_BALANCE_PERCENT = parseFloat(process.env.MAX_BALANCE_PERCENT, 10);
const MIN_SWAP_BINS = parseInt(process.env.MIN_SWAP_BINS, 10);
const MAX_SWAP_BINS = parseInt(process.env.MAX_SWAP_BINS, 10);
const TARGET_SWAP_BINS_MIN = parseInt(process.env.TARGET_SWAP_BINS_MIN, 10);
const TARGET_SWAP_BINS_MAX = parseInt(process.env.TARGET_SWAP_BINS_MAX, 10);
const MAX_SWAP_AMOUNT = process.env.MAX_SWAP_AMOUNT ? BigInt(process.env.MAX_SWAP_AMOUNT) : null;
const SLIPPAGE_TOLERANCE = parseInt(process.env.SLIPPAGE_TOLERANCE, 10);
const BIN_SLIPPAGE_TOLERANCE = parseInt(process.env.BIN_SLIPPAGE_TOLERANCE, 10);
const USE_MIN_RECEIVED = process.env.USE_MIN_RECEIVED === 'true';
const USE_POST_CONDITIONS = process.env.USE_POST_CONDITIONS === 'true';
const USE_SIMPLE_SWAP = process.env.USE_SIMPLE_SWAP === 'true';
const ADDITIONAL_STEPS_PER_GROUP = parseInt(process.env.ADDITIONAL_STEPS_PER_GROUP || '0', 10);
const ALLOW_ALL_TOKENS = process.env.ALLOW_ALL_TOKENS === 'true';
const DEBUG_MODE = process.env.DEBUG_MODE === 'true';

// Allowed tokens and their per-transaction maximums (do not scale)
const ALLOWED_TOKENS = {
  // Mainnet tokens
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tstx-v-0-2': 150000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tdog-v-0-2': 1050000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tusdc-v-0-2': 150000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tusdh-v-0-1': 10000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tbtc-v-0-2': 0.1,

  // Testnet tokens
  'ST1WA4CXFR54B1W42R7NSMXEQYQTTMB3CXQM63ETH.token-tstx-v-0-1': 150000,
  'ST1WA4CXFR54B1W42R7NSMXEQYQTTMB3CXQM63ETH.token-tusdc-v-0-1': 150000,
  'ST1WA4CXFR54B1W42R7NSMXEQYQTTMB3CXQM63ETH.token-tusdh-v-0-1': 10000,
  'ST1WA4CXFR54B1W42R7NSMXEQYQTTMB3CXQM63ETH.token-tbtc-v-0-1': 0.1
};

// Maximum total steps per simple swap transaction (294 max on-chain before hitting limits)
const MAX_TOTAL_STEPS = 290;

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

const getNextNonce = async () => {
  try {
    const isMainnet = String(STACKS_NETWORK_VERSION || 'mainnet').toLowerCase() === 'mainnet';
    
    const defaultUrl = isMainnet
      ? 'https://api.mainnet.hiro.so'
      : 'https://api.testnet.hiro.so'; 
    const url = `${STACKS_API_URL || defaultUrl}/extended/v1/address/${STACKS_PUBLIC_KEY}/nonces`;
    
    const headers = {};
    if (STACKS_NODE_KEY) headers['X-API-Key'] = STACKS_NODE_KEY;
    
    const response = await fetch(url, { headers });
    if (!response.ok) throw new Error(`API returned status '${response.status}' - '${response.statusText}'`);
    
    const responseData = await response.json();
    if (responseData) {
      const pendingCount = responseData.pending_nonce_count || 0;
      
      if (
        responseData.detected_missing_nonces &&
        responseData.detected_missing_nonces.length > 0
      ) {
        const missingNonces = responseData.detected_missing_nonces;
        const nextNonce = Math.min(...missingNonces);
        console.log(`Using missing nonce: ${nextNonce} (missing nonces: ${missingNonces.join(', ')}, pending: ${pendingCount})`);
        return { nonce: BigInt(nextNonce), pendingCount };
      } else if (responseData.possible_next_nonce !== undefined) {
        const nextNonce = responseData.possible_next_nonce;
        console.log(`Using possible next nonce: ${nextNonce} (pending: ${pendingCount})`);
        return { nonce: BigInt(nextNonce), pendingCount };
      } else {
        throw new Error('Failed to retrieve next nonce: invalid response format');
      };
    } else {
      throw new Error('Failed to retrieve next nonce: empty response');
    };
  } catch (error) {
    console.error(`Error getting next nonce: ${error.message}`);
    
    console.log('Falling back to standard getNonce...');
    try {
      const fallbackNonce = await getNonce(STACKS_PUBLIC_KEY, stacksNetwork);
      return { nonce: fallbackNonce, pendingCount: 0 };
    } catch (fallbackError) {
      throw new Error(`Failed to retrieve next nonce: ${error.message} (fallback also failed: ${fallbackError.message})`);
    };
  };
};

const parseContract = (contract) => {
  const [address, name] = contract.split('.');
  return { address, name };
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

const getDirectionalSwapKey = (inputToken, outputToken) => `${inputToken}->${outputToken}`;

const isPoolOnCooldown = (inputToken, outputToken) => {
  const swapKey = getDirectionalSwapKey(inputToken, outputToken);
  const lastSwapTime = poolCooldowns.get(swapKey);
  
  if (!lastSwapTime) return false;
  
  const elapsed = Date.now() - lastSwapTime;
  return elapsed < POOL_COOLDOWN_MS;
};

const setPoolCooldown = (inputToken, outputToken) => {
  const swapKey = getDirectionalSwapKey(inputToken, outputToken);
  poolCooldowns.set(swapKey, Date.now());
};

const getPools = async () => {
  const response = await fetch(BFF_API_URL + '/app/v1/pools', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
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
    
    if (!isDLMM || !isActive || !tokenX || !tokenY) return false;
    
    if (ALLOW_ALL_TOKENS) return true;
    
    const hasTokenX = ALLOWED_TOKENS.hasOwnProperty(tokenX);
    const hasTokenY = ALLOWED_TOKENS.hasOwnProperty(tokenY);
    
    return hasTokenX && hasTokenY;
  });

  return filteredPools.map(pool => ({
    tokenX: pool.tokens.tokenX.contract,
    tokenY: pool.tokens.tokenY.contract
  }));
};

const getMultiQuote = async (inputToken, outputToken, amountIn) => {
  const response = await fetch(BFF_API_URL + '/quotes/v1/quote/multi', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input_token: inputToken,
      output_token: outputToken,
      amount_in: amountIn.toString(),
      amm_strategy: 'best',
      slippage_tolerance: SLIPPAGE_TOLERANCE,
    })
  });

  if (!response.ok) throw new Error(`Multi quote returned ${response.status} with message: ${await response.text()}`);

  const data = await response.json();

  if (!data.success) throw new Error(`Multi quote error: ${data.error}`);
  if (!data.routes || data.routes.length === 0) throw new Error('No routes found');

  return data;
};

const getSwapData = async (executionPath, amountIn, amountOut, inputToken, outputToken, inputDecimals, outputDecimals) => {
  const response = await fetch(BFF_API_URL + '/quotes/v1/swap', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      execution_path: executionPath,
      amount_in: amountIn.toString(),
      amount_out: amountOut,
      input_token: inputToken,
      output_token: outputToken,
      input_token_decimals: inputDecimals,
      output_token_decimals: outputDecimals,
      slippage_tolerance: SLIPPAGE_TOLERANCE,
      swap_parameters_type: USE_SIMPLE_SWAP ? 'simple' : 'full'
    })
  });

  if (!response.ok) throw new Error(`Swap data returned ${response.status} with message: ${await response.text()}`);

  const data = await response.json();

  if (!data.success) throw new Error(`Swap data error: ${data.error}`);

  return data;
};

const buildSwapMultiParams = (swapParamsTyped) => {
  return swapParamsTyped.map(param => {
    const value = param.value;
    return tupleCV({
      'pool-trait': principalCV(value['pool-trait'].value),
      'x-token-trait': principalCV(value['x-token-trait'].value),
      'y-token-trait': principalCV(value['y-token-trait'].value),
      'expected-bin-id': intCV(value['expected-bin-id'].value),
      'amount': uintCV(value['amount'].value),
      'min-received': uintCV(USE_MIN_RECEIVED ? value['min-received'].value : 0),
      'x-for-y': value['x-for-y'].type === 'true' ? trueCV() : falseCV()
    });
  });
};

const buildSwapSimpleMultiParams = (swapParamsTyped) => {
  if (swapParamsTyped.length === 0) return [];
  
  const groupsWithInitialSteps = swapParamsTyped.map(param => {
    const value = param.value;
    const apiMaxSteps = parseInt(value['max-steps'].value, 10);
    const initialMaxSteps = Math.max(1, Math.min(apiMaxSteps + ADDITIONAL_STEPS_PER_GROUP, 350));
    
    return {
      param: param,
      initialMaxSteps: initialMaxSteps
    };
  });
  
  const totalInitialSteps = groupsWithInitialSteps.reduce((sum, group) => sum + group.initialMaxSteps, 0);
  const scaleFactor = totalInitialSteps > MAX_TOTAL_STEPS ? MAX_TOTAL_STEPS / totalInitialSteps : 1;
  
  return groupsWithInitialSteps.map(group => {
    const value = group.param.value;
    const scaledMaxSteps = Math.max(1, Math.floor(group.initialMaxSteps * scaleFactor));
    
    return {
      'pool-trait': principalCV(value['pool-trait'].value),
      'x-token-trait': principalCV(value['x-token-trait'].value),
      'y-token-trait': principalCV(value['y-token-trait'].value),
      'amount': uintCV(value['amount'].value),
      'min-received': uintCV(USE_MIN_RECEIVED ? value['min-received'].value : 0),
      'x-for-y': value['x-for-y'].type === 'true' ? trueCV() : falseCV(),
      'max-steps': uintCV(scaledMaxSteps)
    };
  });
};

const buildSwapSimpleMultiParamsManual = (swapParamsTyped) => {
  if (swapParamsTyped.length === 0) return [];
  
  const orderedGroups = [];
  let currentGroup = null;
  
  swapParamsTyped.forEach((param) => {
    const value = param.value;
    const poolTrait = value['pool-trait'].value;
    const xTokenTrait = value['x-token-trait'].value;
    const yTokenTrait = value['y-token-trait'].value;
    const xForY = value['x-for-y'].type === 'true';
    
    const needsNewGroup = !currentGroup || 
      currentGroup['pool-trait'] !== poolTrait ||
      currentGroup['x-token-trait'] !== xTokenTrait ||
      currentGroup['y-token-trait'] !== yTokenTrait ||
      currentGroup['x-for-y'] !== xForY;
    
    if (needsNewGroup) {
      if (currentGroup) {
        const initialMaxSteps = Math.max(1, Math.min(currentGroup.binCount + ADDITIONAL_STEPS_PER_GROUP, 350));
        orderedGroups.push({
          'pool-trait': currentGroup['pool-trait'],
          'x-token-trait': currentGroup['x-token-trait'],
          'y-token-trait': currentGroup['y-token-trait'],
          'x-for-y': currentGroup['x-for-y'],
          'amount': currentGroup.amount,
          'min-received': currentGroup.minReceived,
          'binCount': currentGroup.binCount,
          'initialMaxSteps': initialMaxSteps
        });
      };

      currentGroup = {
        'pool-trait': poolTrait,
        'x-token-trait': xTokenTrait,
        'y-token-trait': yTokenTrait,
        'x-for-y': xForY,
        amount: BigInt(0),
        minReceived: BigInt(0),
        binCount: 0
      };
    };
    
    currentGroup.amount += BigInt(value['amount'].value);
    if (USE_MIN_RECEIVED) currentGroup.minReceived += BigInt(value['min-received'].value);
    currentGroup.binCount += 1;
  });
  
  if (currentGroup) {
    const initialMaxSteps = Math.max(1, Math.min(currentGroup.binCount + ADDITIONAL_STEPS_PER_GROUP, 350));
    orderedGroups.push({
      'pool-trait': currentGroup['pool-trait'],
      'x-token-trait': currentGroup['x-token-trait'],
      'y-token-trait': currentGroup['y-token-trait'],
      'x-for-y': currentGroup['x-for-y'],
      'amount': currentGroup.amount,
      'min-received': currentGroup.minReceived,
      'binCount': currentGroup.binCount,
      'initialMaxSteps': initialMaxSteps
    });
  };

  const totalInitialSteps = orderedGroups.reduce((sum, group) => sum + group.initialMaxSteps, 0);
  const scaleFactor = totalInitialSteps > MAX_TOTAL_STEPS ? MAX_TOTAL_STEPS / totalInitialSteps : 1;

  return orderedGroups.map(group => {
    const scaledMaxSteps = Math.max(1, Math.floor(group.initialMaxSteps * scaleFactor));
    return {
      'pool-trait': principalCV(group['pool-trait']),
      'x-token-trait': principalCV(group['x-token-trait']),
      'y-token-trait': principalCV(group['y-token-trait']),
      'amount': uintCV(group['amount'].toString()),
      'min-received': uintCV(group['min-received'].toString()),
      'x-for-y': group['x-for-y'] ? trueCV() : falseCV(),
      'max-steps': uintCV(scaledMaxSteps)
    };
  });
};

const buildPostConditions = (postConditions, minAmountOut) => {
  const conditions = [];

  for (let i = 0; i < postConditions.length; i++) {
    const pc = postConditions[i];
    const { address: tokenAddress, name: tokenName } = parseContract(pc.token_contract);
    const assetInfo = createAssetInfo(tokenAddress, tokenName, pc.token_asset_name);

    let amount = pc.amount;
    const isLastPostCondition = i === postConditions.length - 1;

    if (isLastPostCondition) {
      if (USE_MIN_RECEIVED) {
        amount = minAmountOut;
      } else {
        amount = '0';
      };
    };

    const conditionCode = pc.condition_code === 'less_than_or_equal_to' 
      ? FungibleConditionCode.LessEqual 
      : FungibleConditionCode.GreaterEqual;

    if (pc.sender_address === 'tx-sender') {
      conditions.push(
        makeStandardFungiblePostCondition(
          STACKS_PUBLIC_KEY,
          conditionCode,
          amount,
          assetInfo
        )
      );
    } else {
      conditions.push(
        makeContractFungiblePostCondition(
          pc.sender_address.split('.')[0],
          pc.sender_address.split('.')[1],
          conditionCode,
          amount,
          assetInfo
        )
      );
    };
  };

  return conditions;
};

const findOptimalSwapAmount = async (inputToken, outputToken, initialAmount, maxAmount) => {
  let currentAmount = BigInt(initialAmount);
  let minAmount = BigInt(1);
  let bestSwapData = null;
  let bestAmount = null;
  let bestRoute = null;
  let attempts = 0;
  const maxAttempts = 10;

  if (MAX_SWAP_AMOUNT && currentAmount > MAX_SWAP_AMOUNT) currentAmount = MAX_SWAP_AMOUNT;
  if (maxAmount && currentAmount > maxAmount) currentAmount = maxAmount;

  while (attempts < maxAttempts) {
    attempts++;
    
    try {
      const multiQuote = await getMultiQuote(inputToken, outputToken, currentAmount.toString());
      
      if (!multiQuote.routes || multiQuote.routes.length === 0) {
        if (currentAmount <= minAmount) break;
        currentAmount = (currentAmount * BigInt(70)) / BigInt(100);
        continue;
      };

      const route = multiQuote.routes.reduce((best, r) => {
        const currentAmountOut = BigInt(r.amount_out);
        const bestAmountOut = best ? BigInt(best.amount_out) : BigInt(0);
        return currentAmountOut > bestAmountOut ? r : best;
      }, null);

      if (!route) {
        if (currentAmount <= minAmount) break;
        currentAmount = (currentAmount * BigInt(70)) / BigInt(100);
        continue;
      };

      const swapData = await getSwapData(
        route.execution_path,
        currentAmount.toString(),
        route.amount_out,
        inputToken,
        outputToken,
        route.input_token_decimals,
        route.output_token_decimals
      );

      const binCount = swapData.swap_parameters?.length || 0;
      const isAcceptable = binCount >= MIN_SWAP_BINS && binCount <= MAX_SWAP_BINS;
      
      if (binCount >= TARGET_SWAP_BINS_MIN && binCount <= TARGET_SWAP_BINS_MAX) {
        bestSwapData = swapData;
        bestAmount = currentAmount;
        bestRoute = route;
        break;
      };

      if (isAcceptable && (!bestSwapData || Math.abs(binCount - TARGET_SWAP_BINS_MIN) < Math.abs((bestSwapData.swap_parameters?.length || 0) - TARGET_SWAP_BINS_MIN))) {
        bestSwapData = swapData;
        bestAmount = currentAmount;
        bestRoute = route;
      };

      if (binCount > TARGET_SWAP_BINS_MAX) {
        if (currentAmount <= minAmount) {
          if (!bestSwapData && binCount <= MAX_SWAP_BINS) {
            bestSwapData = swapData;
            bestAmount = currentAmount;
            bestRoute = route;
          };
          break;
        };
        currentAmount = (currentAmount * BigInt(60)) / BigInt(100);
        continue;
      };

      if (binCount < TARGET_SWAP_BINS_MIN) {
        if (binCount < MIN_SWAP_BINS) {
          const increasedAmount = (currentAmount * BigInt(120)) / BigInt(100);
          if ((MAX_SWAP_AMOUNT && increasedAmount > MAX_SWAP_AMOUNT) || (maxAmount && increasedAmount > maxAmount)) {
            break;
          };
          
          currentAmount = increasedAmount;
          continue;
        };

        const increasedAmount = (currentAmount * BigInt(120)) / BigInt(100);
        if ((MAX_SWAP_AMOUNT && increasedAmount > MAX_SWAP_AMOUNT) || (maxAmount && increasedAmount > maxAmount)) break;

        currentAmount = increasedAmount;
        continue;
      };
    } catch (error) {
      console.log(`Error finding optimal amount (attempt ${attempts}): ${error.message}`);
      if (currentAmount <= minAmount) break;
      currentAmount = (currentAmount * BigInt(70)) / BigInt(100);
    };
  };

  if (bestSwapData && bestAmount && bestRoute) {
    const finalBinCount = bestSwapData.swap_parameters?.length || 0;
    if (finalBinCount >= MIN_SWAP_BINS && finalBinCount <= MAX_SWAP_BINS) {
      return { swapData: bestSwapData, amount: bestAmount, route: bestRoute };
    };
  };

  return { swapData: null, amount: null, route: null };
};

const executeRandomSwap = async () => {
  const availableSwaps = [];

  for (const pool of POOLS) {
    if (!isPoolOnCooldown(pool.tokenX, pool.tokenY)) availableSwaps.push({ pool, xForY: true });
    if (!isPoolOnCooldown(pool.tokenY, pool.tokenX)) availableSwaps.push({ pool, xForY: false });
  };

  if (availableSwaps.length === 0) {
    console.log(`Skipping swap: All swap directions are on cooldown`);
    return { executed: false, reason: 'cooldown' };
  };

  const selectedSwap = sample(availableSwaps);
  const pool = selectedSwap.pool;
  const xForY = selectedSwap.xForY;
  const inputToken = xForY ? pool.tokenX : pool.tokenY;
  const outputToken = xForY ? pool.tokenY : pool.tokenX;

  const tokenBalance = await getTokenBalance(inputToken, STACKS_PUBLIC_KEY);
  if (tokenBalance === 0) {
    console.log(`Skipping swap: No balance for ${inputToken}`);
    return { executed: false, reason: 'no_balance' };
  };

  const stxBalance = await getSTXBalance(STACKS_PUBLIC_KEY);
  if (stxBalance - TRANSACTION_FEE_RATE <= 0) {
    console.log(`Skipping swap: Insufficient STX balance for transaction fees`);
    return { executed: false, reason: 'insufficient_stx' };
  };

  const randomPercent = MIN_BALANCE_PERCENT + Math.random() * (MAX_BALANCE_PERCENT - MIN_BALANCE_PERCENT);
  let initialAmount = Math.floor(tokenBalance * (randomPercent / 100));

  const tokenMaxAmountIn = ALLOWED_TOKENS[inputToken];
  let maxAmount = null;
  
  if (tokenMaxAmountIn && typeof tokenMaxAmountIn === 'number') maxAmount = BigInt(Math.floor(tokenMaxAmountIn));
  if (MAX_SWAP_AMOUNT) maxAmount = maxAmount ? (maxAmount < MAX_SWAP_AMOUNT ? maxAmount : MAX_SWAP_AMOUNT) : MAX_SWAP_AMOUNT;

  if (initialAmount === 0) {
    console.log(`Skipping swap: Amount too small for ${inputToken}`);
    return { executed: false, reason: 'amount_too_small' };
  };

  console.log(`Finding optimal swap amount for ${inputToken} to ${outputToken} (target: ${TARGET_SWAP_BINS_MIN}-${TARGET_SWAP_BINS_MAX} bins)`);

  const optimalSwap = await findOptimalSwapAmount(inputToken, outputToken, initialAmount, maxAmount);

  if (!optimalSwap.swapData || !optimalSwap.amount || !optimalSwap.route) {
    console.log(`Skipping swap: Could not find optimal swap amount`);
    return { executed: false, reason: 'no_optimal_amount' };
  };

  const swapData = optimalSwap.swapData;
  const bestRoute = optimalSwap.route;
  const amountIn = Number(optimalSwap.amount);
  const minReceived = swapData.swap_parameters_typed.reduce((sum, param) => sum + BigInt(param.value['min-received'].value), BigInt(0)).toString();

  console.log(`Optimal swap found: ${amountIn} ${inputToken} -> ${outputToken} (${swapData.swap_parameters.length} bins, target: ${TARGET_SWAP_BINS_MIN}-${TARGET_SWAP_BINS_MAX})`);

  if (!swapData.swap_parameters_typed || swapData.swap_parameters_typed.length === 0) {
    console.log(`Skipping swap: No swap parameters found`);
    return { executed: false, reason: 'no_swap_parameters' };
  };
  if (swapData.swap_parameters.length < MIN_SWAP_BINS) {
    console.log(`Skipping swap: Requires ${swapData.swap_parameters.length} bins, minimum is ${MIN_SWAP_BINS} bins`);
    return { executed: false, reason: 'bins_below_minimum' };
  };
  if (swapData.swap_parameters.length > MAX_SWAP_BINS) {
    console.log(`Skipping swap: Requires ${swapData.swap_parameters.length} bins, exceeds max of ${MAX_SWAP_BINS} bins`);
    return { executed: false, reason: 'bins_exceeds_maximum' };
  };

  const swapParamsCV = USE_SIMPLE_SWAP
    ? buildSwapSimpleMultiParams(swapData.swap_parameters_typed)
    : buildSwapMultiParams(swapData.swap_parameters_typed);
  const postConditions = buildPostConditions(swapData.post_conditions, bestRoute.min_amount_out);

  const { address: swapAddress, name: swapName } = CUSTOM_SWAP_ROUTER_CONTRACT
    ? parseContract(CUSTOM_SWAP_ROUTER_CONTRACT)
    : parseContract(swapData.swap_contract);

  let functionArgs = [];
  if (USE_SIMPLE_SWAP) {
    if (swapParamsCV.length === 0) {
      console.log(`Skipping swap: No grouped swap parameters found`);
      return { executed: false, reason: 'no_grouped_swap_parameters' };
    };
    
    if (swapParamsCV.length > 5) {
      console.log(`Skipping swap: Too many swap groups (${swapParamsCV.length}), maximum is 5`);
      return { executed: false, reason: 'too_many_swap_groups' };
    };
    
    functionArgs = [
      listCV(swapParamsCV.map(param => tupleCV(param)))
    ];
  } else {
    functionArgs = [
      listCV(swapParamsCV),
      uintCV(BIN_SLIPPAGE_TOLERANCE)
    ];
  };

  const txOptions = {
    contractAddress: swapAddress,
    contractName: swapName,
    functionName: swapData.function_name,
    functionArgs: functionArgs,
    senderKey: STACKS_PRIVATE_KEY,
    network: stacksNetwork,
    fee: TRANSACTION_FEE_RATE,
    postConditions: USE_POST_CONDITIONS ? postConditions : [],
    postConditionMode: USE_POST_CONDITIONS ? PostConditionMode.Deny : PostConditionMode.Allow,
    anchorMode: 3
  };

  if (DEBUG_MODE) {
    const outputTokenBalance = await getTokenBalance(outputToken, STACKS_PUBLIC_KEY);
    const wasAmountCapped = tokenMaxAmountIn && amountIn >= tokenMaxAmountIn;
    const randomPercentUsed = ((amountIn / tokenBalance) * 100);

    const debugInfo = {
      routeIndex: bestRoute.route_index,
      poolsUsed: bestRoute.execution_details?.pools_used ?? [bestRoute.execution_details?.pool_id],
      inputToken,
      outputToken,
      inputTokenBalance: tokenBalance,
      outputTokenBalance: outputTokenBalance,
      amountIn,
      amountInPercent: randomPercentUsed + '%',
      wasAmountCapped,
      tokenMaxAmountIn: tokenMaxAmountIn || 'unlimited',
      expectedAmountOut: bestRoute.amount_out,
      minReceived: minReceived,
      direction: xForY ? 'x-for-y' : 'y-for-x',
      hops: swapData.total_hops,
      bins: swapData.swap_parameters.length,
      swapContract: swapData.swap_contract,
      functionName: swapData.function_name,
      fee: TRANSACTION_FEE_RATE,
      binSlippageTolerance: USE_SIMPLE_SWAP ? 'N/A' : BIN_SLIPPAGE_TOLERANCE,
      postConditionsCount: USE_POST_CONDITIONS ? postConditions.length : 0,
      useMinReceived: USE_MIN_RECEIVED,
      usePostConditions: USE_POST_CONDITIONS,
      useSimpleSwap: USE_SIMPLE_SWAP
    };
    
    if (USE_SIMPLE_SWAP) {
      const groupsWithSteps = swapData.swap_parameters_typed.map(param => {
        const value = param.value;
        const apiMaxSteps = parseInt(value['max-steps'].value, 10);
        const initialMaxSteps = Math.max(1, Math.min(apiMaxSteps + ADDITIONAL_STEPS_PER_GROUP, 350));
        return {
          apiMaxSteps,
          initialMaxSteps,
          param
        };
      });
      
      const totalInitialSteps = groupsWithSteps.reduce((sum, group) => sum + group.initialMaxSteps, 0);
      const scaleFactor = totalInitialSteps > MAX_TOTAL_STEPS ? MAX_TOTAL_STEPS / totalInitialSteps : 1;
      const totalFinalSteps = Math.floor(totalInitialSteps * scaleFactor);
      
      debugInfo.swapSimpleMultiArgs = {
        swapGroups: swapData.swap_parameters_typed.length,
        totalInitialSteps: totalInitialSteps,
        totalFinalSteps: totalFinalSteps,
        scaleFactor: scaleFactor < 1 ? scaleFactor.toFixed(4) : 1,
        groups: groupsWithSteps.map((group, idx) => {
          const value = group.param.value;
          const scaledMaxSteps = Math.max(1, Math.floor(group.initialMaxSteps * scaleFactor));
          return {
            groupIndex: idx,
            pool: value['pool-trait'].value,
            xToken: value['x-token-trait'].value,
            yToken: value['y-token-trait'].value,
            amount: value['amount'].value,
            minReceived: value['min-received'].value,
            xForY: value['x-for-y'].type === 'true',
            apiMaxSteps: group.apiMaxSteps,
            initialMaxSteps: group.initialMaxSteps,
            finalMaxSteps: scaledMaxSteps
          };
        })
      };
    };
    
    console.log('Swap prepared (debug mode):', debugInfo);
    if (USE_SIMPLE_SWAP && debugInfo.swapSimpleMultiArgs) {
      console.log('\nSwap Groups Details:');
      console.log(`  Total Initial Steps: ${debugInfo.swapSimpleMultiArgs.totalInitialSteps}`);
      console.log(`  Total Final Steps: ${debugInfo.swapSimpleMultiArgs.totalFinalSteps}`);
      if (debugInfo.swapSimpleMultiArgs.scaleFactor < 1) {
        console.log(`  Scale Factor: ${debugInfo.swapSimpleMultiArgs.scaleFactor} (scaled down from ${debugInfo.swapSimpleMultiArgs.totalInitialSteps})`);
      }
      debugInfo.swapSimpleMultiArgs.groups.forEach((group, idx) => {
        console.log(`  Group ${idx + 1}:`);
        console.log(`    Pool: ${group.pool}`);
        console.log(`    X Token: ${group.xToken}`);
        console.log(`    Y Token: ${group.yToken}`);
        console.log(`    Direction: ${group.xForY ? 'x-for-y' : 'y-for-x'}`);
        console.log(`    Amount: ${group.amount}`);
        console.log(`    Min Received: ${group.minReceived}`);
        console.log(`    API Max Steps: ${group.apiMaxSteps}`);
        console.log(`    Initial Max Steps: ${group.initialMaxSteps} (API + ${ADDITIONAL_STEPS_PER_GROUP})`);
        console.log(`    Final Max Steps: ${group.finalMaxSteps}`);
      });
    };
    return { executed: false, reason: 'debug_mode' };
  };

  const nonceResult = await getNextNonce();

  if (nonceResult.pendingCount >= MAX_PENDING_TRANSACTIONS) {
    console.log(`Skipping swap: Too many pending transactions (${nonceResult.pendingCount}, max: ${MAX_PENDING_TRANSACTIONS})`);
    return { executed: false, reason: 'too_many_pending' };
  };
  
  if (nonceResult.pendingCount > MAX_PENDING_TRANSACTIONS * 0.8) {
    console.log(`Warning: High number of pending transactions (${nonceResult.pendingCount}), consider reducing transaction frequency`);
  };
  
  const currentNonce = nonceResult.nonce;

  for (let i = 0; i < TRANSACTIONS_TO_BROADCAST; i++) {
    const transaction = await makeContractCall({
      ...txOptions,
      nonce: currentNonce + BigInt(i)
    });
    
    const broadcastResponse = await broadcastTransaction(transaction, stacksNetwork);

    if (broadcastResponse.error) {
      console.error(`Broadcast failed for transaction ${i + 1}/${TRANSACTIONS_TO_BROADCAST}: ${broadcastResponse.reason} (${broadcastResponse.reason_data})`);
      return { executed: false, reason: 'broadcast_failed', error: broadcastResponse.reason };
    };

    console.log(`Swap executed (${i + 1}/${TRANSACTIONS_TO_BROADCAST}):`, {
      txId: broadcastResponse.txid,
      nonce: (currentNonce + BigInt(i)).toString(),
      fee: TRANSACTION_FEE_RATE,
      routeIndex: bestRoute.route_index,
      poolsUsed: bestRoute.execution_details?.pools_used ?? [bestRoute.execution_details?.pool_id],
      inputToken,
      outputToken,
      amountIn,
      expectedAmountOut: bestRoute.amount_out,
      direction: xForY ? 'x-for-y' : 'y-for-x',
      hops: swapData.total_hops,
      bins: swapData.swap_parameters.length,
      useMinReceived: USE_MIN_RECEIVED,
      usePostConditions: USE_POST_CONDITIONS,
      useSimpleSwap: USE_SIMPLE_SWAP
    });
  };

  setPoolCooldown(inputToken, outputToken);
  return { executed: true };
};

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const mainLoop = async () => {
  console.log('');
  console.log('Starting HODLMM swap helper...');
  
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
  if (CUSTOM_SWAP_ROUTER_CONTRACT) console.log(`Custom swap router contract: ${CUSTOM_SWAP_ROUTER_CONTRACT}`);
  console.log(`Transactions to broadcast: ${TRANSACTIONS_TO_BROADCAST}`);
  console.log(`Transaction fee rate: ${TRANSACTION_FEE_RATE} uSTX`);
  console.log(`Transaction interval: ${TRANSACTION_INTERVAL_MS}ms`);
  console.log(`Pool cooldown: ${POOL_COOLDOWN_MS}ms`);
  console.log(`Balance percent range: ${MIN_BALANCE_PERCENT}% - ${MAX_BALANCE_PERCENT}%`);
  console.log(`Bins per transaction range: ${MIN_SWAP_BINS} - ${MAX_SWAP_BINS} bins`);
  console.log(`Slippage tolerance: ${SLIPPAGE_TOLERANCE}%`);
  console.log(`Bin slippage tolerance: ${BIN_SLIPPAGE_TOLERANCE} bins`);
  console.log(`Min received: ${USE_MIN_RECEIVED ? 'Enabled' : 'Disabled'}`);
  console.log(`Post conditions: ${USE_POST_CONDITIONS ? 'Enabled' : 'Disabled'}`);
  console.log(`Simple swap: ${USE_SIMPLE_SWAP ? 'Enabled' : 'Disabled'}`);
  if (USE_SIMPLE_SWAP) {
    console.log(`Additional steps per group: ${ADDITIONAL_STEPS_PER_GROUP}`);
    console.log(`Max total steps across all groups: ${MAX_TOTAL_STEPS}`);
  };
  console.log(`Allow all tokens: ${ALLOW_ALL_TOKENS ? 'Enabled' : 'Disabled'}`);
  console.log(`Debug mode: ${DEBUG_MODE ? 'Enabled' : 'Disabled'}`);

  while (true) {
    try {
      console.log('');
      const result = await executeRandomSwap();

      if (result && result.reason === 'insufficient_stx') {
        console.log('Insufficient STX balance detected. Exiting...');
        break;
      };

      if (result && result.executed) {
        await delay(TRANSACTION_INTERVAL_MS);
      } else {
        await delay(100);
      };
    } catch (error) {
      console.error('Error executing swap transaction:', error.message);
      if (error.stack) {
        console.error(error.stack);
      };
      await delay(1000);
    };
  };
};

mainLoop();