"""
x402 Policy Engine — CLI Tool

Usage:
    x402-policy-cli trust-score <agent_id> [--chain base]
    x402-policy-cli create-session --daily-limit 5.0 --per-tx 0.10
    x402-policy-cli pay <recipient> <amount>
    x402-policy-cli policy-info
    x402-policy-cli dashboard
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

# Add src to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from policy import PolicyConfig, create_policy
from tap_resolver import TAPResolver
from session_keys import SessionKeyManager


def parse_args():
    parser = argparse.ArgumentParser(
        description="x402 Policy Engine CLI — autonomous AI agent payments",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # trust-score command
    ts_parser = subparsers.add_parser("trust-score", help="Get ERC-8004 trust score for an agent")
    ts_parser.add_argument("agent_id", help="Agent ID (bytes32 hex)")
    ts_parser.add_argument("--chain", default="base", choices=["ethereum", "base", "arbitrum", "optimism", "bsc"],
                          help="Primary chain (default: base)")
    
    # create-session command
    session_parser = subparsers.add_parser("create-session", help="Create a new session key")
    session_parser.add_argument("--daily-limit", type=float, default=5.0, help="Daily spending limit in USD")
    session_parser.add_argument("--per-tx", type=float, default=0.10, help="Per-transaction limit in USD")
    session_parser.add_argument("--window", type=int, default=24, help="Session window in hours")
    session_parser.add_argument("--recipients", nargs="*", help="Allowed recipient domains")
    
    # pay command
    pay_parser = subparsers.add_parser("pay", help="Execute a payment")
    pay_parser.add_argument("recipient", help="Payment recipient URL")
    pay_parser.add_argument("amount", type=float, help="Amount in USD")
    pay_parser.add_argument("--description", default="", help="Payment description")
    
    # policy-info command
    subparsers.add_parser("policy-info", help="Show current policy configuration")
    
    # dashboard command
    subparsers.add_parser("dashboard", help="Start the policy dashboard")
    
    # init command (setup)
    init_parser = subparsers.add_parser("init", help="Initialize x402-policy configuration")
    init_parser.add_argument("--wallet", help="Wallet private key (or set WALLET_PRIVATE_KEY env var)")
    
    return parser.parse_args()


def chain_name_to_id(chain: str) -> int:
    """Convert chain name to chain ID."""
    return {
        "ethereum": 1,
        "base": 8453,
        "arbitrum": 42161,
        "optimism": 10,
        "bsc": 56,
    }[chain]


async def cmd_trust_score(agent_id: str, chain: str):
    """Get trust score for an agent."""
    chain_id = chain_name_to_id(chain)
    print(f"🔍 Resolving trust score for: {agent_id[:20]}...")
    print(f"   Chain: {chain} ({chain_id})")
    
    resolver = TAPResolver()
    score = await resolver.score(agent_id, chain_id)
    
    if not score:
        print("❌ Agent not found in ERC-8004 registry")
        return
    
    print(f"\n⭐ Trust Score: {score.overall_score:.2f}/5.0")
    print(f"   Level: {score.trust_level.value}")
    print(f"   Recommendation: {score.recommendation}")
    
    if score.chain_breakdown:
        print(f"\n📊 Chain Breakdown:")
        for chain_name, chain_score in score.chain_breakdown.items():
            print(f"   - {chain_name}: {chain_score:.1f}")
    
    if score.blockers:
        print(f"\n⚠️  Blockers:")
        for blocker in score.blockers:
            print(f"   - {blocker}")


async def cmd_create_session(daily_limit: float, per_tx: float, window: int, recipients: list):
    """Create a new session key."""
    wallet_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not wallet_key:
        print("❌ Set WALLET_PRIVATE_KEY env var or use --wallet flag")
        print("   export WALLET_PRIVATE_KEY=0x...")
        return
    
    print(f"📝 Creating session...")
    print(f"   Daily limit: ${daily_limit}")
    print(f"   Per-tx limit: ${per_tx}")
    print(f"   Window: {window} hours")
    
    manager = SessionKeyManager(wallet_private_key=wallet_key, chain_id=8453)
    session = await manager.create_session(
        daily_limit=daily_limit,
        per_tx_limit=per_tx,
        window_hours=window,
        allowed_recipients=recipients or []
    )
    
    print(f"\n✅ Session created!")
    print(f"   Session ID: {session.key_id}")
    print(f"   Session address: {session.session_address}")
    print(f"   Expires: {session.expires_at}")
    print(f"   Remaining budget: ${session.remaining_budget():.2f}")
    
    # Save session ID to file for later use
    session_file = os.path.expanduser("~/.x402_policy_session")
    with open(session_file, "w") as f:
        f.write(session.key_id)
    print(f"\n   Session saved to: {session_file}")


async def cmd_pay(recipient: str, amount: float, description: str):
    """Execute a payment using stored session."""
    wallet_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not wallet_key:
        print("❌ Set WALLET_PRIVATE_KEY env var")
        return
    
    # Load session
    session_file = os.path.expanduser("~/.x402_policy_session")
    if not os.path.exists(session_file):
        print("❌ No session found. Run: x402-policy-cli create-session")
        return
    
    with open(session_file, "r") as f:
        session_id = f.read().strip()
    
    print(f"💳 Executing payment...")
    print(f"   Recipient: {recipient}")
    print(f"   Amount: ${amount}")
    
    manager = SessionKeyManager(wallet_private_key=wallet_key, chain_id=8453)
    session = manager.get_session(session_id)
    
    if not session:
        print("❌ Session not found or expired. Create a new one.")
        return
    
    result = await manager.execute_payment(
        session=session,
        recipient=recipient,
        amount=amount,
        description=description
    )
    
    print(f"\n✅ Payment executed!")
    print(f"   TX: {result['tx_hash'][:20]}...")
    print(f"   Amount: ${result['amount_usd']}")
    print(f"   Spent total: ${result['spent_total']:.4f}")
    print(f"   Remaining: ${result['remaining_budget']:.4f}")


def cmd_policy_info():
    """Show policy configuration."""
    print("📋 x402 Policy Engine Configuration")
    print(f"   Version: 0.2.0")
    print(f"   Supported chains: Ethereum, Base, Arbitrum, Optimism, BSC, Polygon, Avalanche")
    print(f"   x402 Protocol: V2 with batch settlement")
    print(f"   ERC-8004: TAP resolver active")
    
    # Show environment status
    wallet = os.environ.get("WALLET_PRIVATE_KEY", "")
    has_wallet = bool(wallet and len(wallet) > 10)
    
    print(f"\n🔐 Wallet: {'✅ Configured' if has_wallet else '❌ Not set (set WALLET_PRIVATE_KEY)'}")
    
    # Check session
    session_file = os.path.expanduser("~/.x402_policy_session")
    if os.path.exists(session_file):
        with open(session_file, "r") as f:
            session_id = f.read().strip()
        print(f"📝 Active session: {session_id}")
    else:
        print(f"📝 Active session: ❌ None (run create-session)")


def cmd_dashboard():
    """Start the policy dashboard."""
    print("🚀 Starting x402 Policy Engine Dashboard...")
    print("   URL: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("\n   Press Ctrl+C to stop\n")
    
    import uvicorn
    from dashboard import app
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


def cmd_init(wallet: Optional[str]):
    """Initialize configuration."""
    config_dir = os.path.expanduser("~/.x402_policy")
    os.makedirs(config_dir, exist_ok=True)
    
    if wallet:
        env_file = os.path.join(config_dir, ".env")
        with open(env_file, "w") as f:
            f.write(f"WALLET_PRIVATE_KEY={wallet}\n")
        print(f"✅ Wallet configured and saved to: {env_file}")
    else:
        # Create template .env
        env_file = os.path.join(config_dir, ".env.example")
        with open(env_file, "w") as f:
            f.write("# x402 Policy Engine Configuration\n")
            f.write("WALLET_PRIVATE_KEY=0x...\n")
            f.write("DEFAULT_CHAIN=base\n")
            f.write("DAILY_BUDGET=5.0\n")
            f.write("PER_TX_LIMIT=0.10\n")
        print(f"✅ Configuration template created: {env_file}")
        print("   Edit the file and set your WALLET_PRIVATE_KEY")
    
    # Create session storage dir
    print(f"✅ Storage directory: {config_dir}")


async def main_async(args):
    """Run the appropriate command."""
    if args.command == "trust-score":
        await cmd_trust_score(args.agent_id, args.chain)
    elif args.command == "create-session":
        await cmd_create_session(args.daily_limit, args.per_tx, args.window, args.recipients)
    elif args.command == "pay":
        await cmd_pay(args.recipient, args.amount, args.description)
    elif args.command == "policy-info":
        cmd_policy_info()
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "init":
        cmd_init(args.wallet)
    else:
        print("x402-policy-cli: a command-line tool for autonomous AI agent payments")
        print("Run: x402-policy-cli --help for available commands")


def main():
    args = parse_args()
    
    if not args.command:
        print("x402-policy-cli v0.2.0")
        print("Autonomous AI agent payments via x402 + ERC-8004")
        print()
        print("Usage: x402-policy-cli <command> [options]")
        print("Commands:")
        print("  trust-score    Get ERC-8004 trust score for an agent")
        print("  create-session Create a new session key")
        print("  pay            Execute a payment")
        print("  policy-info    Show current configuration")
        print("  dashboard      Start the policy dashboard")
        print("  init           Initialize configuration")
        print()
        print("Run 'x402-policy-cli <command> --help' for more info")
        return
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()