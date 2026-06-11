"""
x402 Agent Wallet — Session Keys for Gasless Autonomous Payments

Implements EIP-3009 (transferWithAuthorization) + EIP-4337 (account abstraction)
for gasless USDC payments. User signs once, agent transacts freely within limits.

pip install x402-policy
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_hash.auto import keccak
from eth_utils import to_checksum_address, keccak_hex

logger = logging.getLogger(__name__)


class SessionKeyError(Exception):
    """Base exception for session key errors."""
    pass


class SessionExpiredError(SessionKeyError):
    """Session key has expired."""
    pass


class SpendingLimitExceededError(SessionKeyError):
    """Session has exceeded its spending limit."""
    pass


class InvalidSignatureError(SessionKeyError):
    """Signature verification failed."""
    pass


@dataclass
class SpendLimit:
    """Spending limit configuration for a session."""
    total_usd: float          # Total spend allowed
    per_tx_usd: float         # Max per transaction
    daily_limit_usd: float    # Daily cap
    window_seconds: int      # Session validity window


@dataclass
class SessionKey:
    """
    A delegatable session key for gasless agent payments.
    
    The user signs a session authorization once. The agent then uses
    this session key to make autonomous payments without further approval.
    """
    key_id: str               # Unique session identifier
    session_address: str     # The delegatable wallet address
    delegator_address: str    # The original owner who authorized
    created_at: datetime
    expires_at: datetime
    
    # Spending limits (set at creation, enforced on every tx)
    limits: SpendLimit
    
    # Usage tracking
    spent_total: float = 0.0
    spent_today: float = 0.0
    tx_count: int = 0
    last_used: Optional[datetime] = None
    
    # Metadata
    description: str = ""
    allowed_recipients: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if session is still valid."""
        return datetime.utcnow() < self.expires_at
    
    def is_expired(self) -> bool:
        return not self.is_valid()
    
    def remaining_budget(self) -> float:
        return max(0, self.limits.total_usd - self.spent_total)
    
    def remaining_daily(self) -> float:
        return max(0, self.limits.daily_limit_usd - self.spent_today)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "session_address": self.session_address,
            "delegator_address": self.delegator_address,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_valid": self.is_valid(),
            "limits": {
                "total_usd": self.limits.total_usd,
                "per_tx_usd": self.limits.per_tx_usd,
                "daily_limit_usd": self.limits.daily_limit_usd,
                "window_seconds": self.limits.window_seconds
            },
            "spent_total": round(self.spent_total, 4),
            "spent_today": round(self.spent_today, 4),
            "remaining_budget": round(self.remaining_budget(), 4),
            "tx_count": self.tx_count,
            "description": self.description,
            "allowed_recipients": self.allowed_recipients
        }


@dataclass
class AuthorizationData:
    """
    EIP-3009 transfer authorization data.
    Signed by the delegator once to authorize a session.
    """
    from_address: str
    to_address: str
    value: int                # USDC (6 decimals)
    valid_after: int          # Unix timestamp
    valid_before: int         # Unix timestamp
    nonce: int
    chain_id: int


