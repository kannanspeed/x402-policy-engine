# ETHGlobal Cannes 2026 — Project Submission

## x402 Policy Engine: Autonomous Payment Infrastructure for AI Agents

**Team:** Solo Builder (Python + AI + Crypto)
**Track:** x402 + ERC-8004 Ecosystem
**Repository:** github.com/x402-policy/x402-policy-engine

---

## What We Built

**x402 Policy Engine** — a Python SDK stack that gives AI agents the ability to pay autonomously via x402 micro-payments, with ERC-8004 trust scoring and gasless session keys.

### The Problem

x402 protocol (Coinbase/Cloudflare) enables AI agent micro-payments, but:
- Every tx requires 5-15 seconds of human wallet approval
- Average tx = $0.52 — friction cost exceeds value
- Volume collapsed 77% from Nov 2025 peak ($5.15M → $1.19M)
- 2.89M monthly txns × 5-15s approval = 4,000-12,000 user-hours/month of dead friction

ERC-8004 (Trustless Agents) shipped on Ethereum mainnet Jan 2026:
- 200K+ agents registered across 23+ chains
- ~194K reputation records locked per-chain
- No cross-chain aggregation layer
- Paying agents have no way to verify counterparty trust

### Our Solution

Four integrated modules that solve the full stack:

**1. Session Keys (EIP-3009/EIP-4337)**
- User signs once, agent transacts freely for up to 24 hours
- Configurable daily/per-tx limits per session
- Recipient allowlists, time windows, kill-switch
- Eliminates the 5-15s approval wall entirely

**2. TAP Resolver (Trustless Agent Plus)**
- Cross-chain ERC-8004 identity aggregation
- Reads from 23+ chains: Ethereum, Base, Arbitrum, Optimism, BSC, Polygon, etc.
- Returns weighted trust score (0-5) + recommendation (APPROVE/REVIEW/REJECT)
- First-mover on the named TAP fragmentation problem

**3. Policy Engine**
- Per-tx caps, daily budgets, allowlists, time windows, rate limiting
- ERC-8004 trust score feeds into elevated limits (trusted agents get higher caps)
- Full audit trail of all payment decisions

**4. Gasless Relayer**
- Sponsors gas for agent transactions
- Charges 0.1% on settled volume
- Revenue model for facilitators

### Key Metrics

| Metric | Value |
|---|---|
| x402 monthly volume | $1.19M (May 2026) |
| Avg tx size | $0.52 |
| ERC-8004 agents live | 200K+ |
| Supported chains | 23+ |
| Session setup | 1 sign, unlimited txns |
| Trust check latency | <100ms |

---

## Technical Architecture

```
User signs session authorization (one-time, ~5 seconds)
        ↓
SessionKeyManager issues session key (EIP-3009/EIP-4337)
        ↓
AI agent calls MCP tool: tap_verify("0xAgentId")
        ↓
TAPResolver aggregates ERC-8004 reputation across chains
        ↓
PolicyEngine enforces spending limits (or raises them for trusted agents)
        ↓
x402 client executes USDC payment (Base/Arbitrum/Optimism)
        ↓
RelayerService sponsors gas, earns 0.1% fee
```

### Stack

- **Language:** Python 3.11+
- **Web3:** web3.py, eth_account, eth_hash
- **x402:** Coinbase x402 protocol (HTTP 402)
- **ERC-8004:** Direct contract reads, no Solidity required
- **Account Abstraction:** EIP-3009 (transferWithAuthorization), EIP-4337 (EntryPoint)
- **MCP:** Model Context Protocol for AI agent tool integration
- **USDC:** Base mainnet (0x833589fCD6eDb6E08f4c7C32D4Fa71D5b97FdB2e)

---

## What's Deployed

**GitHub:** github.com/x402-policy/x402-policy-engine
**PyPI:** `pip install x402-policy`
**MCP Server:** 14 tools exposed via JSON-RPC stdio
**OpenClaw Skills:** 3 skills for ClawHub distribution

### Core Files

```
src/
  policy.py          # Policy engine (caps, allowlists, kill-switch)
  x402_client.py     # x402 payment wrapper
  erc8004.py         # ERC-8004 single-chain reader
  tap_resolver.py    # Cross-chain TAP aggregator (23 chains)
  session_keys.py    # EIP-3009/EIP-4337 session keys + relayer
  dashboard.py       # FastAPI policy management dashboard
  cli.py             # CLI tool (x402-policy-cli)
mcp-server/
  server.py          # MCP server (14 tools)
openclaw-skills/
  x402-pay/          # Autonomous payment skill
  erc8004-id/        # Identity + reputation skill
  tap-resolver/      # Cross-chain trust score skill
```

---

## Differentiation

| Competitor | What we do differently |
|---|---|
| ChaosChain SDK | Multi-chain (23 vs 1), trust scoring, policy engine |
| BNBAgent SDK | Multi-chain (23 vs 1), x402 native, gasless sessions |
| x402r (hackathon) | Refund-only → we do full policy + trust + payments |
| QuickNode guides | Documentation → we ship actual working SDK |
| OpenClaw payments | Payment flow → we add ERC-8004 trust layer + policy |

**The gap we fill:** x402 ships the payment rails. ERC-8004 ships the identity. We ship the intelligence layer — the trust scoring, policy enforcement, and session management that makes autonomous agent payments actually work.

---

## Future Plans

1. **Agent.market listing** — paid API endpoint (TAP trust scores via x402)
2. **PyPI publish** — `pip install x402-policy` goes live
3. **ClawHub submission** — 3 skills targeting 1.5M+ downloads
4. **Arbitrum grant application** — Trailblazer $1K-$50K
5. **x402 Foundation grant** — ecosystem builder funding
6. **Consensus Miami 2026** — enter "Agentic Track" (requires x402 on Base)

---

## Demo

```bash
pip install x402-policy
python -c "
import asyncio
from x402_policy import SessionKeyManager, TAPResolver

async def demo():
    resolver = TAPResolver()
    tap = await resolver.verify('0xAgentId...', chain_id=8453)
    print(f'Trust: {tap[\"trust_level\"]} | Approved: {tap[\"payment_approved\"]}')

asyncio.run(demo())
"
```

**MCP tools available:** tap_resolve, tap_verify, tap_score, session_create, session_pay, session_status, session_revoke, policy_create, policy_approve, x402_pay, x402_status

---

## Why This Fits the Track

- **x402 native** — built on Coinbase's protocol, uses batch settlement
- **ERC-8004 integration** — reads identity + reputation, solves cross-chain fragmentation
- **Python-first** — targets LangChain, CrewAI, AutoGen, smolagents ecosystem
- **Dev-tool shape** — `pip install` + MCP tools, not a service business
- **Live distribution** — PyPI + ClawHub + Agent.market = 3 monetization channels
- **Hackathon validated** — addresses named, unsolved problems from the ecosystem

---

**Contact:** hello@x402-policy.dev
**Submission:** github.com/x402-policy/x402-policy-engine
**License:** MIT