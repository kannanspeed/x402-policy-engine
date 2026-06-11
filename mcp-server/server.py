"""
x402 Policy Engine — MCP Server (Model Context Protocol)

Exposes x402 Policy Engine tools as MCP endpoints for AI agents.
Works with OpenClaw, Claude Code, Cursor, and any MCP-compatible client.

Usage:
    python mcp_server.py

Then add to your MCP client config:
    {
      "mcpServers": {
        "x402-policy": {
          "command": "python",
          "args": ["path/to/mcp_server.py"]
        }
      }
    }
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from policy import PolicyConfig, create_policy, TimeWindow
from tap_resolver import TAPResolver, TrustLevel
from session_keys import SessionKeyManager, SessionKey
from erc8004 import ERC8004Reader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# MCP Protocol — JSON-RPC 2.0 over stdio
# ============================================

@dataclass
class MCPRequest:
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str = ""
    params: Dict[str, Any] = None

@dataclass
class MCPResponse:
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Any = None
    error: Optional[Dict[str, Any]] = None


def send_response(response: MCPResponse):
    """Send JSON-RPC response to stdout."""
    output = json.dumps(asdict(response), default=str)
    print(output, flush=True)


def send_notification(method: str, params: Dict[str, Any] = None):
    """Send JSON-RPC notification (no id)."""
    msg = {"jsonrpc": "2.0", "method": method}
    if params:
        msg["params"] = params
    print(json.dumps(msg), flush=True)


# ============================================
# MCP Tool Registry
# ============================================

class ToolRegistry:
    """Registry of available MCP tools."""
    
    def __init__(self):
        self.manager: Optional[SessionKeyManager] = None
        self.resolver = TAPResolver()
        self.policies: Dict[str, Any] = {}
        self._sessions: Dict[str, SessionKey] = {}
        
    def init_manager(self, wallet_key: str):
        """Initialize the session key manager."""
        if not self.manager:
            self.manager = SessionKeyManager(
                wallet_private_key=wallet_key,
                chain_id=8453
            )
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Return all available tools."""
        return [
            # === Trust & Reputation ===
            {
                "name": "tap_resolve",
                "description": "Resolve cross-chain ERC-8004 agent identity + trust score",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "Agent ID (bytes32 hex)"},
                        "chain": {"type": "string", "description": "Primary chain (default: base)", "default": "base"}
                    },
                    "required": ["agent_id"]
                }
            },
            {
                "name": "tap_verify",
                "description": "Full TAP verification for x402 payment decisions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "Agent ID"},
                        "chain": {"type": "string", "default": "base"}
                    },
                    "required": ["agent_id"]
                }
            },
            {
                "name": "tap_score",
                "description": "Get trust score (0-5) with breakdown for an agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "chain": {"type": "string", "default": "base"}
                    },
                    "required": ["agent_id"]
                }
            },
            
            # === Session Keys ===
            {
                "name": "session_create",
                "description": "Create a session key — user signs once, agent pays freely",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "daily_limit": {"type": "number", "description": "Daily budget in USD", "default": 5.0},
                        "per_tx_limit": {"type": "number", "description": "Max per transaction in USD", "default": 0.10},
                        "window_hours": {"type": "number", "description": "Session validity in hours", "default": 24},
                        "recipients": {"type": "array", "items": {"type": "string"}, "description": "Allowed recipient domains"}
                    }
                }
            },
            {
                "name": "session_pay",
                "description": "Execute a payment using an active session",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session key ID"},
                        "recipient": {"type": "string", "description": "Payment recipient URL"},
                        "amount": {"type": "number", "description": "Amount in USD"},
                        "description": {"type": "string", "description": "Payment description", "default": ""}
                    },
                    "required": ["session_id", "recipient", "amount"]
                }
            },
            {
                "name": "session_status",
                "description": "Get session status and remaining budget",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"}
                    },
                    "required": ["session_id"]
                }
            },
            {
                "name": "session_revoke",
                "description": "Revoke a session key immediately (kill switch)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"}
                    },
                    "required": ["session_id"]
                }
            },
            {
                "name": "session_list",
                "description": "List all active sessions"
            },
            
            # === Policy Engine ===
            {
                "name": "policy_approve",
                "description": "Check if a payment is approved under policy rules",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string"},
                        "recipient": {"type": "string"},
                        "amount": {"type": "number"},
                        "description": {"type": "string", "default": ""}
                    },
                    "required": ["recipient", "amount"]
                }
            },
            {
                "name": "policy_create",
                "description": "Create a new spending policy",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string"},
                        "daily_budget": {"type": "number", "default": 5.0},
                        "per_tx_max": {"type": "number", "default": 0.10},
                        "allowlist": {"type": "array", "items": {"type": "string"}, "default": []},
                        "blocklist": {"type": "array", "items": {"type": "string"}, "default": []}
                    }
                }
            },
            {
                "name": "policy_stats",
                "description": "Get policy spending statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string"}
                    },
                    "required": ["policy_id"]
                }
            },
            
            # === x402 Payments ===
            {
                "name": "x402_pay",
                "description": "Execute an x402 payment with policy enforcement",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string"},
                        "amount": {"type": "number"},
                        "description": {"type": "string", "default": ""},
                        "use_trust_limits": {"type": "boolean", "description": "Adjust limits based on ERC-8004 trust score", "default": True}
                    },
                    "required": ["recipient", "amount"]
                }
            },
            
            # === Info ===
            {
                "name": "x402_status",
                "description": "Get x402 Policy Engine status and capabilities",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]


