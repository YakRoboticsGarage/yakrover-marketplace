# Plan: Production Gasless USDC Payment

**Date:** 2026-04-05
**Goal:** Buyer pays USDC on Base or Ethereum mainnet without needing ETH for gas. Platform sponsors gas via ERC-2612 permit relay. Works with Rabby, MetaMask, Coinbase Wallet.

---

## Architecture

```
Buyer's wallet (Rabby / MetaMask / Coinbase Wallet)
  |
  |-- Signs EIP-712 permit off-chain (gasless for buyer)
  |
  v
Cloudflare Worker (/api/relay-usdc)
  |
  |-- Calls USDC.permit(buyer, worker, amount, deadline, v, r, s)
  |-- Calls USDC.transferFrom(buyer, robotWallet, 88%)
  |-- Calls USDC.transferFrom(buyer, platformWallet, 12%)
  |-- Pays gas from platform's funded EOA
  |
  v
Both transfers confirmed on-chain → tx hashes returned to browser
```

**Why this works:**
- USDC on Base and Ethereum is FiatTokenV2_2 with ERC-2612 permit support
- Buyer signs a typed data message (EIP-712) — no gas needed
- Worker submits the permit + transfers, paying gas from platform wallet
- All wallets that support EIP-712 signing work (MetaMask, Rabby, Coinbase Wallet)

## Cost

| Chain | Gas per relay | 100 tx/month | Platform wallet funding |
|-------|--------------|-------------|----------------------|
| Base | ~$0.005 | ~$0.50 | 0.01 ETH lasts thousands of tx |
| Ethereum mainnet | ~$0.04-$0.15 | ~$4-$15 | 0.01 ETH lasts ~200 tx |

## USDC Contract Addresses

| Chain | USDC Address |
|-------|-------------|
| Base mainnet | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Ethereum mainnet | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Base Sepolia | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Eth Sepolia | `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` |

## Implementation

### Worker endpoint: POST /api/relay-usdc

Receives the signed permit + transfer details, submits on-chain.

### Demo page changes

1. Add Rabby to wallet detection (already works via window.ethereum)
2. Add EIP-6963 multi-wallet discovery (handles Rabby + MetaMask conflict)
3. Replace direct USDC.transfer() with permit + relay flow
4. Support Base mainnet + Ethereum mainnet chain selection

### Worker secrets needed

```
RELAY_PRIVATE_KEY    — Platform's relay wallet private key (funded with ETH on Base + mainnet)
```

## Security

- Permit is scoped: specific amount, specific spender (worker address), deadline
- Worker can only transferFrom what the buyer permitted — no excess access
- Relay wallet only needs ETH for gas, never holds USDC
- Private key stored as Cloudflare Worker secret (encrypted at rest)
- Permit expires (deadline parameter) — replay protection
- Nonce tracked by USDC contract — each permit can only be used once
