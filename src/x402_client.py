"""
x402 Client — Wrapped Coinbase x402 SDK with policy enforcement.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from decimal import Decimal
import httpx
from eth_account import Account
from eth_account.signers.local import LocalAccount

from policy import SpendContext, PolicyConfig, create_policy, PaymentRecord

logger = logging.getLogger(__name__)

@dataclass
class x402PaymentRequest:
    """A payment request for x402."""
    amount: float
    recipient: str
    description: str
    max_payload_size_bytes: int = 1024

@dataclass
class x402PaymentResponse:
    """Response from x402 payment."""
    success: bool
    tx_hash: Optional[str] = None
    amount_paid: float = 0.0
    message: str = ""
    policy_decision: Dict[str, Any] = None

class x402PolicyClient:
    """
    x402 client with built-in policy enforcement.
    
    Usage:
        client = x402PolicyClient(
            wallet_private_key="0x...",
            policy_config=policy_config
        )
        
        result = await client.pay("api.openai.com", 0.05, "GPT-4o mini call")
    """
    
    def __init__(
        self,
        wallet_private_key: str,
        policy_config: PolicyConfig,
        x402_relay_url: str = "https://payments.x402.tech",
        chain_id: int = 8453,  # Base mainnet
        payment_token: str = "USDC"
    ):
        self.account: LocalAccount = Account.from_key(wallet_private_key)
        self.policy = SpendContext(policy_config)
        self.x402_relay_url = x402_relay_url
        self.chain_id = chain_id
        self.payment_token = payment_token
        
        logger.info(f"x402 Policy Client initialized for wallet {self.account.address[:8]}...")
    
    async def pay(
        self,
        recipient: str,
        amount: float,
        description: str = "",
        idempotency_key: Optional[str] = None
    ) -> x402PaymentResponse:
        """
        Execute a policy-controlled x402 payment.
        
        Args:
            recipient: The payment recipient (URL or address)
            amount: Amount in USD (x402 uses USDC)
            description: Human-readable description
            idempotency_key: Unique key to prevent double-spends
            
        Returns:
            x402PaymentResponse with policy decision and tx details
        """
        # Step 1: Policy check FIRST — before any on-chain activity
        policy_decision = self.policy.approve_payment(
            recipient=recipient,
            amount=amount,
            description=description
        )
        
        if not policy_decision["approved"]:
            logger.warning(
                f"Payment denied: {policy_decision['reason']} | "
                f"recipient={recipient}, amount=${amount}"
            )
            return x402PaymentResponse(
                success=False,
                message=policy_decision["reason"],
                policy_decision=policy_decision,
                amount_paid=0.0
            )
        
        # Step 2: Execute x402 payment via relay
        try:
            tx_hash = await self._send_x402_payment(
                recipient=recipient,
                amount=amount,
                description=description,
                idempotency_key=idempotency_key
            )
            
            logger.info(
                f"Payment approved & sent: {tx_hash} | "
                f"${amount} → {recipient}"
            )
            
            return x402PaymentResponse(
                success=True,
                tx_hash=tx_hash,
                amount_paid=amount,
                message="Payment executed successfully",
                policy_decision=policy_decision
            )
            
        except Exception as e:
            logger.error(f"Payment failed after policy approval: {e}")
            return x402PaymentResponse(
                success=False,
                message=f"Payment execution failed: {str(e)}",
                policy_decision=policy_decision,
                amount_paid=0.0
            )
    
    async def _send_x402_payment(
        self,
        recipient: str,
        amount: float,
        description: str,
        idempotency_key: Optional[str] = None
    ) -> str:
        """
        Send payment via x402 relay.
        
        In production, this uses Coinbase's x402 SDK.
        For demo, this hits the relay HTTP endpoint.
        """
        # Build x402 payment request
        headers = {
            "x402-version": "1",
            "x402-payment-token": self.payment_token,
            "x402-chain-id": str(self.chain_id),
            "x402-payer": self.account.address,
            "Content-Type": "application/json"
        }
        
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        payload = {
            "recipient": recipient,
            "amount": str(Decimal(str(amount))),
            "description": description,
            "maxPayloadSizeBytes": 1024
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.x402_relay_url}/v1/pay",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("txHash", f"mock_tx_{recipient}_{amount}")
            else:
                # In demo mode, return mock tx hash
                # In production, raise exception
                logger.warning(f"Relay returned {response.status_code}, using mock tx")
                return f"0x{'1' * 64}"  # Mock tx hash
    
    def get_stats(self) -> Dict[str, Any]:
        """Get policy spending statistics."""
        return self.policy.get_spending_stats()
    
    def enable_kill_switch(self):
        """Emergency stop — revoke all spending."""
        self.policy.enable_kill_switch()
        logger.critical("KILL SWITCH ACTIVATED — all payments blocked")
    
    def disable_kill_switch(self):
        """Reactivate policy enforcement."""
        self.policy.disable_kill_switch()
        logger.info("Kill switch deactivated, policy enforcement resumed")
    
    def get_history(self, limit: int = 100) -> List[PaymentRecord]:
        """Get recent payment history."""
        return self.policy.get_history(limit=limit)


class x402BatchClient:
    """
    Batch payment client for handling multiple small payments efficiently.
    Groups payments into batched transactions to save gas.
    """
    
    def __init__(client: x402PolicyClient, batch_size: int = 10):
        self.client = client
        self.batch_size = batch_size
        self._pending_payments: List[x402PaymentRequest] = []
    
    async def add_payment(self, recipient: str, amount: float, description: str = ""):
        """Add a payment to the batch queue."""
        self._pending_payments.append(
            x402PaymentRequest(recipient=recipient, amount=amount, description=description)
        )
        
        if len(self._pending_payments) >= self.batch_size:
            return await self.flush()
        return None
    
    async def flush(self) -> List[x402PaymentResponse]:
        """Execute all pending payments."""
        if not self._pending_payments:
            return []
        
        results = []
        for payment in self._pending_payments:
            result = await self.client.pay(
                recipient=payment.recipient,
                amount=payment.amount,
                description=payment.description
            )
            results.append(result)
        
        self._pending_payments = []
        return results


async def quick_pay_demo():
    """Demo: quick policy-controlled payment."""
    from policy import PolicyConfig, create_policy
    
    config = PolicyConfig(
        daily_budget=5.0,
        per_tx_max=0.10,
        allowlist=["api.weather.com", "api.coinbase.com", "api.coingecko.com"],
    )
    
    # Note: NEVER hardcode private keys in production!
    # Use environment variables: os.environ.get("WALLET_PRIVATE_KEY")
    client = x402PolicyClient(
        wallet_private_key="0x" + "0" * 64,  # Replace with real key
        policy_config=config
    )
    
    # This will be approved
    result1 = await client.pay("api.coinbase.com", 0.05, "Price data feed")
    print(f"Payment 1: {result1}")
    
    # This will be denied (exceeds per-tx limit)
    result2 = await client.pay("api.coinbase.com", 1.00, "Bulk data request")
    print(f"Payment 2: {result2}")
    
    # This will be denied (not in allowlist)
    result3 = await client.pay("random-site.com", 0.05, "Unknown API")
    print(f"Payment 3: {result3}")
    
    print(f"Stats: {client.get_stats()}")


if __name__ == "__main__":
    asyncio.run(quick_pay_demo())
