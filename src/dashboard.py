"""
x402 Policy Engine — FastAPI Dashboard
Hosted policy management service.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import uuid
import os

app = FastAPI(
    title="x402 Policy Engine API",
    description="Autonomous policy enforcement for AI agent payments",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (replace with PostgreSQL in production)
POLICIES = {}
PAYMENTS = []

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "x402_policy.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            recipient TEXT,
            amount REAL,
            description TEXT,
            approved BOOLEAN,
            reason TEXT,
            tx_hash TEXT,
            timestamp TEXT,
            policy_id TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id TEXT PRIMARY KEY,
            name TEXT,
            daily_budget REAL,
            per_tx_max REAL,
            allowlist TEXT,
            blocklist TEXT,
            erc8004_agent_id TEXT,
            created_at TEXT,
            active BOOLEAN
        )
    """)
    conn.commit()
    conn.close()

init_db()


# --- Pydantic Models ---

class TimeWindowModel(BaseModel):
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=0, le=23)
    timezone: str = "UTC"

class CreatePolicyRequest(BaseModel):
    name: str
    daily_budget: float = Field(default=10.0, gt=0)
    per_tx_max: float = Field(default=0.50, gt=0)
    allowlist: List[str] = Field(default_factory=list)
    blocklist: List[str] = Field(default_factory=list)
    time_windows: List[TimeWindowModel] = Field(default_factory=list)
    erc8004_agent_id: Optional[str] = None

class PaymentRequest(BaseModel):
    policy_id: str
    recipient: str
    amount: float = Field(gt=0)
    description: str = ""
    agent_id: str

class PolicyResponse(BaseModel):
    id: str
    name: str
    daily_budget: float
    per_tx_max: float
    allowlist: List[str]
    blocklist: List[str]
    erc8004_agent_id: Optional[str]
    created_at: str
    active: bool
    spent_today: float
    remaining_budget: float

class PaymentResponse(BaseModel):
    id: str
    approved: bool
    reason: str
    amount_paid: float
    tx_hash: Optional[str]
    timestamp: str

class StatsResponse(BaseModel):
    policy_id: str
    spent_today: float
    daily_budget: float
    remaining_budget: float
    total_transactions: int
    approved_count: int
    denied_count: int
    kill_switch_active: bool


# --- In-memory policy engine (simplified for demo) ---

