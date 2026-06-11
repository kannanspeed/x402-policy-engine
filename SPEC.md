# x402 Policy Engine — Project SPEC

**Last updated:** 2026-06-05 (Day 1 complete)
**Status:** 🚧 BUILDING — Core modules shipped

---

## The Problem

AI agents can't make autonomous micro-payments with x402 because:
- Every tx requires human wallet approval (5–15 seconds of friction)
- Average x402 tx = $0.52 — friction cost exceeds transaction value
- 2.89M x402 txns/month, but volume collapsed **77%** from Nov 2025 peak
- ERC-8004 agents have no cross-chain identity layer — 200K+ agents fragmented across 23+ chains

## The Solution

**x402 Policy Engine** — a Python SDK stack that gives AI agents:
1. **Session keys** — sign once, transact freely (no 5-15s approval wall)
2. **Policy guardrails** — caps, allowlists, kill-switch, rate limits
3. **Cross-chain reputation** — TAP resolver aggregates ERC-8004 trust scores
4. **Gasless relayer** — sponsor transactions, earn 0.1% on settled volume

---

## Modules Built (Day 1)

| Module | File | Status | Purpose |
|---|---|---|---|
| Policy Engine | `src/policy.py` | ✅ | Caps, allowlists, time windows, kill-switch |
| x402 Client | `src/x402_client.py` | ✅ | Wrapped x402 payment with policy enforcement |
| ERC-8004 Reader | `src/erc8004.py` | ✅ | Single-chain identity/reputation reader |
| TAP Resolver | `src/tap_resolver.py` | ✅ | Cross-chain aggregation, trust scores |
| Session Keys | `src/session_keys.py` | ✅ | EIP-3009/EIP-4337 gasless signing |
| Relayer Service | `src/session_keys.py` | ✅ | Gas sponsor + fee extraction |
| FastAPI Dashboard | `src/dashboard.py` | ✅ | Policy management + spending logs |
| Landing Page | `index.html` | ✅ | Sales copy + pricing |

---

## Architecture

```
User signs session authorization (one-time)
        ↓
SessionKeyManager issues session key
        ↓
Agent calls client.pay() or session.execute_payment()
        ↓
TAPResolver checks cross-chain reputation
        ↓
PolicyEngine enforces spending limits
        ↓
RelayerService sponsors gas + takes 0.1% fee
        ↓
x402 payment executes (USDC on Base/Arb/Op)
```

---

## Revenue Model

| Tier | Price | Includes |
|---|---|---|
| Open Source | Free | SDK, session keys, TAP resolver |
| Pro (SaaS) | $49/mo | Hosted dashboard, webhook alerts, relayer service |
| Enterprise | $499/mo | Multi-agent management, SLA, white-label |

**Plus:** Hackathon prize money (ETHGlobal Cannes, Consensus Miami, DoraHacks — $150K+ pool)

---

## Tech Stack

- **Language:** Python 3.11+
- **Web3:** web3.py, eth_account, eth_hash
- **x402:** Coinbase x402 protocol
- **ERC-8004:** Direct contract reads (no Solidity needed)
- **Account Abstraction:** EIP-3009, EIP-4337
- **API:** FastAPI + SQLite
- **USDC:** Base (0x833589fCD6eDb6E08f4c7C32D4Fa71D5b97FdB2e)

---

## 7-Day Build Plan

| Day | Deliverable |
|---|---|
| 1 ✅ | Core modules: policy engine, x402 client, ERC-8004 reader |
| 2 | TAP resolver + cross-chain aggregation |
| 3 | Session keys + gasless relayer |
| 4 | FastAPI dashboard + spending logs |
| 5 | PyPI package + GitHub repo |
| 6 | OpenClaw skill package + ClawHub submission |
| 7 | ETHGlobal Cannes submission + landing page deploy |

---

## OpenClaw Skill Package (for ClawHub)

3 skills targeting 1.5M+ downloads:
1. `x402-pay` — Session key + policy-controlled payments
2. `erc8004-id` — ERC-8004 identity + trust score
3. `tap-resolver` — Cross-chain reputation aggregator

---

## Files

```
x402-policy-engine/
├── src/
│   ├── __init__.py         # Package init
│   ├── policy.py           # Core policy engine
│   ├── x402_client.py       # x402 payment wrapper
│   ├── erc8004.py           # ERC-8004 identity reader
│   ├── tap_resolver.py      # Cross-chain TAP aggregator
│   ├── session_keys.py      # Session keys + relayer
│   └── dashboard.py         # FastAPI dashboard
├── tests/
├── docs/
├── index.html              # Landing page
├── demo.py                  # Integration demo
├── requirements.txt
└── SPEC.md
```

---

## Hackathon Targets

- **ETHGlobal Cannes 2026** — x402 + ERC-8004 prize tracks
- **Consensus Miami 2026** — "Agentic Track" (requires x402 on Base)
- **DoraHacks x402** — $150K prize pool

---

## OpenClaw Skills (ClawHub Distribution)

3 skills for ClawHub — targeting 1.5M+ skill downloads:

| Skill | Path | Purpose |
|---|---|---|
| `x402-pay` | `openclaw-skills/x402-pay/SKILL.md` | Autonomous payments with session keys + policies |
| `erc8004-id` | `openclaw-skills/erc8004-id/SKILL.md` | On-chain identity + reputation reader |
| `tap-resolver` | `openclaw-skills/tap-resolver/SKILL.md` | Cross-chain trust score aggregator |

## Hackathon Submission

✅ **ETHGlobal Cannes 2026 submission drafted** — `ethglobal-cannes-submission.md`

## Current Status

🚧 **Day 1-3 complete** — All core modules + PyPI package + OpenClaw skills + MCP server + Cannes submission

🎯 **Next (in order):**
- [ ] Get PyPI account + API token → publish package
- [ ] Set `WALLET_PRIVATE_KEY` env var → test CLI
- [ ] Deploy landing page to Vercel
- [ ] Submit OpenClaw skills to ClawHub
- [ ] List on Agent.market (TAP trust score API)