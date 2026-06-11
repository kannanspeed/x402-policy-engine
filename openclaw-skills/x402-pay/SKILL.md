# x402-Pay — Autonomous Payment Skill for OpenClaw

**Give any OpenClaw agent a wallet + autonomous spending policy.**

## What it does

Wraps any tool call with x402 micro-payment headers. AI agents pay for APIs, data, and compute — without human approval.

## Usage

```yaml
name: x402-pay
version: 1.0.0
description: Autonomous x402 micro-payments with policy guardrails
trigger: pay <recipient> <amount>
```

```
pay api.openai.com/v1/chat/completions 0.05
pay api.coinbase.com/v1/prices 0.02
pay api.anthropic.com/v1/messages 0.08
```

## Features

- **Session keys** — user signs once, agent pays freely
- **Spending policies** — daily budget, per-tx limits, allowlists
- **Kill switch** — revoke all spending instantly
- **ERC-8004 integration** — trust scores feed into spending limits
- **Multi-chain** — Base, Arbitrum, Optimism, Ethereum, BSC

## Setup

```bash
pip install x402-policy
export WALLET_PRIVATE_KEY=0x...
```

## Policy Configuration

```python
from x402_policy import create_policy, TimeWindow

policy = create_policy(
    daily_budget=5.0,          # $5/day max
    per_tx_max=0.10,          # $0.10 per call
    allowlist=["api.openai.com", "api.coinbase.com", "api.anthropic.com"],
    time_windows=[TimeWindow(start_hour=6, end_hour=22)]  # 6am-10pm UTC
)
```

## Commands

| Command | Description |
|---|---|
| `pay <recipient> <amount>` | Execute autonomous payment |
| `pay-status` | Show remaining budget + session info |
| `pay-policy` | Display current policy rules |
| `pay-kill` | Activate kill switch (block all payments) |
| `pay-reset` | Reset daily counters |

## Example Session

```
user: pay api.coinbase.com/v1/prices 0.02
agent: ✅ Payment approved — $0.02 → api.coinbase.com
       tx: 0x8f2e...a3b1
       remaining budget: $4.98

user: pay random-site.com 0.05
agent: ❌ Payment denied — recipient not in allowlist

user: pay-status
agent: Daily budget: $5.00
       Spent today: $0.02
       Remaining: $4.98
       Session expires: 2026-06-06 06:00 UTC
```

## Dependencies

- `x402-policy>=0.2.0`
- `web3>=6.0.0`
- `eth-account>=0.9.0`

## Links

- PyPI: https://pypi.org/project/x402-policy/
- Docs: https://x402-policy.dev/docs
- GitHub: https://github.com/x402-policy/x402-policy-engine

## Author

x402 Policy Engine — open-source AI agent payment infrastructure