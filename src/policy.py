"""
x402 Policy Engine — Core Policy Engine
Wraps x402 payments with autonomous guardrails for AI agents.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal

class PolicyViolation(Exception):
    """Raised when a payment violates policy rules."""
    pass

class SpendingLimitExceeded(PolicyViolation):
    """Daily budget exceeded."""
    pass

class PerTransactionLimitExceeded(PolicyViolation):
    """Single transaction limit exceeded."""
    pass

class RecipientNotAllowed(PolicyViolation):
    """Recipient not in allowlist."""
    pass

class TimeWindowViolation(PolicyViolation):
    """Payment outside allowed time window."""
    pass

@dataclass
class SpendingRule:
    """A single spending rule/condition."""
    name: str
    max_amount: float
    window_seconds: int = 86400  # Default: daily

@dataclass
class TimeWindow:
    """Allowed time window for spending."""
    start_hour: int  # 0-23
    end_hour: int    # 0-23
    timezone: str = "UTC"

    def is_active(self) -> bool:
        now = datetime.utcnow()
        current_hour = now.hour
        if self.start_hour <= self.end_hour:
            return self.start_hour <= current_hour < self.end_hour
        else:  # Handles overnight windows like 22:00 - 06:00
            return current_hour >= self.start_hour or current_hour < self.end_hour

@dataclass
class PaymentRecord:
    """Record of a payment attempt."""
    timestamp: datetime
    recipient: str
    amount: float
    description: str
    approved: bool
    reason: str = ""
    tx_hash: Optional[str] = None

@dataclass
class PolicyConfig:
    """Configuration for a spending policy."""
    daily_budget: float = 10.0
    per_tx_max: float = 0.50
    allowlist: List[str] = field(default_factory=list)
    blocklist: List[str] = field(default_factory=list)
    time_windows: List[TimeWindow] = field(default_factory=list)
    erc8004_agent_id: Optional[str] = None
    kill_switch: bool = False
    max_calls_per_minute: int = 60

class SpendContext:
    """
    Manages spending policy for an AI agent.
    Thread-safe, supports concurrent payment attempts.
    """
    
    def __init__(self, config: PolicyConfig):
        self.config = config
        self._spent_today: float = 0.0
        self._day_start: datetime = datetime.utcnow()
        self._lock = threading.Lock()
        self._payment_history: List[PaymentRecord] = []
        self._recent_calls: List[float] = []  # Timestamps of recent calls
        
    def _reset_daily_if_needed(self):
        """Reset daily counter if day has changed."""
        now = datetime.utcnow()
        if now.date() > self._day_start.date():
            self._spent_today = 0.0
            self._day_start = now
            
    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows this call."""
        now = time.time()
        # Remove calls older than 1 minute
        self._recent_calls = [ts for ts in self._recent_calls if now - ts < 60]
        return len(self._recent_calls) < self.config.max_calls_per_minute
    
    def _is_recipient_allowed(self, recipient: str) -> bool:
        """Check if recipient is allowed."""
        # Blocklist check first
        for blocked in self.config.blocklist:
            if blocked in recipient:
                return False
        # Allowlist check
        if self.config.allowlist:
            for allowed in self.config.allowlist:
                if allowed in recipient or recipient in allowed:
                    return True
            return False
        return True
        
    def _is_time_allowed(self) -> bool:
        """Check if current time is in allowed windows."""
        if not self.config.time_windows:
            return True
        return any(tw.is_active() for tw in self.config.time_windows)
    
    def approve_payment(
        self,
        recipient: str,
        amount: float,
        description: str = "",
        tx_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate and approve/deny a payment request.
        
        Returns:
            Dict with:
                - approved: bool
                - reason: str
                - remaining_budget: float
                - record: PaymentRecord
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            # Kill switch check
            if self.config.kill_switch:
                record = PaymentRecord(
                    timestamp=datetime.utcnow(),
                    recipient=recipient,
                    amount=amount,
                    description=description,
                    approved=False,
                    reason="Kill switch active"
                )
                self._payment_history.append(record)
                return {
                    "approved": False,
                    "reason": "Kill switch is active",
                    "remaining_budget": self.config.daily_budget - self._spent_today,
                    "record": record
                }
            
            # Rate limit check
            if not self._check_rate_limit():
                record = PaymentRecord(
                    timestamp=datetime.utcnow(),
                    recipient=recipient,
                    amount=amount,
                    description=description,
                    approved=False,
                    reason="Rate limit exceeded"
                )
                self._payment_history.append(record)
                return {
                    "approved": False,
                    "reason": f"Rate limit: max {self.config.max_calls_per_minute} calls/min",
                    "remaining_budget": self.config.daily_budget - self._spent_today,
                    "record": record
                }
            
            # Per-transaction limit check
            if amount > self.config.per_tx_max:
                record = PaymentRecord(
                    timestamp=datetime.utcnow(),
                    recipient=recipient,
                    amount=amount,
                    description=description,
                    approved=False,
                    reason=f"Amount ${amount:.4f} exceeds per-tx max ${self.config.per_tx_max:.4f}"
                )
                self._payment_history.append(record)
                return {
                    "approved": False,
                    "reason": f"Per-transaction limit exceeded: ${amount:.4f} > ${self.config.per_tx_max:.4f}",
                    "remaining_budget": self.config.daily_budget - self._spent_today,
                    "record": record
                }
            
            # Daily budget check
            if self._spent_today + amount > self.config.daily_budget:
                record = PaymentRecord(
                    timestamp=datetime.utcnow(),
                    recipient=recipient,
                    amount=amount,
                    description=description,
                    approved=False,
                    reason=f"Would exceed daily budget: ${self._spent_today + amount:.4f} > ${self.config.daily_budget:.4f}"
                )
                self._payment_history.append(record)
                return {
                    "approved": False,
                    "reason": f"Daily budget exceeded: ${self._spent_today:.4f}/${self.config.daily_budget:.4f}",
                    "remaining_budget": self.config.daily_budget - self._spent_today,
                    "record": record
                }
            
            # Recipient check
            if not self._is_recipient_allowed(recipient):
                record = PaymentRecord(
                    timestamp=datetime.utcnow(),
                    recipient=recipient,
                    amount=amount,
                    description=description,
                    approved=False,
                    reason=f"Recipient not in allowlist: {recipient}"
                )
                self._payment_history.append(record)
                return {
                    "approved": False,
                    "reason": f"Recipient not allowed: {recipient}",
                    "remaining_budget": self.config.daily_budget - self._spent_today,
                    "record": record
                }
            
            # Time window check
            if not self._is_time_allowed():
                record = PaymentRecord(
                    timestamp=datetime.utcnow(),
                    recipient=recipient,
                    amount=amount,
                    description=description,
                    approved=False,
                    reason="Outside allowed time window"
                )
                self._payment_history.append(record)
                return {
                    "approved": False,
                    "reason": "Payment outside allowed time window",
                    "remaining_budget": self.config.daily_budget - self._spent_today,
                    "record": record
                }
            
            # APPROVED
            self._spent_today += amount
            self._recent_calls.append(time.time())
            
            record = PaymentRecord(
                timestamp=datetime.utcnow(),
                recipient=recipient,
                amount=amount,
                description=description,
                approved=True,
                reason="Approved by policy",
                tx_hash=tx_hash
            )
            self._payment_history.append(record)
            
            return {
                "approved": True,
                "reason": "Approved by x402 policy engine",
                "remaining_budget": self.config.daily_budget - self._spent_today,
                "spent_today": self._spent_today,
                "record": record
            }
    
    def get_spending_stats(self) -> Dict[str, Any]:
        """Get current spending statistics."""
        with self._lock:
            self._reset_daily_if_needed()
            today_records = [
                r for r in self._payment_history 
                if r.timestamp.date() == datetime.utcnow().date()
            ]
            approved = [r for r in today_records if r.approved]
            denied = [r for r in today_records if not r.approved]
            
            return {
                "spent_today": self._spent_today,
                "daily_budget": self.config.daily_budget,
                "remaining_budget": self.config.daily_budget - self._spent_today,
                "total_transactions": len(today_records),
                "approved_count": len(approved),
                "denied_count": len(denied),
                "kill_switch_active": self.config.kill_switch,
                "erc8004_agent_id": self.config.erc8004_agent_id
            }
    
    def enable_kill_switch(self):
        """Activate the kill switch — block all payments."""
        with self._lock:
            self.config.kill_switch = True
            
    def disable_kill_switch(self):
        """Deactivate the kill switch."""
        with self._lock:
            self.config.kill_switch = False
            
    def get_history(self, limit: int = 100) -> List[PaymentRecord]:
        """Get recent payment history."""
        return self._payment_history[-limit:]

def create_policy(
    daily_budget: float = 10.0,
    per_tx_max: float = 0.50,
    allowlist: List[str] = None,
    blocklist: List[str] = None,
    time_windows: List[TimeWindow] = None,
    erc8004_agent_id: str = None
) -> SpendContext:
    """Factory function to create a SpendContext with policy."""
    config = PolicyConfig(
        daily_budget=daily_budget,
        per_tx_max=per_tx_max,
        allowlist=allowlist or [],
        blocklist=blocklist or [],
        time_windows=time_windows or [],
        erc8004_agent_id=erc8004_agent_id
    )
    return SpendContext(config)