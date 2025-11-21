// swap_helper.js

require('dotenv').config();

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
const TRANSACTIONS_TO_BROADCAST = parseInt(process.env.TRANSACTIONS_TO_BROADCAST, 10);
const TRANSACTION_FEE_RATE = parseInt(process.env.TRANSACTION_FEE_RATE, 10);
const TRANSACTION_INTERVAL_MS = parseInt(process.env.TRANSACTION_INTERVAL_MS, 10);
const POOL_COOLDOWN_MS = parseInt(process.env.POOL_COOLDOWN_MS, 10);
const MIN_BALANCE_PERCENT = parseFloat(process.env.MIN_BALANCE_PERCENT, 10);
const MAX_BALANCE_PERCENT = parseFloat(process.env.MAX_BALANCE_PERCENT, 10);
const MIN_SWAP_BINS = parseInt(process.env.MIN_SWAP_BINS, 10);
const MAX_SWAP_BINS = parseInt(process.env.MAX_SWAP_BINS, 10);
const SLIPPAGE_TOLERANCE = parseInt(process.env.SLIPPAGE_TOLERANCE, 10);
const BIN_SLIPPAGE_TOLERANCE = parseInt(process.env.BIN_SLIPPAGE_TOLERANCE, 10);
const USE_MIN_RECEIVED = process.env.USE_MIN_RECEIVED === 'true';
const USE_POST_CONDITIONS = process.env.USE_POST_CONDITIONS === 'true';
const USE_SIMPLE_SWAP = process.env.USE_SIMPLE_SWAP === 'true';
const ALLOW_ALL_TOKENS = process.env.ALLOW_ALL_TOKENS === 'true';
const DEBUG_MODE = process.env.DEBUG_MODE === 'true';

// Allowed tokens and their per-transaction maximums (do not scale)
const ALLOWED_TOKENS = {
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tstx-v-0-2': 35000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tdog-v-0-2': 350000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tusdc-v-0-2': 35000,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tusdh-v-0-1': 3500,
  'SP3ESW1QCNQPVXJDGQWT7E45RDCH38QBK9HEJSX4X.token-tbtc-v-0-2': 0.035
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

const getPoolKey = (tokenX, tokenY) => `${tokenX}::${tokenY}`;

const isPoolOnCooldown = (tokenX, tokenY) => {
  const poolKey = getPoolKey(tokenX, tokenY);
  const lastSwapTime = poolCooldowns.get(poolKey);
  
  if (!lastSwapTime) return false;
  
  const elapsed = Date.now() - lastSwapTime;
  return elapsed < POOL_COOLDOWN_MS;
};

const setPoolCooldown = (tokenX, tokenY) => {
  const poolKey = getPoolKey(tokenX, tokenY);
  poolCooldowns.set(poolKey, Date.now());
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
      slippage_tolerance: SLIPPAGE_TOLERANCE
    })
  });

  if (!response.ok) throw new Error(`Swap data returned ${response.status} with message: ${await response.text()}`);

  const data = await response.json();

  if (!data.success) throw new Error(`Swap data error: ${data.error}`);

  return data;
};

