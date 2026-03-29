# MCP Deployment Plan -- Robot Task Auction Marketplace

**Date:** 2026-03-29
**Status:** Ready to execute
**Goal:** Get `serve_with_auction.py` running on a public URL so Claude Code users and the yakrobot.bid frontend can connect to a hosted auction engine.

---

## 1. Hosting Options Comparison

| Factor | Railway | Fly.io | Render | DigitalOcean App Platform | ngrok static domain |
|--------|---------|--------|--------|---------------------------|---------------------|
| **Monthly cost (MVP)** | ~$5 (hobby plan, usage-based) | ~$3-5 (single shared-cpu-1x) | $7 (starter instance) | $5 (basic) | $0 (free static domain) / $10 (pro) |
| **Persistent URL** | `*.up.railway.app` | `*.fly.dev` | `*.onrender.com` | `*.ondigitalocean.app` | `*.ngrok-free.app` |
| **SSL** | Auto (Let's Encrypt) | Auto | Auto | Auto | Auto |
| **Deploy from Git** | Yes (auto-detect) | Yes (via Dockerfile) | Yes (auto-detect) | Yes | No (runs locally) |
| **Custom domain** | Yes (free) | Yes (free) | Yes (paid plan) | Yes (free) | Yes ($10/mo) |
| **SQLite persistence** | Volume mount ($0.25/GB) | Volume mount ($0.15/GB) | Disk on paid plan | No persistent disk | Local filesystem |
| **Deploy complexity** | `railway up` | `fly deploy` (needs Dockerfile) | Git push | Git push | `ngrok http 8000` |
| **Cold start** | ~2s (hobby) | ~1s (always-on) | ~30s (free tier spin-down) | ~5s | None (local) |
| **Postgres add-on** | One-click ($5/mo) | Built-in ($3.57/mo) | One-click ($7/mo) | Separate ($15/mo) | N/A |

### Recommendation: Railway

**Why:** Fastest path from repo to public URL. Auto-detects Python/FastAPI, usage-based pricing keeps MVP costs at $5/mo, one-click Postgres when we outgrow SQLite, and volume mounts for SQLite in the meantime. The `railway up` workflow matches our "deploy this week" timeline. Fly.io is a close second (cheaper at scale, better for multi-region), but Railway's zero-config Python detection wins for a team of one.

**Fallback:** If you want zero cost during development, use ngrok with a free static domain (`ngrok http 8000 --url yakrobot.ngrok-free.app`). This keeps the server on your machine but gives a stable public URL.

---

## 2. Deployment Architecture

```
Internet
  |
  +---> Railway (public URL: marketplace.up.railway.app)
          |
          +-- FastAPI app (serve_with_auction.py)
          |     |-- /fleet/mcp ......... MCP endpoint (15 auction tools)
          |     |-- /fakerover/mcp ..... FakeRover simulator MCP
          |     |-- /api/v1/ ........... HTTP REST for yakrobot.bid frontend
          |     +-- / .................. Health check / status JSON
          |
          +-- SQLite volume (/data/auction.db)
          +-- Environment variables (Railway dashboard)
```

### Environment Variables (set in Railway dashboard)

```
AUCTION_DB_PATH=/data/auction.db
STRIPE_SECRET_KEY=sk_test_...          # Stripe test mode
STRIPE_OPERATOR_ACCOUNT=acct_...       # Connect Express test account
SIGNING_MODE=ed25519
MCP_BEARER_TOKEN=<generate-random-64>  # Auth for MCP endpoint
FAKEROVER_URL=internal                 # Fakerover runs in-process
PORT=8000                              # Railway sets this automatically
```

### Database Path

- **MVP (now):** SQLite on a Railway volume mount. Good for single-instance, low traffic.
- **When to switch:** When you need >1 instance (horizontal scaling) or >10 concurrent auction writers. Add Railway Postgres, change `AUCTION_DB_PATH` to a `postgresql://` connection string, swap `SyncTaskStore` for an async Postgres store.

---

## 3. Step-by-Step Deployment (Railway)

### 3a. Create Dockerfile

Create `Dockerfile` in the repo root:

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

# Install uv and sync dependencies
RUN pip install uv && uv sync --all-extras --no-dev

# Create data directory for SQLite
RUN mkdir -p /data

EXPOSE 8000

CMD ["uv", "run", "python", "serve_with_auction.py", "--port", "8000"]
```

### 3b. Deploy

```bash
# Install Railway CLI
brew install railway

# Login and create project
railway login
railway init          # name it "robot-marketplace"

# Add a volume for SQLite persistence
railway volume add --mount /data

# Set environment variables
railway variables set AUCTION_DB_PATH=/data/auction.db
railway variables set SIGNING_MODE=ed25519
railway variables set MCP_BEARER_TOKEN=$(openssl rand -hex 32)
railway variables set STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE

# Deploy
railway up

# Get your public URL
railway domain     # prints: marketplace.up.railway.app
```

### 3c. Verify Deployment

```bash
# Health check
curl https://marketplace.up.railway.app/

# Expected: JSON with service info, robot list, auction status

# Test MCP endpoint responds
curl -X POST https://marketplace.up.railway.app/fleet/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Expected: JSON-RPC response listing 15 auction tools
```

---

## 4. MCP Connection Guide

### 4a. Connect Claude Code to the Hosted Server

```bash
claude mcp add-json auction-marketplace '{
  "type": "http",
  "url": "https://marketplace.up.railway.app/fleet/mcp",
  "headers": {
    "Authorization": "Bearer YOUR_MCP_BEARER_TOKEN"
  }
}'
```

Or without auth (if you skip bearer token for MVP):

```bash
claude mcp add --transport http auction-marketplace \
  https://marketplace.up.railway.app/fleet/mcp
