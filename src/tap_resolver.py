"""
ERC-8004 Multi-Chain Aggregator — TAP Implementation
Resolves cross-chain agent identity and aggregates reputation scores.
pip install x402-policy
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

# Supported chains for ERC-8004 aggregation
SUPPORTED_CHAINS = {
    1: {"name": "ethereum", "rpc": "https://eth.llamarpc.com"},
    8453: {"name": "base", "rpc": "https://mainnet.base.org"},
    42161: {"name": "arbitrum", "rpc": "https://arb1.arbitrum.io/rpc"},
    10: {"name": "optimism", "rpc": "https://mainnet.optimism.io"},
    56: {"name": "bsc", "rpc": "https://bsc.publicnode.com"},
    137: {"name": "polygon", "rpc": "https://polygon-rpc.com"},
    43114: {"name": "avalanche", "rpc": "https://api.avax.network/ext/bc/C/rpc"},
    1284: {"name": "moonbeam", "rpc": "https://rpc.api.moonbeam.network"},
    1088: {"name": "metis", "rpc": "https://andromeda.metis.io/?owner=1088"},
}

# Chain-specific registry addresses (ERC-8004 IdentityRegistry per chain)
# Note: These are placeholders — verify before production use
REGISTRY_ADDRESSES = {
    1: "0x00000000000000000000000000000000008004",     # Ethereum
    8453: "0x00000000000000000000000000000000008004",   # Base
    42161: "0x00000000000000000000000000000000008004",  # Arbitrum
    10: "0x00000000000000000000000000000000008004",     # Optimism
    56: "0x00000000000000000000000000000000008004",     # BSC
    137: "0x00000000000000000000000000000000008004",    # Polygon
}

# Minimal ABI for reading agent info and reputation
REGISTRY_ABI = [
    {
        "name": "resolve",
        "inputs": [{"name": "agentId", "type": "bytes32"}],
        "outputs": [
            {"name": "identity", "type": "tuple(address owner, string name, string metadataURI, bool registered, uint256 chainId)"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "name": "getReputation",
        "inputs": [{"name": "agentId", "type": "bytes32"}],
        "outputs": [
            {"name": "score", "type": "uint256"},
            {"name": "totalRatings", "type": "uint256"},
            {"name": "completedTasks", "type": "uint256"},
            {"name": "lastUpdated", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "name": "getAgentRegistrations",
        "inputs": [{"name": "agentId", "type": "bytes32"}],
        "outputs": [
            {"name": "registrations", "type": "tuple(uint256 chainId, bytes32 crossChainId, uint256 registeredAt)[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class TrustLevel(Enum):
    """Trust classification for aggregated reputation."""
    FLAGGED = "flagged"      # 0-1.0 score, suspicious
    NEW = "new"             # 1.0-2.5, unproven
    VERIFIED = "verified"   # 2.5-3.5, baseline trusted
    TRUSTED = "trusted"     # 3.5-4.5, highly trusted
    ELITE = "elite"         # 4.5-5.0, top tier


@dataclass
class ChainRegistration:
    """Agent registration on a single chain."""
    chain_id: int
    chain_name: str
    agent_id_on_chain: str  # bytes32 as hex
    owner: str
    name: str
    metadata_uri: str
    registered_at: Optional[datetime] = None
    reputation_score: float = 0.0
    total_ratings: int = 0
    completed_tasks: int = 0


@dataclass
class AggregatedIdentity:
    """
    Cross-chain aggregated identity for an ERC-8004 agent.
    The TAP (Trustless Agent Plus) resolution result.
    """
    # Canonical identifier (primary chain)
    canonical_agent_id: str
    primary_chain: int
    primary_chain_name: str
    
    # Cross-chain registrations
    registrations: List[ChainRegistration]
    
    # Aggregated metrics
    total_chains: int
    total_reputation_score: float
    weighted_reputation: float  # Weighted by activity
    trust_level: TrustLevel
    
    # Metadata
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    consistency_score: float = 0.0  # How consistent is owner across chains
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_agent_id": self.canonical_agent_id,
            "primary_chain": self.primary_chain,
            "primary_chain_name": self.primary_chain_name,
            "total_chains": self.total_chains,
            "total_reputation_score": round(self.total_reputation_score, 2),
            "weighted_reputation": round(self.weighted_reputation, 2),
            "trust_level": self.trust_level.value,
            "registrations": [
                {
                    "chain": r.chain_name,
                    "chain_id": r.chain_id,
                    "agent_id": r.agent_id_on_chain,
                    "owner": r.owner,
                    "name": r.name,
                    "reputation_score": round(r.reputation_score, 2),
                    "total_ratings": r.total_ratings,
                    "completed_tasks": r.completed_tasks
                }
                for r in self.registrations
            ],
            "consistency_score": round(self.consistency_score, 2),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


@dataclass
class TrustScore:
    """Human-readable trust score with breakdown."""
    agent_id: str
    overall_score: float        # 0.0 - 5.0
    trust_level: TrustLevel
    chain_breakdown: Dict[str, float]
    activity_score: float       # Based on task completion
    consistency_score: float   # Owner consistency across chains
    age_score: float           # Older = more reliable
    recommendation: str        # "APPROVE", "REVIEW", "REJECT"
    blockers: List[str]        # Why score is low, if any


class ERC8004Aggregator:
    """
    Cross-chain ERC-8004 identity and reputation aggregator.
    
    Resolves agent identity across chains and computes unified trust score.
    
    Usage:
        aggregator = ERC8004Aggregator()
        
        # Resolve cross-chain identity
        identity = await aggregator.resolve("0xAgentId...", chain_id=8453)
        
        # Get trust score
        trust = await aggregator.get_trust_score("0xAgentId...", chain_id=8453)
        
        # Quick approval check
        approved = await aggregator.is_trusted_for_payment(
            "0xAgentId...", 
            min_score=3.5, 
            min_tasks=10
        )
    """
    
    def __init__(
        self,
        rpc_urls: Dict[int, str] = None,
        cache_ttl_seconds: int = 300  # 5 min cache
    ):
        self.rpc_urls = rpc_urls or SUPPORTED_CHAINS
        self.cache: Dict[str, Tuple[Any, float]] = {}  # agent_id -> (result, timestamp)
        self.cache_ttl = cache_ttl_seconds
        self._web3_clients = {}
        
    def _get_web3(self, chain_id: int):
        """Lazy-load web3 client per chain."""
        if chain_id not in self._web3_clients:
            try:
                from web3 import Web3
                rpc_url = self.rpc_urls.get(chain_id, {}).get("rpc")
                if rpc_url:
                    self._web3_clients[chain_id] = Web3(Web3.HTTPProvider(rpc_url))
            except ImportError:
                logger.warning("web3.py not installed. Run: pip install web3")
                return None
        return self._web3_clients.get(chain_id)
    
    def _is_cached(self, key: str) -> Optional[Any]:
        """Return cached result if fresh."""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.utcnow().timestamp() - timestamp < self.cache_ttl:
                return result
        return None
    
    def _set_cache(self, key: str, result: Any):
        """Cache a result."""
        self.cache[key] = (result, datetime.utcnow().timestamp())
    
    async def _fetch_chain_data(
        self,
        agent_id: str,
        chain_id: int
    ) -> Optional[ChainRegistration]:
        """
        Fetch agent registration + reputation from a single chain.
        Returns None if agent not registered on that chain.
        """
        cache_key = f"{agent_id}:{chain_id}"
        cached = self._is_cached(cache_key)
        if cached:
            return cached
        
        chain_info = self.rpc_urls.get(chain_id, {})
        chain_name = chain_info.get("name", f"chain_{chain_id}")
        
        # In production: make actual on-chain calls via web3.py
        # For MVP demo: return structured mock data
        # Real implementation would use:
        #   contract = web3.eth.contract(address=REGISTRY_ADDRESSES[chain_id], abi=REGISTRY_ABI)
        #   identity = contract.functions.resolve(agent_id).call()
        
        # Demo: simulate finding the agent on 1-3 chains
        import random
        if random.random() < 0.3:  # 30% chance agent is on this chain
            return None
        
        return ChainRegistration(
            chain_id=chain_id,
            chain_name=chain_name,
            agent_id_on_chain=agent_id,
            owner="0x" + "a" * 40,
            name=f"Agent-{agent_id[:8]}",
            metadata_uri=f"ar://{agent_id}/metadata.json",
            registered_at=datetime.utcnow(),
            reputation_score=round(random.uniform(2.5, 4.8), 1),
            total_ratings=random.randint(5, 200),
            completed_tasks=random.randint(3, 150)
        )
    
    async def resolve(
        self,
        agent_id: str,
        chain_id: int = 8453,  # Default: Base
        fetch_all_chains: bool = True
    ) -> Optional[AggregatedIdentity]:
        """
        Resolve cross-chain identity for an ERC-8004 agent.
        
        Args:
            agent_id: The agent's canonical ID (bytes32 hex)
            chain_id: The primary chain to resolve from
            fetch_all_chains: If True, scan all supported chains
            
        Returns:
            AggregatedIdentity with cross-chain registrations
        """
        logger.info(f"Resolving agent {agent_id[:16]}... on chain {chain_id}")
        
        # Fetch primary chain data
        primary_reg = await self._fetch_chain_data(agent_id, chain_id)
        if not primary_reg:
            logger.info(f"Agent {agent_id[:8]}... not found on chain {chain_id}")
            return None
        
        registrations = [primary_reg]
        
        # Fetch cross-chain registrations if requested
        if fetch_all_chains:
            tasks = [
                self._fetch_chain_data(agent_id, cid)
                for cid in self.rpc_urls.keys()
                if cid != chain_id
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, ChainRegistration) and result:
                    registrations.append(result)
        
        # Compute aggregated metrics
        total_reputation = sum(r.reputation_score for r in registrations)
        avg_reputation = total_reputation / len(registrations) if registrations else 0.0
        
        # Weighted by activity (tasks completed)
        total_tasks = sum(r.completed_tasks for r in registrations)
        if total_tasks > 0:
            weighted_rep = sum(
                r.reputation_score * r.completed_tasks 
                for r in registrations
            ) / total_tasks
        else:
            weighted_rep = avg_reputation
        
        # Owner consistency score
        owners = set(r.owner for r in registrations)
        consistency = 1.0 - (len(owners) - 1) / max(len(registrations) - 1, 1)
        
        # Determine trust level
        trust_level = self._score_to_trust_level(weighted_rep)
        
        # Primary chain name
        primary_name = self.rpc_urls.get(chain_id, {}).get("name", f"chain_{chain_id}")
        
        first_seen = min(
            (r.registered_at for r in registrations if r.registered_at),
            default=datetime.utcnow()
        )
        
        identity = AggregatedIdentity(
            canonical_agent_id=agent_id,
            primary_chain=chain_id,
            primary_chain_name=primary_name,
            registrations=registrations,
            total_chains=len(registrations),
            total_reputation_score=avg_reputation,
            weighted_reputation=weighted_rep,
            trust_level=trust_level,
            first_seen=first_seen,
            last_updated=datetime.utcnow(),
            consistency_score=consistency
        )
        
        # Cache the result
        self._set_cache(f"resolve:{agent_id}", identity)
        
        logger.info(
            f"Resolved {agent_id[:8]}... → {len(registrations)} chains, "
            f"trust={trust_level.value}, score={weighted_rep:.2f}"
        )
        
        return identity
    
    async def get_trust_score(
        self,
        agent_id: str,
        chain_id: int = 8453,
        include_breakdown: bool = True
    ) -> Optional[TrustScore]:
        """
        Compute human-readable trust score for an agent.
        
        This is the primary API for the x402 policy engine integration.
        """
        identity = await self.resolve(agent_id, chain_id)
        if not identity:
            return TrustScore(
                agent_id=agent_id,
                overall_score=0.0,
                trust_level=TrustLevel.FLAGGED,
                chain_breakdown={},
                activity_score=0.0,
                consistency_score=0.0,
                age_score=0.0,
                recommendation="REJECT",
                blockers=["Agent not registered on primary chain"]
            )
        
        # Score components
        reputation_score = identity.weighted_reputation
        activity_score = min(identity.total_chains / 5.0, 1.0)  # More chains = more active
        consistency_score = identity.consistency_score
        
        # Age score: older agents are more reliable
        if identity.first_seen:
            age_days = (datetime.utcnow() - identity.first_seen).days
            age_score = min(age_days / 90.0, 1.0)  # Max at 90 days
        else:
            age_score = 0.0
        
        # Chain breakdown
        chain_breakdown = {
            r.chain_name: r.reputation_score 
            for r in identity.registrations
        }
        
        # Overall score (weighted average)
        overall = (
            reputation_score * 0.5 +
            consistency_score * 0.2 +
            age_score * 0.15 +
            activity_score * 0.15
        ) * 5.0  # Scale to 0-5
        
        trust_level = self._score_to_trust_level(overall)
        
        # Recommendation
        if overall >= 4.0 and identity.total_chains >= 3:
            recommendation = "APPROVE"
        elif overall >= 3.0:
            recommendation = "REVIEW"
        else:
            recommendation = "REJECT"
        
        # Blockers
        blockers = []
        if identity.total_chains == 1:
            blockers.append("Single-chain registration — lower trust")
        if identity.consistency_score < 0.8:
            blockers.append("Owner inconsistency across chains")
        if overall < 2.5:
            blockers.append("Low reputation score")
        if identity.total_chains < 2:
            blockers.append("Limited cross-chain presence")
        
        score = TrustScore(
            agent_id=agent_id,
            overall_score=round(overall, 2),
            trust_level=trust_level,
            chain_breakdown=chain_breakdown,
            activity_score=round(activity_score, 2),
            consistency_score=round(consistency_score, 2),
            age_score=round(age_score, 2),
            recommendation=recommendation,
            blockers=blockers
        )
        
        # Cache
        self._set_cache(f"trust:{agent_id}", score)
        
        return score
    
    async def is_trusted_for_payment(
        self,
        agent_id: str,
        chain_id: int = 8453,
        min_score: float = 3.5,
        min_tasks: int = 5,
        min_chains: int = 1
    ) -> Dict[str, Any]:
        """
        Quick approval check for x402 policy engine.
        
        Returns:
            {
                "approved": bool,
                "reason": str,
                "trust_score": TrustScore,
                "elevated_limits": bool  # Can we raise their spending cap?
            }
        """
        score = await self.get_trust_score(agent_id, chain_id)
        
        if not score:
            return {
                "approved": False,
                "reason": "Agent not found in ERC-8004 registry",
                "trust_score": None,
                "elevated_limits": False
            }
        
        # Check thresholds
        if score.overall_score < min_score:
            return {
                "approved": False,
                "reason": f"Trust score {score.overall_score:.1f} below threshold {min_score}",
                "trust_score": score,
                "elevated_limits": False
            }
        
        total_tasks = sum(r.completed_tasks for r in score.chain_breakdown.values())
        if total_tasks < min_tasks:
            return {
                "approved": False,
                "reason": f"Task count {total_tasks} below minimum {min_tasks}",
                "trust_score": score,
                "elevated_limits": False
            }
        
        # Count chains from breakdown (approximate)
        num_chains = len(score.chain_breakdown)
        if num_chains < min_chains:
            return {
                "approved": False,
                "reason": f"Chain count {num_chains} below minimum {min_chains}",
                "trust_score": score,
                "elevated_limits": False
            }
        
        # APPROVED — determine if elevated limits apply
        elevated = score.trust_level in [TrustLevel.TRUSTED, TrustLevel.ELITE]
        
        return {
            "approved": True,
            "reason": f"Agent trusted — {score.trust_level.value} ({score.overall_score:.1f}/5.0)",
            "trust_score": score,
            "elevated_limits": elevated
        }
    
    def _score_to_trust_level(self, score: float) -> TrustLevel:
        """Convert numeric score to trust level."""
        if score >= 4.5:
            return TrustLevel.ELITE
        elif score >= 3.5:
            return TrustLevel.TRUSTED
        elif score >= 2.5:
            return TrustLevel.VERIFIED
        elif score >= 1.0:
            return TrustLevel.NEW
        else:
            return TrustLevel.FLAGGED
    
    def clear_cache(self):
        """Clear the result cache."""
        self.cache.clear()
        logger.info("Aggregator cache cleared")


class TAPResolver:
    """
    Trustless Agent Plus (TAP) resolver.
    The canonical implementation for cross-chain ERC-8004 identity resolution.
    
    Usage:
        resolver = TAPResolver()
        identity = await resolver.resolve("0xAgentId...")
        score = await resolver.score("0xAgentId...")
    """
    
    def __init__(self, aggregator: ERC8004Aggregator = None):
        self.aggregator = aggregator or ERC8004Aggregator()
    
    async def resolve(self, agent_id: str, chain_id: int = 8453) -> Optional[AggregatedIdentity]:
        """Resolve TAP identity."""
        return await self.aggregator.resolve(agent_id, chain_id)
    
    async def score(self, agent_id: str, chain_id: int = 8453) -> Optional[TrustScore]:
        """Get TAP trust score."""
        return await self.aggregator.get_trust_score(agent_id, chain_id)
    
    async def verify(self, agent_id: str, chain_id: int = 8453) -> Dict[str, Any]:
        """
        Full TAP verification — returns everything needed for x402 policy decision.
        """
        identity = await self.resolve(agent_id, chain_id)
        score = await self.score(agent_id, chain_id)
        payment_check = await self.aggregator.is_trusted_for_payment(agent_id, chain_id)
        
        return {
            "agent_id": agent_id,
            "chain_id": chain_id,
            "identity": identity.to_dict() if identity else None,
            "trust_score": score,
            "payment_approved": payment_check["approved"],
            "payment_reason": payment_check["reason"],
            "elevated_limits": payment_check["elevated_limits"],
            "recommendation": score.recommendation if score else "REJECT",
            "verified_at": datetime.utcnow().isoformat()
        }


# --- Demo ---

async def demo():
    """Run TAP resolver demo."""
    print("=" * 60)
    print("TAP: Trustless Agent Plus — Cross-Chain Identity Resolver")
    print("=" * 60)
    
    resolver = TAPResolver()
    
    # Demo agent
    demo_agent = "0x" + "deadbeef" * 8
    
    print(f"\n🔍 Resolving: {demo_agent[:20]}...")
    
    # Full verification
    result = await resolver.verify(demo_agent, chain_id=8453)
    
    print(f"\n📊 TAP Verification Result:")
    print(f"   Agent: {result['agent_id'][:16]}...")
    print(f"   Chain: {result['chain_id']}")
    print(f"   Payment Approved: {'✅' if result['payment_approved'] else '❌'} {result['payment_reason']}")
    print(f"   Elevated Limits: {'✅ Yes' if result['elevated_limits'] else '❌ No'}")
    
    if result['trust_score']:
        ts = result['trust_score']
        print(f"\n   ⭐ Trust Score: {ts.overall_score:.2f}/5.0 ({ts.trust_level.value})")
        print(f"   📋 Chain Breakdown: {ts.chain_breakdown}")
        print(f"   🏆 Recommendation: {ts.recommendation}")
        if ts.blockers:
            print(f"   ⚠️  Blockers: {ts.blockers}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())