class SessionKeyManager:
    """
    Manages session keys for gasless agent payments.
    
    Usage:
        manager = SessionKeyManager(wallet_private_key="0x...")
        
        # User authorizes a session (one-time sign)
        session = await manager.create_session(
            daily_limit=5.0,
            per_tx_limit=0.10,
            window_hours=24,
            allowed_recipients=["api.coinbase.com", "api.openai.com"]
        )
        
        # Agent uses session for payments (no further approval needed)
        result = await manager.execute_payment(
            session=session,
            recipient="api.coinbase.com",
            amount=0.05,
            description="Price feed"
        )
    """
    
    def __init__(
        self,
        wallet_private_key: str,
        usdc_contract: str = "0x833589fCD6eDb6E08f4c7C32D4Fa71D5b97FdB2e",  # Base USDC
        chain_id: int = 8453,
        session_key_contract: str = None  # EIP-4337 entry point
    ):
        self.account: LocalAccount = Account.from_key(wallet_private_key)
        self.usdc_contract = to_checksum_address(usdc_contract)
        self.chain_id = chain_id
        self.session_key_contract = session_key_contract
        
        # Active sessions
        self._sessions: Dict[str, SessionKey] = {}
        
        logger.info(f"SessionKeyManager initialized for {self.account.address[:10]}...")
    
    async def create_session(
        self,
        daily_limit: float,
        per_tx_limit: float,
        window_hours: int = 24,
        total_limit: float = None,
        description: str = "",
        allowed_recipients: List[str] = None
    ) -> SessionKey:
        """
        Create a new session key.
        
        In production: deploys a minimal proxy contract (EIP-1167) or uses
        EIP-4337 account abstraction for gasless delegation.
        
        For MVP: simulates the session with a virtual session address.
        """
        import uuid
        
        key_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow()
        
        # Generate a virtual session address
        # In production: this would be a deployed minimal proxy contract
        session_address = self._derive_session_address(key_id)
        
        limits = SpendLimit(
            total_usd=total_limit or (daily_limit * 30),  # Default: 30 days of daily budget
            per_tx_usd=per_tx_limit,
            daily_limit_usd=daily_limit,
            window_seconds=window_hours * 3600
        )
        
        session = SessionKey(
            key_id=key_id,
            session_address=session_address,
            delegator_address=self.account.address,
            created_at=now,
            expires_at=now + timedelta(hours=window_hours),
            limits=limits,
            description=description or f"AI agent session — {window_hours}h window",
            allowed_recipients=allowed_recipients or []
        )
        
        self._sessions[key_id] = session
        
        logger.info(
            f"Session created: {key_id} | "
            f"daily=${daily_limit} | per_tx=${per_tx_limit} | "
            f"expires={session.expires_at.strftime('%H:%M')}"
        )
        
        return session
    
    async def execute_payment(
        self,
        session: SessionKey,
        recipient: str,
        amount: float,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Execute a payment using a session key.
        
        Validates: session validity, spending limits, recipient allowlist.
        Returns: payment result with tx hash.
        """
        # Validation 1: Session is valid
        if session.is_expired():
            raise SessionExpiredError(
                f"Session {session.key_id} expired at {session.expires_at}"
            )
        
        # Validation 2: Per-tx limit
        if amount > session.limits.per_tx_usd:
            raise SpendingLimitExceededError(
                f"Amount ${amount:.4f} exceeds per-tx limit ${session.limits.per_tx_usd:.4f}"
            )
        
        # Validation 3: Total budget
        if session.spent_total + amount > session.limits.total_usd:
            raise SpendingLimitExceededError(
                f"Would exceed total budget: ${session.spent_total + amount:.4f} > ${session.limits.total_usd:.4f}"
            )
        
        # Validation 4: Daily limit
        if session.spent_today + amount > session.limits.daily_limit_usd:
            raise SpendingLimitExceededError(
                f"Would exceed daily limit: ${session.spent_today + amount:.4f} > ${session.limits.daily_limit_usd:.4f}"
            )
        
        # Validation 5: Recipient allowlist
        if session.allowed_recipients:
            allowed = any(r in recipient for r in session.allowed_recipients)
            if not allowed:
                raise SessionKeyError(
                    f"Recipient {recipient} not in session allowlist"
                )
        
        # Execute payment
        # In production: call EIP-3009 transferWithAuthorization or EIP-4337 userOp
        tx_hash = await self._execute_gasless_transfer(
            session=session,
            recipient=recipient,
            amount_usdc=int(amount * 1_000_000)  # USDC has 6 decimals
        )
        
        # Update session tracking
        session.spent_total += amount
        session.spent_today += amount
        session.tx_count += 1
        session.last_used = datetime.utcnow()
        
        logger.info(
            f"Session payment: {session.key_id} → ${amount:.4f} | "
            f"recipient={recipient[:30]} | tx={tx_hash[:16]}..."
        )
        
        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount_usd": amount,
            "recipient": recipient,
            "session_id": session.key_id,
            "session_address": session.session_address,
            "spent_total": session.spent_total,
            "remaining_budget": session.remaining_budget(),
            "tx_count": session.tx_count
        }
    
    async def _execute_gasless_transfer(
        self,
        session: SessionKey,
        recipient: str,
        amount_usdc: int
    ) -> str:
        """
        Execute a gasless USDC transfer.
        
        EIP-3009 flow:
        1. Build transferWithAuthorization payload
        2. Sign with delegator key (or session key if using 4337)
        3. Submit to relayer (who pays gas, takes small fee)
        
        For MVP: returns mock tx hash after simulating the flow.
        """
        # Simulate gasless transfer
        # In production:
        #   1. Build EIP-3009 authorization
        #   2. Sign with session key (EIP-4337) or delegator (EIP-3009)
        #   3. Send to relayer / bundler
        
        import hashlib
        now = int(time.time())
        
        # Mock tx hash
        payload = f"{session.session_address}{recipient}{amount_usdc}{now}".encode()
        tx_hash = "0x" + hashlib.sha256(payload).hexdigest()
        
        logger.debug(f"Gasless transfer: {amount_usdc} USDC → {recipient[:20]}")
        
        return tx_hash
    
    def _derive_session_address(self, key_id: str) -> str:
        """Derive a deterministic session address from key ID."""
        # In production: this would be a CREATE2 address from a factory contract
        import hashlib
        raw = hashlib.sha256(f"{self.account.address}{key_id}".encode()).digest()
        return "0x" + raw.hex()[:40].rjust(40, "0")
    
    def get_session(self, key_id: str) -> Optional[SessionKey]:
        """Get an active session by ID."""
        return self._sessions.get(key_id)
    
    def list_sessions(self, include_expired: bool = False) -> List[SessionKey]:
        """List all sessions."""
        sessions = list(self._sessions.values())
        if not include_expired:
            sessions = [s for s in sessions if s.is_valid()]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)
    
    def revoke_session(self, key_id: str) -> bool:
        """Revoke a session immediately."""
        if key_id in self._sessions:
            self._sessions[key_id].expires_at = datetime.utcnow()
            logger.info(f"Session revoked: {key_id}")
            return True
        return False
    
    def get_total_spent(self) -> float:
        """Get total spent across all sessions."""
        return sum(s.spent_total for s in self._sessions.values())


class RelayerService:
    """
    Gasless relayer service for sponsoring agent transactions.
    
    Charges a small fee (0.1%) for paying gas on behalf of agents.
    This is how facilitators earn from x402 volume.
    
    Usage:
        relayer = RelayerService(
            relayer_wallet="0x...",
            fee_bps=10  # 0.1%
        )
        
        # Relayer receives signed userOp and submits to EntryPoint
        tx_hash = await relayer.relay(user_op, fee_token="USDC")
    """
    
    def __init__(
        self,
        relayer_private_key: str,
        entry_point: str = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789",  # EIP-4337 EntryPoint
        fee_bps: int = 10,  # 0.1%
        chain_id: int = 8453
    ):
        self.relayer_account = Account.from_key(relayer_private_key)
        self.entry_point = to_checksum_address(entry_point)
        self.fee_bps = fee_bps
        self.chain_id = chain_id
        
        # Track relayed transactions
        self._relayed: List[Dict[str, Any]] = []
        
        logger.info(f"Relayer initialized: {self.relayer_account.address[:10]}...")
    
    def calculate_fee(self, amount_usdc: int) -> int:
        """Calculate relayer fee in USDC (6 decimals)."""
        return int(amount_usdc * self.fee_bps / 10000)
    
    async def relay(
        self,
        user_op: Dict[str, Any],
        payer: str
    ) -> Dict[str, Any]:
        """
        Relay a user operation (EIP-4337) by paying gas and taking a fee.
        
        In production: submits userOp to EntryPoint, extracts fee from user balance.
        For MVP: simulates the flow.
        """
        call_data = user_op.get("callData", "0x")
        amount_usdc = user_op.get("callDataAmount", 0)
        
        fee = self.calculate_fee(amount_usdc)
        
        # Simulate relay
        # In production: eth_sendUserOperation to EntryPoint
        import hashlib, time
        tx_hash = "0x" + hashlib.sha256(f"{call_data}{time.time()}".encode()).hexdigest()
        
        result = {
            "success": True,
            "tx_hash": tx_hash,
            "fee_charged_usdc": fee / 1_000_000,
            "fee_bps": self.fee_bps,
            "relayer": self.relayer_account.address,
            "payer": payer
        }
        
        self._relayed.append(result)
        
        logger.info(
            f"Relayed: tx={tx_hash[:16]}... | "
            f"fee=${fee/1_000_000:.4f} | from={payer[:12]}..."
        )
        
        return result
    
    def get_relayer_stats(self) -> Dict[str, Any]:
        """Get relayer statistics."""
        total_volume = sum(r.get("fee_charged_usdc", 0) for r in self._relayed)
        return {
            "total_relayed": len(self._relayed),
            "total_volume_usd": round(sum(
                r.get("callDataAmount", 0) / 1_000_000 
                for r in self._relayed
            ), 2),
            "total_fees_usd": round(total_volume, 4),
            "relayer_address": self.relayer_account.address,
            "fee_bps": self.fee_bps
        }


async def demo():
    """Demo session key flow."""
    print("=" * 60)
    print("x402 AGENT WALLET — Session Keys for Gasless Payments")
    print("=" * 60)
    
    # Initialize manager (use mock key for demo)
    manager = SessionKeyManager(
        wallet_private_key="0x" + "0" * 64,  # Replace with real key
        chain_id=8453
    )
    
    # Create a session
    print("\n📝 Creating session...")
    session = await manager.create_session(
        daily_limit=5.0,
        per_tx_limit=0.10,
        window_hours=24,
        allowed_recipients=["api.coinbase.com", "api.coingecko.com", "api.openai.com"]
    )
    print(f"   Session ID: {session.key_id}")
    print(f"   Address: {session.session_address}")
    print(f"   Expires: {session.expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   Daily limit: ${session.limits.daily_limit_usd}")
    print(f"   Per-tx limit: ${session.limits.per_tx_usd}")
    
    # Execute payments (no human approval needed)
    print("\n💳 Executing payments via session key...")
    
    payments = [
        ("api.coinbase.com/v1/prices", 0.02, "ETH price feed"),
        ("api.coingecko.com/simple", 0.03, "BTC price feed"),
        ("api.coinbase.com/v2/ohlc", 0.05, "Market data"),
    ]
    
    for recipient, amount, desc in payments:
        try:
            result = await manager.execute_payment(
                session=session,
                recipient=recipient,
                amount=amount,
                description=desc
            )
            print(f"   ✅ {recipient[:30]}... ${amount} — tx={result['tx_hash'][:16]}...")
        except Exception as e:
            print(f"   ❌ {recipient[:30]}... — {e}")
    
    # Try exceeding per-tx limit
    print("\n⚠️  Testing limit enforcement...")
    try:
        await manager.execute_payment(
            session=session,
            recipient="api.coinbase.com",
            amount=1.00,
            description="Large transaction"
        )
    except SpendingLimitExceededError as e:
        print(f"   ✅ Blocked: {e}")
    
    # Session stats
    print("\n📊 Session Stats:")
    print(f"   Total spent: ${session.spent_total:.4f}")
    print(f"   Today: ${session.spent_today:.4f}")
    print(f"   Remaining: ${session.remaining_budget():.4f}")
    print(f"   Transactions: {session.tx_count}")
    
    # List all sessions
    print("\n📋 All Sessions:")
    for s in manager.list_sessions():
        status = "🟢 Active" if s.is_valid() else "🔴 Expired"
        print(f"   {s.key_id} | {status} | ${s.spent_total:.2f} spent | {s.tx_count} txns")
    
    print("\n" + "=" * 60)
    print("✅ Session key flow complete!")
    print("   User signed once. Agent paid 3 times. Zero approvals needed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())