const convertTypedSwapParams = (swapParamsTyped) => {
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

const buildPostConditions = (postConditions, swapParamsTyped) => {
  const conditions = [];

  for (let i = 0; i < postConditions.length; i++) {
    const pc = postConditions[i];
    const { address: tokenAddress, name: tokenName } = parseContract(pc.token_contract);
    const assetInfo = createAssetInfo(tokenAddress, tokenName, pc.token_asset_name);

    let amount = pc.amount;
    const isLastPostCondition = i === postConditions.length - 1;

    if (isLastPostCondition && swapParamsTyped?.length) {
      if (USE_MIN_RECEIVED) {
        const totalMinReceived = swapParamsTyped.reduce(
          (sum, swapParam) => sum + BigInt(swapParam.value['min-received'].value),
          BigInt(0)
        );
        amount = totalMinReceived.toString();
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

const executeRandomSwap = async () => {
  const availableSwaps = [];

  for (const pool of POOLS) {
    if (!isPoolOnCooldown(pool.tokenX, pool.tokenY)) availableSwaps.push({ pool, xForY: true });
    if (!isPoolOnCooldown(pool.tokenY, pool.tokenX)) availableSwaps.push({ pool, xForY: false });
  };

  if (availableSwaps.length === 0) return console.log(`Skipping swap: All swap directions are on cooldown`);

  const selectedSwap = sample(availableSwaps);
  const pool = selectedSwap.pool;
  const xForY = selectedSwap.xForY;
  const inputToken = xForY ? pool.tokenX : pool.tokenY;
  const outputToken = xForY ? pool.tokenY : pool.tokenX;

  const tokenBalance = await getTokenBalance(inputToken, STACKS_PUBLIC_KEY);
  if (tokenBalance === 0) return console.log(`Skipping swap: No balance for ${inputToken}`);

  const stxBalance = await getSTXBalance(STACKS_PUBLIC_KEY);
  if (stxBalance - TRANSACTION_FEE_RATE <= 0) return console.log(`Skipping swap: Insufficient STX balance for transaction fees`);

  const randomPercent = MIN_BALANCE_PERCENT + Math.random() * (MAX_BALANCE_PERCENT - MIN_BALANCE_PERCENT);
  let amountIn = Math.floor(tokenBalance * (randomPercent / 100));

  const tokenMaxAmountIn = ALLOWED_TOKENS[inputToken];
  if (tokenMaxAmountIn && typeof tokenMaxAmountIn === 'number' && amountIn > tokenMaxAmountIn) amountIn = tokenMaxAmountIn;

  if (amountIn === 0) return console.log(`Skipping swap: Amount too small for ${inputToken}`);

  console.log(`Requesting multi-quote for ${amountIn} ${inputToken} to ${outputToken}`);

  const multiQuote = await getMultiQuote(inputToken, outputToken, amountIn);

  console.log(`Multi-quote received: ${multiQuote.routes.length} route(s) found`);

  const bestRoute = multiQuote.routes.reduce((best, route) => {
    const currentAmountOut = BigInt(route.amount_out);
    const bestAmountOut = best ? BigInt(best.amount_out) : BigInt(0);
    return currentAmountOut > bestAmountOut ? route : best;
  }, null);
  if (!bestRoute) throw new Error('No valid route found');

  console.log(`Best route selected: Route #${bestRoute.route_index} with expected output of ${bestRoute.amount_out}`);

  console.log(`Requesting swap data for route #${bestRoute.route_index}`);

  const swapData = await getSwapData(
    bestRoute.execution_path,
    amountIn.toString(),
    bestRoute.amount_out,
    inputToken,
    outputToken,
    bestRoute.input_token_decimals,
    bestRoute.output_token_decimals
  );
  const minReceived = swapData.swap_parameters_typed.reduce((sum, param) => sum + BigInt(param.value['min-received'].value), BigInt(0)).toString();

  console.log(`Swap data received: ${swapData.total_hops} hop(s) and ${swapData.swap_parameters.length} bins(s)`);

  if (!swapData.swap_parameters_typed || swapData.swap_parameters_typed.length === 0) return console.log(`Skipping swap: No swap parameters found`);
  if (swapData.swap_parameters.length < MIN_SWAP_BINS) return console.log(`Skipping swap: Requires ${swapData.swap_parameters.length} bins, minimum is ${MIN_SWAP_BINS} bins`);
  if (swapData.swap_parameters.length > MAX_SWAP_BINS) return console.log(`Skipping swap: Requires ${swapData.swap_parameters.length} bins, exceeds max of ${MAX_SWAP_BINS} bins`);

  const swapParamsCV = convertTypedSwapParams(swapData.swap_parameters_typed);
  const postConditions = buildPostConditions(swapData.post_conditions, swapData.swap_parameters_typed);

  const { address: swapAddress, name: swapName } = parseContract(swapData.swap_contract);

  let functionName = swapData.function_name;
  if (USE_SIMPLE_SWAP) functionName = xForY ? 'swap-x-for-y-simple-multi' : 'swap-y-for-x-simple-multi';

  let functionArgs = [];
  if (USE_SIMPLE_SWAP) {
    const firstSwap = swapData.swap_parameters_typed[0].value;

    functionArgs = [
      principalCV(firstSwap['pool-trait'].value),
      principalCV(firstSwap['x-token-trait'].value),
      principalCV(firstSwap['y-token-trait'].value),
      uintCV(firstSwap['amount'].value),
      uintCV(USE_MIN_RECEIVED ? minReceived : '0')
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
    functionName: functionName,
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
      functionName: functionName,
      fee: TRANSACTION_FEE_RATE,
      binSlippageTolerance: USE_SIMPLE_SWAP ? 'N/A' : BIN_SLIPPAGE_TOLERANCE,
      postConditionsCount: USE_POST_CONDITIONS ? postConditions.length : 0,
      useMinReceived: USE_MIN_RECEIVED,
      usePostConditions: USE_POST_CONDITIONS,
      useSimpleSwap: USE_SIMPLE_SWAP
    };
    
    if (USE_SIMPLE_SWAP) {
      debugInfo.simpleSwapArgs = {
        pool: swapData.swap_parameters_typed[0].value['pool-trait'].value,
        xToken: swapData.swap_parameters_typed[0].value['x-token-trait'].value,
        yToken: swapData.swap_parameters_typed[0].value['y-token-trait'].value,
        amount: swapData.swap_parameters_typed[0].value['amount'].value,
        minReceived: USE_MIN_RECEIVED ? minReceived : '0'
      };
    };
    
    return console.log('Swap prepared (debug mode):', debugInfo);
  };

  let currentNonce = await getNonce(STACKS_PUBLIC_KEY, stacksNetwork);

  for (let i = 0; i < TRANSACTIONS_TO_BROADCAST; i++) {
    const transaction = await makeContractCall({
      ...txOptions,
      nonce: currentNonce + BigInt(i)
    });
    
    const broadcastResponse = await broadcastTransaction(transaction, stacksNetwork);

    if (broadcastResponse.error) throw new Error(`Broadcast failed for transaction ${i + 1}/${TRANSACTIONS_TO_BROADCAST}: ${broadcastResponse.reason} (${broadcastResponse.reason_data})`);

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
  console.log(`Allow all tokens: ${ALLOW_ALL_TOKENS ? 'Enabled' : 'Disabled'}`);
  console.log(`Debug mode: ${DEBUG_MODE ? 'Enabled' : 'Disabled'}`);

  while (true) {
    try {
      console.log('');
      await executeRandomSwap();
    } catch (error) {
      console.error('Error executing swap transaction:', error.message);
      if (error.stack) {
        console.error(error.stack);
      };
    };
    await delay(TRANSACTION_INTERVAL_MS);
  };
};

mainLoop();