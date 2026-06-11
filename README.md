# x402 Policy Engine

**Python SDK for autonomous AI agent micro-payments.**

`pip install x402-policy`

---

## What is this?

x402 Policy Engine gives AI agents the ability to pay for APIs, data, and compute **without human approval**.

- **Session keys** — user signs once, agent transacts freely (no 5-15s approval wall)
- **ERC-8004 trust scoring** — cross-chain reputation via TAP resolver
- **Policy guardrails** — daily caps, per-tx limits, allowlists, kill-switch
- **Gasless relayer** — sponsor transactions, earn 0.1% on settled volume

Built on Coinbase's [x402 protocol](https://x402.org) + Ethereum's [ERC-8004 Trustless Agents](https://eips.ethereum.org/EIPS/eip-8004).

---

## Quick Start

```python
from x402_policy import (
    PolicyConfig,
    SessionKeyManager,
    TAPResolver,
    create_policy,
    TimeWindow
)
import asyncio

async def main():
    # 1. Create a session key (user signs once)
    manager = SessionKeyManager(
        wallet_private_key=os.environ["WALLET_PRIVATE_KEY"],
        chain_id=8453  # Base
    )
    session = await manager.create_session(
        daily_limit=5.0,
        per_tx_limit=0.10,
        window_hours=24,
        allowed_recipients=["api.coinbase.com", "api.coingecko.com"]
    )

    # 2. Check agent trust score (cross-chain ERC-8004)
    resolver = TAPResolver()
    tap = await resolver.verify("0xAgentId...", chain_id=8453)
    
    if not tap["payment_approved"]:
        print(f"Agent not trusted: {tap['payment_reason']}")
        return

    # 3. Execute autonomous payment
    result = await manager.execute_payment(
        session=session,
        recipient="api.coinbase.com/v1/prices",
        amount=0.05,
        description="ETH price feed"
    )
    print(f"✅ Paid ${result['amount_usd']} — tx: {result['tx_hash'][:16]}...")

asyncio.run(main())
```

---

## Core Components

### Policy Engine

```python
from x402_policy import create_policy, TimeWindow

policy = create_policy(
    daily_budget=5.0,
    per_tx_max=0.10,
    allowlist=["api.coinbase.com", "api.openai.com"],
    time_windows=[TimeWindow(start_hour=6, end_hour=22)]
)

result = policy.approve_payment(
    recipient="api.coinbase.com",
    amount=0.02,
    description="ETH price feed"
)
# ✅ Auto-approved under policy
```

### TAP Resolver (ERC-8004 Cross-Chain Reputation)

```python
from x402_policy import TAPResolver

resolver = TAPResolver()
trust = await resolver.score("0xAgentId...", chain_id=8453)

print(f"Trust score: {trust.overall_score}/5.0 ({trust.trust_level.value})")
print(f"Recommendation: {trust.recommendation}")
```

### Session Keys (Gasless Payments)

```python
from x402_policy import SessionKeyManager

manager = SessionKeyManager(wallet_private_key="0x...")
session = await manager.create_session(daily_limit=10.0, per_tx_limit=0.50)

# Agent pays without further approval
result = await manager.execute_payment(
    session=session,
    recipient="api.openai.com",
    amount=0.05
)
```

### x402 Policy Client

```python
from x402_policy import x402PolicyClient, PolicyConfig

client = x402PolicyClient(
    wallet_private_key="0x...",
    policy_config=PolicyConfig(daily_budget=5.0, per_tx_max=0.10)
)

result = await client.pay("api.coinbase.com", 0.05, "Price feed")
```

---

## Architecture

```
User signs session (one-time)
        ↓
SessionKeyManager issues session key
        ↓
TAPResolver checks cross-chain ERC-8004 trust score
        ↓
PolicyEngine enforces spending limits
        ↓
x402 client executes USDC payment
        ↓
RelayerService sponsors gas + takes 0.1% fee
```

---

## Supported Chains

- Ethereum (chain ID: 1)
- Base (chain ID: 8453)
- Arbitrum One (chain ID: 42161)
- Optimism (chain ID: 10)
- BSC (chain ID: 56)
- Polygon (chain ID: 137)
- Avalanche (chain ID: 43114)
- Moonbeam (chain ID: 1284)

---

## Dashboard

Run the FastAPI dashboard for policy management:

```bash
uvicorn x402_policy.dashboard:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API docs.

---

## Use Cases

1. **AI trading agents** — pay for price feeds, market data, exchange APIs
2. **AI research agents** — pay for web searches, data APIs, LLM calls
3. **AI content agents** — pay for media APIs, stock photos, transcription
4. **AI automation agents** — pay for infrastructure, compute, storage

---

## Revenue Model

| Tier | Price | Includes |
|---|---|---|
| Open Source | Free | SDK, session keys, TAP resolver |
| Pro | $49/mo | Hosted dashboard, webhook alerts, relayer service |
| Enterprise | $499/mo | Multi-agent management, SLA, white-label |

---

## Hackathon Targets

- ETHGlobal Cannes 2026
- Consensus Miami 2026
- DoraHacks x402

---

## Links

- [x402 Protocol](https://x402.org)
- [ERC-8004 (Trustless Agents)](https://eips.ethereum.org/EIPS/eip-8004)
- [Agent.market](https://agent.market)
- [x402 Foundation](https://www.x402.org)

---

## License

MIT