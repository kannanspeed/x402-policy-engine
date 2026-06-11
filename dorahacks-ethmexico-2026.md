# x402 Policy Engine — DoraHacks Ethereum Mexico 2026 Submission

**Project:** x402 Policy Engine — Autonomous Payment Infrastructure for AI Agents
**Team:** Solo Builder
**Track:** AI × Blockchain
**Prize:** $1,080

---

## What We Built

x402 Policy Engine is a Python SDK that gives AI agents the ability to pay autonomously via x402 micro-payments — without human wallet approval on every transaction.

**The problem it solves:**
- AI agents need to pay for APIs, data, and compute
- x402 protocol enables micro-payments but every tx needs 5-15 seconds of manual approval
- Average x402 tx = $0.52 — friction cost exceeds transaction value
- 2.89M monthly x402 transactions, but volume collapsed 77% from peak

**Our solution:**
1. Session Keys (EIP-3009/EIP-4337) — user signs once, agent transacts freely for 24 hours
2. TAP Resolver — cross-chain ERC-8004 trust scoring for agent reputation
3. Policy Engine — spending caps, allowlists, kill-switch, rate limits
4. Gasless Relayer — sponsor transactions, earn 0.1% on settled volume

---

## Tech Stack

- Python 3.11+
- web3.py, eth_account, eth_hash
- x402 protocol (HTTP 402)
- ERC-8004 (Trustless Agents on Ethereum)
- EIP-3009 / EIP-4337 (Account Abstraction)
- FastAPI dashboard

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
│   └── server.py         # MCP server (14 tools)
├── openclaw-skills/
│   ├── x402-pay/
│   ├── erc8004-id/
│   └── tap-resolver/
├── index.html             # Landing page
├── demo.py               # Integration demo
└── requirements.txt
```

---

## How It Works

```python
from x402_policy import SessionKeyManager, TAPResolver

# Create session key (user signs once)
manager = SessionKeyManager(wallet_private_key="0x...")
session = await manager.create_session(
    daily_limit=5.0,
    per_tx_limit=0.10,
    window_hours=24
)

# Agent pays autonomously
result = await manager.execute_payment(
    session=session,
    recipient="api.coinbase.com",
    amount=0.05,
    description="ETH price feed"
)
```

---

## Demo

```bash
pip install x402-policy
python demo.py
```

MCP tools: tap_resolve, tap_verify, tap_score, session_create, session_pay, session_status, session_revoke, policy_create, policy_approve, x402_pay, x402_status

---

## Why AI × Blockchain

AI agents need to pay for:
- Price feeds (CoinGecko, CoinBase)
- LLM API calls (OpenAI, Anthropic)
- Data services
- Compute resources

x402 enables machine-to-machine payments. Our policy engine makes them autonomous. Together they form the payment layer for the agent economy.

---

## Future Plans

- Publish to PyPI (`pip install x402-policy`)
- List on Agent.market (Coinbase's agent app store)
- Apply for Ethereum Foundation / Base ecosystem grants
- Ship x402-spend (buyer-side SDK) and AP2 Mandate SDK

---

**Contact:** hello@x402-policy.dev
**GitHub:** github.com/x402-policy/x402-policy-engine
**License:** MIT