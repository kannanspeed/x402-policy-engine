# TAP Resolver — Cross-Chain ERC-8004 Trust Aggregator

**Trustless Agent Plus (TAP) — the canonical cross-chain identity layer for AI agents.**

## What it does

Aggregates ERC-8004 agent identity and reputation across all 23+ chains into a single unified trust score. This is what paying agents query before sending x402 payments to unknown counterparty agents.

## Usage

```yaml
name: tap-resolver
version: 1.0.0
description: Cross-chain ERC-8004 identity + reputation aggregator (TAP spec)
trigger: tap <agent_id>
```

```
tap 0xAgentId
tap-verify 0xAgentId --chain base
tap-score 0xAgentId
```

## What is TAP?

Trustless Agent Plus (TAP) is a proposed aggregation layer for ERC-8004. The problem:

- 200K+ ERC-8004 agents registered across 23+ chains
- Each chain gives the same agent a different ID
- Reputation (~194K records) locked in per-chain silos
- No on-chain way to verify "Agent #2065 on Base" = "Agent #5249 on BSC"

TAP solves this by reading the cross-chain registrations array and computing a weighted trust score.

## Features

- **Cross-chain resolution** — aggregates identity from 23+ chains
- **Weighted reputation** — activity-weighted trust score
- **Owner consistency** — detects if same owner controls agent on multiple chains
- **TAP verification** — full trust report for payment decisions
- **Payment approval** — direct integration with x402 policy engine

## Setup

```bash
pip install x402-policy
```

## Commands

| Command | Description |
|---|---|
| `tap <agent_id>` | Full TAP resolution + trust score |
| `tap-verify <id>` | Verification result for x402 payment |
| `tap-score <id>` | Trust score (0-5) with breakdown |
| `tap-chains <id>` | All chains agent is registered on |

## Example Output

```
tap 0xdeadbeef...
🔗 TAP Resolution: 0xdeadbeef...
✅ Payment Approved
   Trust Score: 4.1/5.0 (TRUSTED)
   Chains: 4 (Base, Arbitrum, Optimism, BSC)
   Owner consistency: 100%
   Recommendation: APPROVE

   Chain Breakdown:
   - Base: 4.3 ⭐
   - Arbitrum: 4.0 ⭐
   - Optimism: 4.2 ⭐
   - BSC: 3.9 ⭐

   Elevated limits: ✅ ENABLED
   (Higher spending caps for trusted agents)
```

## Integration with x402-pay

```
# Before paying an unknown agent, check TAP first:
tap 0xCounterpartyAgent
# If trusted → proceed with payment
# If not trusted → use strict limits or reject
```

## Why this matters

- x402 volume collapsed 77% from manual approval friction
- ERC-8004 gives agents on-chain identity but no cross-chain aggregation
- TAP fills the gap — becomes the "credit bureau for AI agents"
- Every x402 payment to a new counterparty needs a TAP lookup

## References

- TAP Spec: Trustless Agent Plus (proposed)
- ERC-8004: https://eips.ethereum.org/EIPS/eip-8004
- x402 Protocol: https://x402.org
- Agent.market: https://agent.market

## Author

x402 Policy Engine — open-source TAP implementation