registry = ToolRegistry()


# ============================================
# Tool Handlers
# ============================================

async def handle_tap_resolve(agent_id: str, chain: str = "base") -> Dict[str, Any]:
    """Resolve cross-chain TAP identity."""
    chain_id = {"ethereum": 1, "base": 8453, "arbitrum": 42161, "optimism": 10, "bsc": 56}.get(chain, 8453)
    identity = await registry.resolver.resolve(agent_id, chain_id)
    
    if not identity:
        return {"success": False, "error": "Agent not found"}
    
    return {
        "success": True,
        "canonical_agent_id": identity.canonical_agent_id,
        "primary_chain": identity.primary_chain_name,
        "total_chains": identity.total_chains,
        "total_reputation_score": round(identity.total_reputation_score, 2),
        "weighted_reputation": round(identity.weighted_reputation, 2),
        "trust_level": identity.trust_level.value,
        "consistency_score": round(identity.consistency_score, 2),
        "registrations": [
            {"chain": r.chain_name, "score": round(r.reputation_score, 1), "tasks": r.completed_tasks}
            for r in identity.registrations
        ]
    }


async def handle_tap_verify(agent_id: str, chain: str = "base") -> Dict[str, Any]:
    """Full TAP verification for payment decisions."""
    chain_id = {"ethereum": 1, "base": 8453, "arbitrum": 42161, "optimism": 10, "bsc": 56}.get(chain, 8453)
    result = await registry.resolver.verify(agent_id, chain_id)
    
    return {
        "success": True,
        "agent_id": result["agent_id"],
        "chain_id": result["chain_id"],
        "payment_approved": result["payment_approved"],
        "payment_reason": result["payment_reason"],
        "elevated_limits": result["elevated_limits"],
        "recommendation": result["recommendation"],
        "verified_at": result["verified_at"]
    }


async def handle_tap_score(agent_id: str, chain: str = "base") -> Dict[str, Any]:
    """Get trust score with breakdown."""
    chain_id = {"ethereum": 1, "base": 8453, "arbitrum": 42161, "optimism": 10, "bsc": 56}.get(chain, 8453)
    score = await registry.resolver.score(agent_id, chain_id)
    
    if not score:
        return {"success": False, "error": "Agent not found"}
    
    return {
        "success": True,
        "agent_id": agent_id,
        "overall_score": score.overall_score,
        "trust_level": score.trust_level.value,
        "recommendation": score.recommendation,
        "chain_breakdown": score.chain_breakdown,
        "activity_score": score.activity_score,
        "consistency_score": score.consistency_score,
        "age_score": score.age_score,
        "blockers": score.blockers
    }


async def handle_session_create(
    daily_limit: float = 5.0,
    per_tx_limit: float = 0.10,
    window_hours: int = 24,
    recipients: List[str] = None
) -> Dict[str, Any]:
    """Create a new session key."""
    wallet_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not wallet_key:
        return {"success": False, "error": "Set WALLET_PRIVATE_KEY env var"}
    
    registry.init_manager(wallet_key)
    
    session = await registry.manager.create_session(
        daily_limit=daily_limit,
        per_tx_limit=per_tx_limit,
        window_hours=window_hours,
        allowed_recipients=recipients or []
    )
    
    registry._sessions[session.key_id] = session
    
    return {
        "success": True,
        "session_id": session.key_id,
        "session_address": session.session_address,
        "daily_limit": session.limits.daily_limit_usd,
        "per_tx_limit": session.limits.per_tx_usd,
        "expires_at": session.expires_at.isoformat(),
        "remaining_budget": session.remaining_budget()
    }


