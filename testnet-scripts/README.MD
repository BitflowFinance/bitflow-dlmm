# DLMM Testnet Scripts

Automated transaction testing scripts for Bitflow HODLMM

## Overview

This repository contains two main scripts for testing HODLMM operations on-chain:

- **`swap_helper.js`**: Executes random swap transactions
- **`liquidity_helper.js`**: Executes random add and withdraw liquidity transactions

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Stacks wallet with testnet or mainnet tokens
- Access to BFF API endpoint

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bitflow-dlmm/testnet-scripts
```

2. Install dependencies:
```bash
npm install
```

3. Copy the example environment file:
```bash
cp example.env .env
```

4. Edit `.env` and fill in your configuration:
   - `BFF_API_URL` - Your BFF API endpoint URL
   - `STACKS_PUBLIC_KEY` - Your Stacks public key
   - `STACKS_PRIVATE_KEY` - Your Stacks private key
   - Other configuration values as needed

## Configuration

All configuration is done through environment variables. See `example.env` for all available options.

### Key Configuration Variables

- `TRANSACTIONS_TO_BROADCAST` - Number of duplicate transactions to broadcast (default: 1)
- `TRANSACTION_FEE_RATE` - Transaction fee in uSTX (default: 30000)
- `MIN_BALANCE_PERCENT` / `MAX_BALANCE_PERCENT` - Percentage of balance to use per transaction
- `MIN_SWAP_BINS` / `MAX_SWAP_BINS` - Minimum and maximum number of bins to use per swap
- `MIN_LIQUIDITY_BINS` / `MAX_LIQUIDITY_BINS` - Minimum and maximum number of bins to use for liquidity operations
- `SLIPPAGE_TOLERANCE` - Slippage tolerance percentage
- `USE_MIN_RECEIVED` - Enable/disable minimum received checks
- `USE_POST_CONDITIONS` - Enable/disable post conditions
- `ALLOW_ALL_TOKENS` - Allow all tokens or only those in ALLOWED_TOKENS (ALLOWED_TOKENS is configurable within the script)
- `DEBUG_MODE` - Enable debug logging. No transactions are broadcast when debug mode is enabled

## Usage

### Swap Helper

Run the swap helper script:
```bash
node src/swap_helper.js
```

The script will:
1. Fetch available pools from the BFF API
2. Select a random pool and build the swap transaction
3. Execute the swap transaction
4. Wait for the configured interval before the next transaction

### Liquidity Helper

Run the liquidity helper script:
```bash
node src/liquidity_helper.js
```

The script will:
1. Fetch available pools from the BFF API
2. Randomly choose to add or withdraw liquidity
3. Select a random pool and build the liquidity transaction
4. If adding: Select bins based on the active bin and token balances
5. If withdrawing: Select from the user's existing positions
6. Execute the liquidity transaction
7. Wait for the configured interval before the next transaction

## Token Limits

Both scripts support per-transaction token limits defined in the `ALLOWED_TOKENS` object. If `ALLOW_ALL_TOKENS` is set to `false`, only tokens in this object will be used. Amounts are automatically scaled down if they exceed the limits.

## Network Configuration

The scripts support both testnet and mainnet. Set `STACKS_NETWORK_VERSION` to either `testnet` or `mainnet`. You can also configure custom node URLs and API keys.