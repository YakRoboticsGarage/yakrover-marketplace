# YAK ROBOTICS Chatbot — Cloudflare Worker

Proxies chat from yakrobot.bid to the Anthropic API. Keeps the API key server-side.

## Architecture

```
yakrobot.bid (static, here.now)
  └── chat widget (JS in demo/index.html)
        └── POST /api/chat
              └── Cloudflare Worker (yakrobot-api)
                    └── Anthropic Messages API (streaming)
```

## Setup

```bash
cd worker
npm install
```

## Configure the API key

```bash
npx wrangler secret put ANTHROPIC_API_KEY
# Paste your Anthropic API key when prompted
```

## Local development

```bash
npx wrangler dev
# Worker runs at http://localhost:8787
```

Update `CHAT_API` in `demo/index.html` to `http://localhost:8787/api/chat` for local testing, then revert before publishing.

## Deploy to Cloudflare

```bash
npx wrangler deploy
# Outputs: https://yakrobot-api.<your-subdomain>.workers.dev
```

## Route to yakrobot.bid/api/chat

After deploy, add a route in `wrangler.toml`:

```toml
[[routes]]
pattern = "yakrobot.bid/api/chat"
custom_domain = true
```

Or configure in the Cloudflare dashboard:
1. Go to Workers & Pages > yakrobot-api > Settings > Triggers
2. Add route: `yakrobot.bid/api/*`
3. Select the zone for yakrobot.bid

Then update `CHAT_API` in `demo/index.html` to `/api/chat` (relative path).

## Update the chat widget URL

In `demo/index.html`, find:
```js
var CHAT_API = '/api/chat';
```

For local dev, change to:
```js
var CHAT_API = 'http://localhost:8787/api/chat';
```

For production with Workers route:
```js
var CHAT_API = '/api/chat';
```

For production without custom route (use the workers.dev URL):
```js
var CHAT_API = 'https://yakrobot-api.<subdomain>.workers.dev/api/chat';
```

## Cost

- Cloudflare Workers free tier: 100K requests/day
- Anthropic API: ~$0.003-$0.015 per chat response (Sonnet 4.6, ~500 tokens avg)
- At 100 chats/day: ~$1/day

## Files

| File | Purpose |
|------|---------|
| `src/index.js` | Worker: CORS, validation, streaming proxy to Anthropic |
| `wrangler.toml` | Cloudflare config (name, env vars, routes) |
| `package.json` | Dev dependency (wrangler CLI) |
| `../demo/index.html` | Chat widget (bottom of file) |