class InMemoryPolicyEngine:
    """Simplified policy engine for the dashboard."""
    
    def __init__(self):
        self.policies = {}
    
    def create_policy(self, policy_id: str, config: dict):
        self.policies[policy_id] = {
            **config,
            "spent_today": 0.0,
            "day_start": datetime.utcnow(),
            "kill_switch": False,
            "history": []
        }
    
    def approve_payment(self, policy_id: str, recipient: str, amount: float, description: str) -> dict:
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")
        
        policy = self.policies[policy_id]
        
        # Reset daily if needed
        if datetime.utcnow().date() > policy["day_start"].date():
            policy["spent_today"] = 0.0
            policy["day_start"] = datetime.utcnow()
        
        # Kill switch
        if policy["kill_switch"]:
            record = self._record(policy_id, recipient, amount, description, False, "Kill switch active")
            return {"approved": False, "reason": "Kill switch active", "record": record}
        
        # Per-tx limit
        if amount > policy["per_tx_max"]:
            record = self._record(policy_id, recipient, amount, description, False, f"Per-tx limit: ${amount} > ${policy['per_tx_max']}")
            return {"approved": False, "reason": f"Per-transaction limit exceeded", "record": record}
        
        # Daily budget
        if policy["spent_today"] + amount > policy["daily_budget"]:
            record = self._record(policy_id, recipient, amount, description, False, f"Daily budget exceeded")
            return {"approved": False, "reason": f"Daily budget exceeded", "record": record}
        
        # Allowlist check
        if policy["allowlist"]:
            allowed = any(a in recipient for a in policy["allowlist"])
            if not allowed:
                record = self._record(policy_id, recipient, amount, description, False, f"Recipient not in allowlist")
                return {"approved": False, "reason": "Recipient not in allowlist", "record": record}
        
        # Blocklist check
        if policy["blocklist"]:
            blocked = any(b in recipient for b in policy["blocklist"])
            if blocked:
                record = self._record(policy_id, recipient, amount, description, False, f"Recipient blocked")
                return {"approved": False, "reason": "Recipient blocked", "record": record}
        
        # APPROVED
        policy["spent_today"] += amount
        tx_hash = f"0x{str(uuid.uuid4()).replace('-', '')}" + "0" * 50
        record = self._record(policy_id, recipient, amount, description, True, "Approved", tx_hash)
        return {
            "approved": True,
            "reason": "Approved by policy",
            "tx_hash": tx_hash,
            "record": record,
            "remaining_budget": policy["daily_budget"] - policy["spent_today"]
        }
    
    def _record(self, policy_id, recipient, amount, description, approved, reason, tx_hash=None):
        record = {
            "id": str(uuid.uuid4()),
            "policy_id": policy_id,
            "recipient": recipient,
            "amount": amount,
            "description": description,
            "approved": approved,
            "reason": reason,
            "tx_hash": tx_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        policy = self.policies.get(policy_id)
        if policy:
            policy["history"].append(record)
        return record
    
    def get_stats(self, policy_id: str) -> dict:
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        history = policy["history"]
        approved = [r for r in history if r["approved"]]
        denied = [r for r in history if not r["approved"]]
        
        return {
            "policy_id": policy_id,
            "spent_today": policy["spent_today"],
            "daily_budget": policy["daily_budget"],
            "remaining_budget": policy["daily_budget"] - policy["spent_today"],
            "total_transactions": len(history),
            "approved_count": len(approved),
            "denied_count": len(denied),
            "kill_switch_active": policy["kill_switch"]
        }


engine = InMemoryPolicyEngine()


# --- API Endpoints ---

@app.post("/policies", response_model=PolicyResponse)
async def create_policy(req: CreatePolicyRequest):
    """Create a new spending policy."""
    policy_id = str(uuid.uuid4())
    
    config = {
        "name": req.name,
        "daily_budget": req.daily_budget,
        "per_tx_max": req.per_tx_max,
        "allowlist": req.allowlist,
        "blocklist": req.blocklist,
        "erc8004_agent_id": req.erc8004_agent_id,
        "created_at": datetime.utcnow().isoformat(),
        "active": True
    }
    
    engine.create_policy(policy_id, config)
    
    return PolicyResponse(
        id=policy_id,
        spent_today=0.0,
        remaining_budget=req.daily_budget,
        **config
    )


@app.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str):
    """Get policy details."""
    if policy_id not in engine.policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    p = engine.policies[policy_id]
    return PolicyResponse(
        id=policy_id,
        spent_today=p["spent_today"],
        remaining_budget=p["daily_budget"] - p["spent_today"],
        **p
    )


@app.post("/payments", response_model=PaymentResponse)
async def create_payment(req: PaymentRequest):
    """Attempt a policy-controlled payment."""
    try:
        result = engine.approve_payment(
            policy_id=req.policy_id,
            recipient=req.recipient,
            amount=req.amount,
            description=req.description
        )
        
        record = result.pop("record")
        
        return PaymentResponse(
            id=record["id"],
            approved=record["approved"],
            reason=record["reason"],
            amount_paid=req.amount if record["approved"] else 0.0,
            tx_hash=record.get("tx_hash"),
            timestamp=record["timestamp"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/policies/{policy_id}/stats", response_model=StatsResponse)
async def get_stats(policy_id: str):
    """Get policy spending statistics."""
    try:
        return engine.get_stats(policy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/policies/{policy_id}/history")
async def get_history(policy_id: str, limit: int = 100):
    """Get payment history for a policy."""
    if policy_id not in engine.policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    history = engine.policies[policy_id]["history"]
    return {"history": history[-limit:]}


@app.post("/policies/{policy_id}/kill-switch")
async def toggle_kill_switch(policy_id: str, active: bool = True):
    """Toggle kill switch for a policy."""
    if policy_id not in engine.policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    engine.policies[policy_id]["kill_switch"] = active
    return {"policy_id": policy_id, "kill_switch_active": active}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# --- Run locally ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)