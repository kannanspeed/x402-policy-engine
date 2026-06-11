# ERC-8004 Identity — On-Chain Agent Identity & Reputation Skill

**Read AI agent identity and reputation from Ethereum's Trustless Agents standard.**

## What it does

Queries the ERC-8004 IdentityRegistry and ReputationRegistry on Base, Arbitrum, Optimism, and 20+ other chains. Returns agent identity, on-chain reputation, and trust scores.

## Usage

```yaml
name: erc8004-id
version: 1.0.0
description: Query ERC-8004 agent identity and reputation on-chain
trigger: agent-info <agent_id>
```

```
agent-info 0x1234...abcd
agent-rep 0xAgentId
agent-trust 0xAgentId --chain base
```

## Features

- **Multi-chain** — reads from 23+ ERC-8004 compatible chains
- **Identity resolution** — owner, name, metadata URI, registration status
- **Reputation scoring** — total ratings, average score, completed tasks
- **Cross-chain aggregation** — unified view across all chains
- **Trust classification** — FLAGGED / NEW / VERIFIED / TRUSTED / ELITE

## Setup

```bash
pip install x402-policy
```

## Commands

| Command | Description |
|---|---|
| `agent-info <id>` | Get agent registration info |
| `agent-rep <id>` | Get agent reputation score |
| `agent-trust <id>` | Get trust level classification |
| `agent-chains <id>` | List all chains agent is registered on |

## Example Output

```
agent-info 0xdeadbeef...
✅ Agent registered on Base (chain 8453)
   Owner: 0xAbc...123
   Name: AI Trading Agent v2
   Metadata: ar://Qm...xyz
   Registered: 2026-01-30 12:00 UTC

agent-rep 0xdeadbeef...
⭐ Reputation: 4.2/5.0
   Total ratings: 127
   Completed tasks: 98
   Avg response time: 230ms

agent-trust 0xdeadbeef...
🏆 Trust Level: TRUSTED
   Recommendation: APPROVE
   Cross-chain: 4 chains verified
   Age: 89 days (established)
```

## Trust Levels

| Level | Score | Meaning |
|---|---|---|
| ELITE | 4.5-5.0 | Top tier, high limits |
| TRUSTED | 3.5-4.5 | Verified, standard limits |
| VERIFIED | 2.5-3.5 | Baseline trusted |
| NEW | 1.0-2.5 | Unproven, strict limits |
| FLAGGED | 0-1.0 | Suspicious, blocked |

## Supported Chains

Ethereum, Base, Arbitrum, Optimism, BSC, Polygon, Avalanche, Moonbeam, Metis, and 15+ more.

## Links

- ERC-8004 Spec: https://eips.ethereum.org/EIPS/eip-8004
- x402 Policy Engine: https://x402-policy.dev