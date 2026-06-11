# x402 Policy Engine — Google Cloud Rapid Agent Hackathon

**Project:** x402 Policy Engine — Autonomous Payment Infrastructure for AI Agents
**Partner Bucket:** MongoDB or Arize (payment + observability combo)
**Submission:** Devpost + public GitHub repo + demo video

---

## TL;DR

x402 Policy Engine gives AI agents a wallet — they pay autonomously for APIs, data, and compute via x402 micro-payments. Built with Python + MCP (14 tools). Existing repo, not a new build.

**Demo URL:** (demo video link)
**Repo:** github.com/x402-policy/x402-policy-engine
**Stack:** Python 3.11+ | MCP | ERC-8004 | EIP-3009 | x402 Protocol

---

## Problem

AI agents need to pay for:
- Price feeds (CoinGecko, OpenAI, Anthropic)
- Data services (Fivetran, Elastic)
- Compute resources

But every x402 payment requires 5-15 seconds of manual wallet approval. Average transaction = $0.52. Friction cost exceeds the transaction value. This is why 2.89M monthly x402 transactions dropped 77% from peak.

**The agent economy can't scale without autonomous payments.**

---

## Solution

x402 Policy Engine — a Python SDK that makes AI agents self-sufficient payers:

```
from x402_policy import SessionKeyManager

# User signs once. Agent pays freely for 24 hours.
session = await manager.create_session(daily_limit=5.0, per_tx_limit=0.10)
result = await manager.execute_payment(session, "api.openai.com", 0.03)
```

**How it works:**
1. **Session Keys** — EIP-3009/EIP-4337. User signs once, agent has 24h spending window
2. **TAP Resolver** — cross-chain ERC-8004 trust scoring. Agents with good reputation get higher limits
3. **Policy Engine** — spending caps, allowlists, blocklists, kill-switches, rate limits
4. **Gasless Relayer** — sponsor transactions, earn 0.1% on settled volume
5. **MCP Server** — 14 tools exposed to any MCP-compatible AI client

---

## MCP Integration (Core)

The MCP server exposes 14 tools to any MCP-compatible AI client:

| Category | Tools |
|---|---|
| Trust & Reputation | `tap_resolve`, `tap_verify`, `tap_score` |
| Session Management | `session_create`, `session_pay`, `session_status`, `session_revoke`, `session_list` |
| Policy Engine | `policy_create`, `policy_approve`, `policy_stats` |
| Payments | `x402_pay`, `x402_status` |

Compatible with: Claude Code, Cursor, OpenCode, OpenClaw, and any MCP client.

**MCP config:**
```json
{
  "mcpServers": {
    "x402-policy": {
      "command": "python",
      "args": ["mcp_server.py"]
    }
  }
}
```

---

## Demo Flow

1. Agent needs ETH/USD price feed → checks trust score via `tap_score`
2. If trusted → creates session key (user approves once)
3. Agent pays $0.05 via `x402_pay` → gets price data
4. Session auto-manages budget, rate limits, kill-switch

**Real world use case:** An AI trading bot on Base pays 14 API providers autonomously, 200+ times per day, without human approval on each tx.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  AI Agent (Claude/Cursor/OpenCode)          │
└────────────────┬───────────────────────────┘
                 │ MCP (14 tools)
┌────────────────▼───────────────────────────┐
│  x402 Policy Engine                        │
│  ├── Session Keys (EIP-3009)               │
│  ├── TAP Resolver (ERC-8004 cross-chain)   │
│  ├── Policy Engine (caps, allowlists)      │
│  └── Gasless Relayer                      │
└────────┬──────────────────────┬─────────────┘
         │                      │
┌────────▼────────┐  ┌──────────▼──────────────┐
│  x402 APIs      │  │  Blockchain (Base/Sol)   │
│  (OpenAI, etc.) │  │  (Session Key txs)      │
└─────────────────┘  └─────────────────────────┘
```

---

## Partner Integration

**MongoDB** — Store agent payment history, session logs, policy decisions:
```python
# Store session in MongoDB
sessions_col.insert_one({
    "session_id": session.key_id,
    "agent_id": agent_id,
    "daily_limit": 5.0,
    "spent": [],
    "created_at": datetime.utcnow()
})
```

**Arize** — Observability for AI agent payment decisions:
```python
# Log payment decision to Arize
arize.log(
    observation_id=tx_hash,
    prediction_id=agent_id,
    features={"trust_score": score, "amount": amount, "approved": approved}
)
```

---

## Technical Stack

- Python 3.11+
- web3.py, eth_account, eth_hash
- x402 protocol (HTTP 402)
- ERC-8004 (Trustless Agents Protocol)
- EIP-3009 / EIP-4337 (Account Abstraction)
- FastAPI dashboard
- MongoDB + Arize integration

---

## Files

```
x402-policy-engine/
├── src/
│   ├── policy.py          # Policy engine
│   ├── x402_client.py     # x402 payment wrapper
│   ├── erc8004.py         # ERC-8004 identity reader
│   ├── tap_resolver.py    # Cross-chain TAP aggregator
│   ├── session_keys.py    # Session keys + gasless relayer
│   ├── dashboard.py       # FastAPI dashboard
│   └── cli.py             # CLI tool
├── mcp-server/
│   └── server.py         # MCP server (14 tools) ← CORE ASSET
├── openclaw-skills/
│   ├── x402-pay/
│   ├── erc8004-id/
│   └── tap-resolver/
├── index.html             # Landing page
├── demo.py               # Integration demo
└── requirements.txt
```

---

## Why This Matters

We're building the **payment layer for the agent economy**.

Today: AI agents can't pay without humans.
Tomorrow: Every AI agent has its own wallet, spends autonomously, earns revenue.

x402 Policy Engine is the infrastructure that makes this possible — open source, Python-first, MCP-native.

---

**Contact:** hello@x402-policy.dev
**Repo:** github.com/x402-policy/x402-policy-engine
**License:** MIT
**Demo:** (YouTube video)