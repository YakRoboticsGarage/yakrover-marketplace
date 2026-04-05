# Demo Testing Checklist

**Problem:** Demo has been deployed multiple times without end-to-end testing, leading to repeated failures during live runs. This checklist must be followed before any demo deployment.

---

## Pre-Deployment Checklist

### 1. Local verification (before deploying anything)

```bash
cd /Users/rafa/Documents/robots/robot-marketplace

# Test RFP processor generates correct task category
PYTHONPATH=. uv run python -c "
from auction.rfp_processor import process_rfp
specs = process_rfp('Environmental monitoring. Temperature and humidity at 3 waypoints in server room.', use_llm=False)
assert specs[0]['task_category'] == 'env_sensing', f'WRONG: {specs[0][\"task_category\"]}'
assert 'temperature' in specs[0]['capability_requirements']['hard']['sensors_required']
print('✓ RFP processor: env_sensing detected')
"

# Test auction gets bids (not withdrawn)
PYTHONPATH=. uv run python -c "
from auction.engine import AuctionEngine
from auction.mock_fleet import create_full_fleet
from auction.wallet import WalletLedger
from auction.rfp_processor import process_rfp
from decimal import Decimal
wallet = WalletLedger()
wallet.create_wallet('buyer', Decimal('0'))
wallet.fund_wallet('buyer', Decimal('1000'))
fleet = create_full_fleet()
engine = AuctionEngine(fleet, wallet=wallet)
specs = process_rfp('Environmental monitoring. Temperature and humidity at 3 waypoints.', use_llm=False)
spec = specs[0]
spec['budget_ceiling'] = Decimal('1.00')
spec['sla_seconds'] = 3600
result = engine.post_task(spec)
assert result['state'] == 'bidding', f'WRONG STATE: {result[\"state\"]}'
bids = engine.get_bids(result['request_id'])
assert bids['bid_count'] >= 1, f'NO BIDS: {bids[\"bid_count\"]}'
print(f'✓ Auction: {bids[\"bid_count\"]} bids, winner: {bids[\"recommended_winner\"]}')
"

# Run full test suite
uv run pytest auction/tests/ -q --tb=short --ignore=auction/tests/integration --ignore=auction/tests/test_fakerover_bid.py
```

### 2. Restart MCP server (if code changed in auction/ or mcp_server.py)

```bash
# Kill existing server (Ctrl+C)
PYTHONPATH=. uv run python mcp_server.py
# Verify: should show "Fleet: 10 operators"
# Verify: FakeRoverBay3 and FakeRoverBay7 should appear with temperature, humidity sensors
```

### 3. Redeploy worker (if code changed in chatbot/src/index.js)

```bash
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
cd chatbot && npx wrangler deploy
```

### 4. Verify worker is live with new code

```bash
# Test health
curl -sS 'https://yakrobot-chat.rafaeldf2.workers.dev/api/health'

# Test RFP processing via worker (sends to MCP server via tunnel)
# Start tunnel first: cloudflared tunnel --url http://localhost:8001
# Then test:
curl -sS 'https://yakrobot-chat.rafaeldf2.workers.dev/api/demo' \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Environmental monitoring. Temperature readings at 3 waypoints.","tunnel_url":"YOUR_TUNNEL_URL"}' | python3 -c "
import sys,json
d = json.load(sys.stdin)
steps = d.get('steps', [])
print(f'Steps: {len(steps)}')
for s in steps:
    if s.get('type') == 'tool_call':
        print(f'  {s[\"tool_name\"]}: {\"error\" if \"error\" in str(s.get(\"result\",{})) else \"ok\"}')
"
```

### 5. Deploy demo page (if HTML changed)

```bash
cd docs/mcp_demo_2 && /Users/rafa/.claude/skills/here-now/scripts/publish.sh . --slug quartz-quail-vcrz --client claude-code
```

### 6. End-to-end browser test

1. Open https://yakrobot.bid/mcp-demo-2/
2. Verify: Tumbller appears in discovery (via RPC fallback)
3. Paste tunnel URL, click Test → "Connected: 35 tools, 10 operators"
4. Click Run Auction → should process RFP → get bids → award → execute → deliver
5. Verify: delivery shows schema validation PASS
6. Test USDC payment: sign permit → commit → release
7. Test Stripe payment: card 4242... → checkout → confirmation
8. Test feedback: rate + submit

---

## Current Blocker

The worker needs redeployment after every change to `chatbot/src/index.js`. This is a manual step that's been missed multiple times. The MCP server also needs restarting after changes to `auction/` or `mcp_server.py`.

**Rule: If you change code, restart/redeploy BEFORE testing the demo.**
