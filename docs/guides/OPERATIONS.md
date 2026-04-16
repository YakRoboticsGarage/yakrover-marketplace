# Operations Runbook

**Last updated:** 2026-04-12

How to manage secrets, deploy services, fund wallets, and respond to alerts.

---

## Recurring Automated Tasks

| Task | Schedule | Platform | What it does |
|------|----------|----------|-------------|
| **Daily research** | 9:00 AM local | claude.ai/code/scheduled | Automated research on topics from `RESEARCH_ROADMAP.yaml` |
| **Daily docs-sync + code review** | 7:00 PM local | claude.ai/code/scheduled | Syncs docs, runs code review against recent changes |
| **Relay wallet balance monitor** | 09:00 UTC daily | Cloudflare Cron Trigger (`yakrobot-api`) | Checks relay ETH balance on Base mainnet. Alerts via Telegram if < 0.005 ETH (warning) or < 0.001 ETH (critical). |

---

## Infrastructure Map

| Service | URL | Deploy command |
|---------|-----|----------------|
| **yakrobot-api** (Worker) | yakrobot-api.rafaeldf2.workers.dev | `cd worker && npx wrangler deploy` (requires Node 20+) |
| **yakrover-marketplace** (MCP) | yakrover-marketplace.fly.dev | `fly deploy -a yakrover-marketplace` |
| **9 category simulators** | yakrover-{category}.fly.dev | `infra/fleet-sim/deploy-category.sh {category}` |
| **yakrobot.bid** (landing) | yakrobot.bid | `./scripts/publish.sh demo/landing --slug ...` (here.now) |
| **yakrobot.bid/demo** (marketplace) | yakrobot.bid/demo | `./scripts/publish.sh demo/marketplace --slug ...` (here.now) |

---

## Secrets Inventory

All secrets are stored in 1Password. This table shows where each secret is deployed.

| Secret | 1Password | Worker | Fly.io MCP | Local .env |
|--------|-----------|--------|------------|------------|
| `ANTHROPIC_API_KEY` | Yes | Yes | No | No |
| `STRIPE_SECRET_KEY` | Yes | Yes | No | No |
| `STRIPE_WEBHOOK_SECRET` | Yes | Yes | No | No |
| `PINATA_JWT` | Yes | Yes | No | Yes |
| `RELAY_PRIVATE_KEY` | Yes | Yes | No | No |
| `MCP_API_TOKEN` | Yes | Yes | Yes | Yes |
| `TELEGRAM_BOT_TOKEN` | Yes | Yes | No | No |
| `SIGNER_PVT_KEY` | Yes | No | Yes | Yes |
| Fleet operator keys (x18) | Yes | No | No | `.fleet_wallets.json` |

### Setting Worker secrets

```bash
source "$HOME/.nvm/nvm.sh" && nvm use 22
cd worker
npx wrangler secret put SECRET_NAME
# paste value when prompted
npx wrangler deploy
```

### Setting Fly.io secrets

```bash
fly secrets set SECRET_NAME=value -a yakrover-marketplace
# App restarts automatically
```

---

## Secret Rotation Procedures

### ANTHROPIC_API_KEY
1. Generate new key at console.anthropic.com
2. `npx wrangler secret put ANTHROPIC_API_KEY`
3. Deploy Worker
4. Revoke old key in Anthropic console
5. Update 1Password

### STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET
1. Roll key in Stripe Dashboard > Developers > API keys
2. `npx wrangler secret put STRIPE_SECRET_KEY`
3. For webhook: Stripe Dashboard > Webhooks > endpoint > Roll secret
4. `npx wrangler secret put STRIPE_WEBHOOK_SECRET`
5. Deploy Worker
6. Update 1Password

### PINATA_JWT
1. Revoke old token in Pinata dashboard (app.pinata.cloud > API Keys)
2. Create new JWT token
3. `npx wrangler secret put PINATA_JWT`
4. Update `.env` (local) and `fly secrets set PINATA_JWT=... -a yakrover-marketplace`
5. Deploy both
6. Update 1Password

### MCP_API_TOKEN
1. Generate new token: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Update `.env` (local)
3. `fly secrets set MCP_API_TOKEN=... -a yakrover-marketplace`
4. `npx wrangler secret put MCP_API_TOKEN` (Worker must match MCP server)
5. Deploy both
6. Update 1Password

### RELAY_PRIVATE_KEY
1. Generate new wallet: `python3 -c "from eth_account import Account; a=Account.create(); print(f'address={a.address}\nkey={a.key.hex()}')" `
2. Fund new address on Base mainnet with ~0.01 ETH
3. `npx wrangler secret put RELAY_PRIVATE_KEY`
4. Deploy Worker
5. Drain old wallet
6. Update 1Password and `RELAY_WALLET` in `auction/contracts.py`

### SIGNER_PVT_KEY (platform wallet)
1. This is the most impactful rotation — all registered robots are owned by this address
2. Generate new wallet, fund on Base
3. Transfer robot ownership via ERC-721 `transferFrom` (batch script needed)
4. Update `.env` and `fly secrets set`
5. Redeploy MCP server
6. Update 1Password

### TELEGRAM_BOT_TOKEN
1. Message @BotFather on Telegram > /revoke
2. Get new token
3. `npx wrangler secret put TELEGRAM_BOT_TOKEN`
4. Update `~/.claude/channels/telegram/.env`
5. Deploy Worker
6. Update 1Password

---

## Wallet Funding

### Relay wallet (0x4b59...0d9)

Pays gas for gasless USDC transfers on Base. Current cost: ~$0.005/tx.

**When to fund:** Telegram alert fires at < 0.005 ETH (~100 txs remaining).

**How to fund:**
1. Send ETH on Base mainnet to `0x4b5974229f96ac5987d6e31065d73d6fd8e130d9`
2. Amount: 0.01-0.02 ETH (lasts ~200-400 transactions)
3. Source: any wallet, Coinbase, or bridge from Ethereum mainnet

### Platform wallet (0xe333...8e5)

Receives 12% commission from USDC payments. Does not need gas funding (only receives).

---

## Alert Response

### "Relay wallet balance low" (Telegram)

**Warning (< 0.005 ETH):** Fund within 24 hours. ~100 txs remaining.

**Critical (< 0.001 ETH):** Fund immediately. USDC payments will fail within ~20 txs.

### MCP server unreachable

1. Check: `curl https://yakrover-marketplace.fly.dev/health`
2. If down: `fly logs -a yakrover-marketplace` to diagnose
3. Restart: `fly apps restart yakrover-marketplace`
4. If persistent: `fly deploy -a yakrover-marketplace`

### Worker errors

1. Check: `npx wrangler tail` (live logs)
2. Or: Cloudflare Dashboard > Workers > yakrobot-api > Logs

---

## Deployment Checklist

### Worker (yakrobot-api)
```bash
source "$HOME/.nvm/nvm.sh" && nvm use 22
cd worker
npx wrangler deploy
# Verify: curl https://yakrobot-api.rafaeldf2.workers.dev/api/health
```

### MCP Server (yakrover-marketplace)
```bash
fly deploy -a yakrover-marketplace
# Verify: curl https://yakrover-marketplace.fly.dev/health
```

### Demo site (yakrobot.bid)
```bash
# Landing page
./scripts/publish.sh demo/landing --slug <slug>
# Marketplace demo
./scripts/publish.sh demo/marketplace --slug <slug>
```