```

### 4b. Test the Connection

Inside Claude Code, say:
- "What robots are available?" -- should list fakerover fleet
- "Fund my wallet with $5" -- should credit the buyer wallet
- "Post a temperature survey task for Bay 3" -- should create an auction

### 4c. Connect yakrobot.bid Frontend

Update the demo site's API base URL. In `demo/index.html`, change the fetch target:

```javascript
const API_BASE = "https://marketplace.up.railway.app/api/v1";
```

The `/api/v1/` endpoints (from `auction/api.py`) serve the same data that the MCP tools provide, formatted for the browser frontend.

---

## 5. Path to Connecting a Real Operator

### What Changes

When a real drone operator (e.g., a DJI Dock 2 running yakrover-8004-mcp) connects:

1. **Discovery bridge:** The operator registers their robot via ERC-8004 agent card. The marketplace's `discovery_bridge.py` polls for new registrations or receives webhook notifications.

2. **MCP endpoint swap:** Instead of fakerover's in-process simulator, the fleet server routes to the operator's remote MCP server:
   ```json
   {
     "real-drone-01": {
       "type": "http",
       "url": "https://operator-fleet.ngrok-free.app/drone-01/mcp",
       "headers": { "Authorization": "Bearer OPERATOR_TOKEN" }
     }
   }
   ```

3. **Authentication:** Each operator gets a unique bearer token. Generated during onboarding, stored in the platform database, validated by middleware on every MCP call. The marketplace never exposes one operator's token to another.

4. **Bidding flow:** The operator's MCP server exposes a `bid()` tool. When a task matches their capabilities, the marketplace calls `bid()` on their server. The operator's agent decides price and SLA autonomously.

### Configuration for Real Operator

```bash
# On the marketplace server, register the operator
railway variables set OPERATOR_DRONE01_URL=https://operator-fleet.example.com/drone-01/mcp
railway variables set OPERATOR_DRONE01_TOKEN=<operator-specific-token>
```

The `discovery_bridge.py` reads these and adds the operator to the fleet roster dynamically.

---

## 6. Monitoring and Ops

### What to Monitor

| Metric | Tool | Alert threshold |
|--------|------|-----------------|
| Uptime | Railway metrics / UptimeRobot (free) | <99% over 24h |
| Response latency (p95) | Railway metrics | >2s on /fleet/mcp |
| Auction completion rate | Custom: log `settled` vs `posted` ratio | <50% completion |
| Payment failures | Stripe dashboard + SQLite audit log | Any failure |
| SQLite DB size | Railway volume metrics | >500MB (time to migrate) |
| Memory usage | Railway dashboard | >80% of plan limit |

### Logging Strategy

The server already logs via Python `logging`. On Railway, stdout/stderr is captured automatically.

```bash
# View logs
railway logs

# Filter for payment events
railway logs | grep PAYMENT

# Filter for errors
railway logs | grep ERROR
```

Key log events to ensure are emitted:
- `AUCTION: Task posted {request_id}` -- every new task
- `AUCTION: Bid accepted {request_id} -> {robot_id}` -- every acceptance
- `PAYMENT: Settlement {request_id} ${amount} via {method}` -- every payment
- `ERROR: Settlement failed {request_id}: {reason}` -- every payment failure

### Uptime Monitoring (Free)

Set up UptimeRobot (free tier: 50 monitors, 5-min checks):
- Monitor: `GET https://marketplace.up.railway.app/`
- Alert: Email + webhook on downtime

---

## 7. Cost Estimate

### MVP (Now -- Low Traffic)

| Item | Monthly cost |
|------|-------------|
| Railway Hobby plan | $5 (includes $5 credit) |
| Railway volume (1GB) | $0.25 |
| Custom domain (yakrobot.bid API) | $0 (included) |
| UptimeRobot | $0 (free tier) |
| Stripe test mode | $0 |
| **Total** | **~$5/mo** |

### When to Upgrade

| Trigger | Action | New cost |
|---------|--------|----------|
| >1 concurrent user testing | Stay on Railway, monitor usage | ~$10/mo |
| Need horizontal scaling (2+ instances) | Add Railway Postgres, drop SQLite | +$5/mo for Postgres |
| >1000 requests/day sustained | Move to Railway Pro ($20/mo) or Fly.io | $20-30/mo |
| Production with real payments | Add monitoring (Sentry $26/mo), dedicated DB | ~$50-70/mo |
| Multi-region (operators worldwide) | Migrate to Fly.io for edge deployment | ~$30-50/mo |

---

## Quick-Start Checklist

- [ ] Create `Dockerfile` in repo root (section 3a)
- [ ] `railway login && railway init`
- [ ] Add volume, set env vars (section 3b)
- [ ] `railway up`
- [ ] Verify health check and MCP endpoint (section 3c)
- [ ] Run `claude mcp add-json` locally (section 4a)
- [ ] Test "What robots are available?" in Claude Code
- [ ] Update yakrobot.bid `API_BASE` to point to Railway URL
- [ ] Set up UptimeRobot monitor
