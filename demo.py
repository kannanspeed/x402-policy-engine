"""
x402 Policy Engine — Full Integration Demo
Run: python demo.py

Shows the complete flow:
1. Session key creation (user signs once)
2. TAP trust score check (cross-chain ERC-8004 reputation)
3. Policy-controlled payment (caps + allowlists)
4. Gasless relayer (sponsor + 0.1% fee)
"""

import asyncio
import os
from dotenv import load_dotenv

# Import the SDK
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from policy import PolicyConfig, create_policy, TimeWindow
from erc8004 import ERC8004Reader
from tap_resolver import TAPResolver, TrustLevel
from session_keys import SessionKeyManager, RelayerService


async def demo_full_flow():
    """Run the complete x402 agent wallet flow."""
    
    print("=" * 70)
    print("x402 POLICY ENGINE — Full Integration Demo")
    print("   Python SDK for autonomous AI agent payments")
    print("   pip install x402-policy")
    print("=" * 70)
    
    # ============================================
    # STEP 1: Create Session Key (user signs once)
    # ============================================
    print("\n" + "─" * 70)
    print("STEP 1: Session Key Creation")
    print("─" * 70)
    
    # Note: NEVER hardcode private keys in production!
    # Use environment variables: os.environ.get("WALLET_PRIVATE_KEY")
    wallet_key = os.environ.get("WALLET_PRIVATE_KEY", "0x" + "0" * 64)
    
    manager = SessionKeyManager(
        wallet_private_key=wallet_key,
        chain_id=8453  # Base
    )
    
    # User creates a session — signs once, agent can transact freely
    session = await manager.create_session(
        daily_limit=5.0,
        per_tx_limit=0.10,
        window_hours=24,
        description="AI trading agent session",
        allowed_recipients=[
            "api.coinbase.com",
            "api.coingecko.com",
            "api.openai.com",
            "api.anthropic.com",
        ]
    )
    
    print(f"\n✅ Session created:")
    print(f"   Session ID: {session.key_id}")
    print(f"   Session address: {session.session_address}")
    print(f"   Daily limit: ${session.limits.daily_limit_usd}")
    print(f"   Per-tx limit: ${session.limits.per_tx_usd}")
    print(f"   Expires: {session.expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   Allowlist: {len(session.allowed_recipients)} endpoints")
    
    # ============================================
    # STEP 2: TAP Trust Score Check (cross-chain reputation)
    # ============================================
    print("\n" + "─" * 70)
    print("STEP 2: TAP Cross-Chain Trust Score")
    print("─" * 70)
    
    resolver = TAPResolver()
    
    # Demo agent ID (in production: use real ERC-8004 agent ID)
    demo_agent = "0x" + "deadbeef" * 8
    
    print(f"\n🔍 Resolving agent: {demo_agent[:20]}...")
    
    # Full TAP verification
    tap_result = await resolver.verify(demo_agent, chain_id=8453)
    
    print(f"\n📊 TAP Verification Result:")
    print(f"   Agent: {tap_result['agent_id'][:20]}...")
    print(f"   Chain: {tap_result['chain_id']}")
    print(f"   Payment Approved: {'✅ YES' if tap_result['payment_approved'] else '❌ NO'}")
    print(f"   Reason: {tap_result['payment_reason']}")
    print(f"   Elevated Limits: {'✅ ENABLED' if tap_result['elevated_limits'] else '❌ STANDARD'}")
    
    if tap_result['trust_score']:
        ts = tap_result['trust_score']
        print(f"\n   ⭐ Trust Score: {ts.overall_score:.2f}/5.0 ({ts.trust_level.value})")
        print(f"   🏆 Recommendation: {ts.recommendation}")
        print(f"   🔗 Chain Breakdown:")
        for chain, score in ts.chain_breakdown.items():
            print(f"      - {chain}: {score:.1f}")
        if ts.blockers:
            print(f"   ⚠️  Blockers: {ts.blockers}")
    
    # ============================================
    # STEP 3: Policy-Controlled Payment
    # ============================================
    print("\n" + "─" * 70)
    print("STEP 3: Policy-Controlled Payments")
    print("─" * 70)
    
    # Create a policy (alternative to session keys)
    policy = create_policy(
        daily_budget=5.0,
        per_tx_max=0.10,
        allowlist=[
            "api.coinbase.com",
            "api.coingecko.com",
            "api.openai.com",
        ],
        time_windows=[
            TimeWindow(start_hour=6, end_hour=22, timezone="UTC"),
        ]
    )
    
    print("\n📋 Policy created:")
    print(f"   Daily budget: $5.00")
    print(f"   Per-tx max: $0.10")
    print(f"   Time window: 6am-10pm UTC")
    
    # Test payments
    print("\n💳 Testing payments:")
    
    tests = [
        ("api.coinbase.com/v1/prices", 0.02, "ETH price feed", True),
        ("api.coingecko.com/simple", 0.03, "BTC price feed", True),
        ("api.openai.com/v1/chat", 0.05, "GPT-4o mini call", True),
        ("api.coinbase.com/v2/bulk", 1.00, "Bulk data (exceeds limit)", False),
        ("random-site.com/api", 0.01, "Unknown endpoint (not in allowlist)", False),
    ]
    
    for recipient, amount, desc, expected in tests:
        result = policy.approve_payment(
            recipient=recipient,
            amount=amount,
            description=desc
        )
        status = "✅" if result["approved"] else "❌"
        print(f"   {status} {recipient[:35]:35} ${amount:.2f} — {result['reason'][:40]}")
    
    # Stats
    stats = policy.get_spending_stats()
    print(f"\n📊 Policy Stats:")
    print(f"   Spent today: ${stats['spent_today']:.4f}")
    print(f"   Remaining: ${stats['remaining_budget']:.2f}")
    print(f"   Approved: {stats['approved_count']} | Denied: {stats['denied_count']}")
    
    # ============================================
    # STEP 4: Gasless Relayer
    # ============================================
    print("\n" + "─" * 70)
    print("STEP 4: Gasless Relayer (0.1% fee)")
    print("─" * 70)
    
    relayer = RelayerService(
        relayer_private_key=wallet_key,  # In production: separate relayer wallet
        fee_bps=10  # 0.1%
    )
    
    # Simulate relaying a transaction
    user_op = {
        "callData": "0x...",
        "callDataAmount": 5000000,  # $5.00 in USDC (6 decimals)
    }
    
    relay_result = await relayer.relay(user_op, payer=session.session_address)
    
    print(f"\n✅ Transaction relayed:")
    print(f"   Tx hash: {relay_result['tx_hash'][:20]}...")
    print(f"   Fee charged: ${relay_result['fee_charged_usdc']:.4f}")
    print(f"   Relayer: {relay_result['relayer'][:16]}...")
    
    relayer_stats = relayer.get_relayer_stats()
    print(f"\n📊 Relayer Stats:")
    print(f"   Total relayed: {relayer_stats['total_relayed']} txns")
    print(f"   Total volume: ${relayer_stats['total_volume_usd']}")
    print(f"   Total fees: ${relayer_stats['total_fees_usd']}")
    
    # ============================================
    # STEP 5: Session + Policy + TAP Combined
    # ============================================
    print("\n" + "─" * 70)
    print("STEP 5: Combined Flow — Session + Policy + TAP")
    print("─" * 70)
    
    print("\n🤖 AI Agent wants to pay $0.05 for GPT-4o mini...")
    
    # Check TAP trust score first
    tap_check = await resolver.verify(demo_agent, chain_id=8453)
    
    # Determine spending limits based on trust
    if tap_check["elevated_limits"]:
        print("   ✅ Agent is TRUSTED — using elevated limits")
        per_tx = 0.50  # Higher limit for trusted agents
    else:
        print("   ⚠️ Agent is standard — using default limits")
        per_tx = 0.10
    
    # Create a custom policy for this agent
    agent_policy = create_policy(
        daily_budget=10.0 if tap_check["elevated_limits"] else 5.0,
        per_tx_max=per_tx,
        allowlist=["api.openai.com"],
    )
    
    # Execute payment
    result = agent_policy.approve_payment(
        recipient="api.openai.com/v1/chat/completions",
        amount=0.05,
        description="GPT-4o mini call"
    )
    
    print(f"\n   💰 Payment result: {'✅ APPROVED' if result['approved'] else '❌ DENIED'}")
    print(f"   📝 Reason: {result['reason']}")
    print(f"   💵 Remaining budget: ${result.get('remaining_budget', 0):.2f}")
    
    # ============================================
    # DONE
    # ============================================
    print("\n" + "=" * 70)
    print("✅ FULL INTEGRATION DEMO COMPLETE!")
    print("=" * 70)
    print("""
Next steps:
  1. Set WALLET_PRIVATE_KEY in .env
  2. pip install -r requirements.txt
  3. python demo.py
  4. uvicorn src.dashboard:app --reload --port 8000
  5. Open: http://localhost:8000/docs
  
Build targets:
  - PyPI package (Day 5)
  - OpenClaw skills → ClawHub (Day 6)
  - ETHGlobal Cannes submission (Day 7)
    """)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(demo_full_flow())