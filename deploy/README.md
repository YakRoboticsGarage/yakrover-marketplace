# Remote Demo — Connect Claude to the Marketplace

Run the MCP server on your machine and let anyone connect their Claude to interact with the construction survey marketplace.

## For the Demo Host (you)

### Quick start (local only)

```bash
cd yakrover-marketplace
PYTHONPATH=. uv run python mcp_server.py
```

Server runs at `http://localhost:8001`. Connect your own Claude:

```bash
claude mcp add --transport http yakrover http://localhost:8001/mcp
```

### Public access (free Cloudflare Tunnel)

```bash
# Install cloudflared (one time)
brew install cloudflared

# Start server + tunnel
./deploy/tunnel.sh
```

This gives you a public `https://xxxxx.trycloudflare.com` URL. Share it with anyone.

### Stable URL (on your domain)

If you want a permanent URL like `mcp.yakrobot.bid`:

```bash
# One-time setup
cloudflared tunnel create yak-demo
cloudflared tunnel route dns yak-demo mcp.yakrobot.bid

# Run
cloudflared tunnel run --url http://localhost:8001 yak-demo
```

## For the GC (person connecting)

### Claude Code (terminal)

```bash
claude mcp add --transport http yakrover https://YOUR-URL-HERE/mcp
```

### Claude Desktop (GUI)

Add to your MCP config file:

```json
{
  "mcpServers": {
    "yakrover": {
      "type": "http",
      "url": "https://YOUR-URL-HERE/mcp"
    }
  }
}
```

### What to say

Try these:

> "I need a topographic survey for a 6-mile highway corridor in Kalamazoo County, Michigan. Budget around $50,000. Need the data in 2 weeks."

> "Process this RFP: [paste your RFP text here]"

> "What drone survey operators are available in Michigan for bridge inspection?"

> "I have a payment bond from Travelers. Can you verify it?"

### What happens

1. Claude decomposes your request into survey tasks (topo, GPR, photogrammetry, etc.)
2. Posts tasks to the marketplace
3. 7 Michigan operators bid (Great Lakes Aerial, Wolverine Survey Tech, Petoskey Drone Works, Midwest GPR, Trident Inspection, ClearLine Survey, Meridian Geospatial)
4. Claude reviews bids, checks compliance (PLS license, FAA Part 107, insurance)
5. Recommends a winner based on price, SLA, confidence, and reputation
6. Verifies payment bond against real Treasury Circular 570 data (501 surety companies)
7. Generates a ConsensusDocs 750 subcontract agreement
8. You review and confirm

### 32 tools available

| Category | Tools |
|----------|-------|
| RFP Processing | process_rfp, validate_task_specs, get_site_recon |
| Task Lifecycle | post_task, get_bids, accept_bid, execute, confirm_delivery, reject_delivery, cancel_task |
| Buyer Review | review_bids, award_with_confirmation |
| Compliance | verify_bond, verify_bond_pdf, verify_operator_compliance, upload_compliance_doc, compare_terms, check_sam_exclusion |
| Agreements | generate_agreement, track_execution, list_tasks |
| Operator | register_operator, add_equipment, activate_operator, onboard_operator, get_operator_status |
| Wallet | fund_wallet, get_wallet_balance |
| Convenience | quick_hire, accept_and_execute, get_task_schema, get_status |

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | For LLM RFP parsing | — | Enables semantic RFP extraction |
| `STRIPE_SECRET_KEY` | No | — | Enables real payment processing |
| `AUCTION_DB_PATH` | No | In-memory | SQLite persistence path |
| `SAM_GOV_API_KEY` | No | — | Real federal debarment checks |
| `MCP_BEARER_TOKEN` | No | — | Optional auth token |