async def handle_session_pay(
    session_id: str,
    recipient: str,
    amount: float,
    description: str = ""
) -> Dict[str, Any]:
    """Execute a payment using a session."""
    wallet_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not wallet_key:
        return {"success": False, "error": "Set WALLET_PRIVATE_KEY env var"}
    
    registry.init_manager(wallet_key)
    
    session = registry.manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found or expired"}
    
    try:
        result = await registry.manager.execute_payment(
            session=session,
            recipient=recipient,
            amount=amount,
            description=description
        )
        return {
            "success": True,
            "tx_hash": result["tx_hash"],
            "amount_usd": result["amount_usd"],
            "recipient": result["recipient"],
            "spent_total": round(result["spent_total"], 4),
            "remaining_budget": round(result["remaining_budget"], 4),
            "tx_count": result["tx_count"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_session_status(session_id: str) -> Dict[str, Any]:
    """Get session status."""
    session = registry._sessions.get(session_id)
    if not session:
        return {"success": False, "error": "Session not found"}
    
    return {
        "success": True,
        "session_id": session.key_id,
        "is_valid": session.is_valid(),
        "expires_at": session.expires_at.isoformat(),
        "spent_total": round(session.spent_total, 4),
        "spent_today": round(session.spent_today, 4),
        "remaining_budget": round(session.remaining_budget(), 4),
        "remaining_daily": round(session.remaining_daily(), 4),
        "tx_count": session.tx_count
    }


async def handle_session_revoke(session_id: str) -> Dict[str, Any]:
    """Revoke a session."""
    if session_id in registry._sessions:
        registry._sessions[session_id].expires_at = datetime.utcnow()
        return {"success": True, "session_id": session_id, "revoked": True}
    return {"success": False, "error": "Session not found"}


async def handle_session_list() -> Dict[str, Any]:
    """List all sessions."""
    sessions = []
    for s in registry._sessions.values():
        sessions.append({
            "session_id": s.key_id,
            "is_valid": s.is_valid(),
            "spent_total": round(s.spent_total, 4),
            "tx_count": s.tx_count,
            "expires_at": s.expires_at.isoformat()
        })
    return {"success": True, "sessions": sessions}


async def handle_policy_create(
    policy_id: str,
    daily_budget: float = 5.0,
    per_tx_max: float = 0.10,
    allowlist: List[str] = None,
    blocklist: List[str] = None
) -> Dict[str, Any]:
    """Create a policy."""
    policy = create_policy(
        daily_budget=daily_budget,
        per_tx_max=per_tx_max,
        allowlist=allowlist or [],
        blocklist=blocklist or []
    )
    registry.policies[policy_id] = policy
    
    return {
        "success": True,
        "policy_id": policy_id,
        "daily_budget": daily_budget,
        "per_tx_max": per_tx_max,
        "allowlist": allowlist or [],
        "remaining_budget": daily_budget
    }


async def handle_policy_approve(
    policy_id: str = "default",
    recipient: str = "",
    amount: float = 0.0,
    description: str = ""
) -> Dict[str, Any]:
    """Check if payment is approved under policy."""
    policy = registry.policies.get(policy_id)
    if not policy:
        # Use default policy
        policy = create_policy(daily_budget=5.0, per_tx_max=0.10)
    
    result = policy.approve_payment(
        recipient=recipient,
        amount=amount,
        description=description
    )
    
    return {
        "success": True,
        "approved": result["approved"],
        "reason": result["reason"],
        "remaining_budget": round(result.get("remaining_budget", 0), 4),
        "record": {
            "recipient": recipient,
            "amount": amount,
            "approved": result["approved"],
            "timestamp": datetime.utcnow().isoformat()
        }
    }


async def handle_policy_stats(policy_id: str) -> Dict[str, Any]:
    """Get policy stats."""
    policy = registry.policies.get(policy_id)
    if not policy:
        return {"success": False, "error": "Policy not found"}
    
    stats = policy.get_spending_stats()
    return {"success": True, **stats}


async def handle_x402_pay(
    recipient: str,
    amount: float,
    description: str = "",
    use_trust_limits: bool = True
) -> Dict[str, Any]:
    """Execute x402 payment with optional trust-based limits."""
    wallet_key = os.environ.get("WALLET_PRIVATE_KEY")
    if not wallet_key:
        return {"success": False, "error": "Set WALLET_PRIVATE_KEY env var"}
    
    # Get agent ID from env or use default
    agent_id = os.environ.get("ERC8004_AGENT_ID", "0x" + "deadbeef" * 8)
    
    # Check trust score if enabled
    elevated = False
    if use_trust_limits:
        trust_result = await registry.resolver.verify(agent_id, 8453)
        elevated = trust_result.get("elevated_limits", False)
    
    # Determine limits based on trust
    daily_limit = 10.0 if elevated else 5.0
    per_tx_limit = 0.50 if elevated else 0.10
    
    # Create a one-time policy for this payment
    policy = create_policy(
        daily_budget=daily_limit,
        per_tx_max=per_tx_limit,
        allowlist=[recipient]
    )
    
    result = policy.approve_payment(
        recipient=recipient,
        amount=amount,
        description=description
    )
    
    return {
        "success": result["approved"],
        "approved": result["approved"],
        "reason": result["reason"],
        "trust_elevated": elevated,
        "daily_limit": daily_limit,
        "per_tx_limit": per_tx_limit,
        "remaining_budget": round(result.get("remaining_budget", 0), 4)
    }


def handle_x402_status() -> Dict[str, Any]:
    """Get engine status."""
    wallet_set = bool(os.environ.get("WALLET_PRIVATE_KEY"))
    agent_id = os.environ.get("ERC8004_AGENT_ID", "")
    
    return {
        "success": True,
        "version": "0.2.0",
        "status": "ready",
        "wallet_configured": wallet_set,
        "erc8004_agent_id": agent_id or "not set",
        "active_sessions": len(registry._sessions),
        "active_policies": len(registry.policies),
        "supported_chains": ["ethereum", "base", "arbitrum", "optimism", "bsc", "polygon", "avalanche"],
        "tools_available": len(registry.list_tools())
    }


# ============================================
# MCP Request Handler
# ============================================

TOOL_HANDLERS = {
    "tap_resolve": lambda p: handle_tap_resolve(p.get("agent_id"), p.get("chain", "base")),
    "tap_verify": lambda p: handle_tap_verify(p.get("agent_id"), p.get("chain", "base")),
    "tap_score": lambda p: handle_tap_score(p.get("agent_id"), p.get("chain", "base")),
    "session_create": lambda p: handle_session_create(
        p.get("daily_limit", 5.0),
        p.get("per_tx_limit", 0.10),
        p.get("window_hours", 24),
        p.get("recipients")
    ),
    "session_pay": lambda p: handle_session_pay(
        p.get("session_id"),
        p.get("recipient"),
        p.get("amount"),
        p.get("description", "")
    ),
    "session_status": lambda p: handle_session_status(p.get("session_id")),
    "session_revoke": lambda p: handle_session_revoke(p.get("session_id")),
    "session_list": lambda p: handle_session_list(),
    "policy_create": lambda p: handle_policy_create(
        p.get("policy_id", "default"),
        p.get("daily_budget", 5.0),
        p.get("per_tx_max", 0.10),
        p.get("allowlist", []),
        p.get("blocklist", [])
    ),
    "policy_approve": lambda p: handle_policy_approve(
        p.get("policy_id", "default"),
        p.get("recipient", ""),
        p.get("amount", 0.0),
        p.get("description", "")
    ),
    "policy_stats": lambda p: handle_policy_stats(p.get("policy_id", "default")),
    "x402_pay": lambda p: handle_x402_pay(
        p.get("recipient"),
        p.get("amount"),
        p.get("description", ""),
        p.get("use_trust_limits", True)
    ),
    "x402_status": lambda p: handle_x402_status(),
}


async def process_request(req: MCPRequest) -> MCPResponse:
    """Process an MCP request."""
    method = req.method
    params = req.params or {}
    req_id = req.id
    
    # Handle MCP protocol methods
    if method == "initialize":
        return MCPResponse(
            id=req_id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "x402-policy-engine", "version": "0.2.0"}
            }
        )
    
    elif method == "tools/list":
        return MCPResponse(id=req_id, result={"tools": registry.list_tools()})
    
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name not in TOOL_HANDLERS:
            return MCPResponse(
                id=req_id,
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"}
            )
        
        try:
            result = await TOOL_HANDLERS[tool_name](tool_args)
            return MCPResponse(
                id=req_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str)
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return MCPResponse(
                id=req_id,
                error={"code": -32603, "message": str(e)}
            )
    
    elif method == "resources/list":
        return MCPResponse(id=req_id, result={"resources": []})
    
    elif method == "ping":
        return MCPResponse(id=req_id, result={"status": "ok"})
    
    else:
        return MCPResponse(
            id=req_id,
            error={"code": -32601, "message": f"Unknown method: {method}"}
        )


# ============================================
# Main Loop — JSON-RPC over stdio
# ============================================

async def main():
    """Run the MCP server."""
    logger.info("x402 Policy Engine MCP Server starting...")
    logger.info(f"Version: 0.2.0")
    logger.info(f"Tools: {len(registry.list_tools())}")
    
    # Send initial notification
    send_notification("initialized", {"success": True})
    
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            req_data = json.loads(line)
            req = MCPRequest(
                jsonrpc=req_data.get("jsonrpc", "2.0"),
                id=req_data.get("id"),
                method=req_data.get("method", ""),
                params=req_data.get("params")
            )
            
            response = await process_request(req)
            send_response(response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            send_response(MCPResponse(
                id=None,
                error={"code": -32700, "message": "Parse error"}
            ))
        except Exception as e:
            logger.error(f"Error: {e}")
            send_response(MCPResponse(
                id=None,
                error={"code": -32603, "message": str(e)}
            ))


if __name__ == "__main__":
    asyncio.run(main())