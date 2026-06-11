"""
x402 Policy Engine — Python SDK for autonomous AI agent payments.
pip install x402-policy
"""

from .policy import (
    PolicyConfig,
    PolicyViolation,
    SpendingLimitExceeded,
    PerTransactionLimitExceeded,
    RecipientNotAllowed,
    TimeWindowViolation,
    TimeWindow,
    PaymentRecord,
    SpendContext,
    create_policy
)

from .x402_client import (
    x402PaymentRequest,
    x402PaymentResponse,
    x402PolicyClient,
    x402BatchClient
)

from .erc8004 import (
    AgentInfo,
    AgentReputation,
    CrossChainIdentity,
    ERC8004Reader,
    ERC8004PaymentIntegration
)

from .tap_resolver import (
    ERC8004Aggregator,
    TAPResolver,
    TrustLevel,
    AggregatedIdentity,
    TrustScore,
    ChainRegistration
)

from .session_keys import (
    SessionKeyManager,
    RelayerService,
    SessionKey,
    SpendLimit,
    SessionKeyError,
    SessionExpiredError,
    SpendingLimitExceededError
)

__version__ = "0.2.0"
__all__ = [
    # Policy engine
    "PolicyConfig",
    "PolicyViolation",
    "SpendingLimitExceeded",
    "PerTransactionLimitExceeded",
    "RecipientNotAllowed",
    "TimeWindowViolation",
    "TimeWindow",
    "PaymentRecord",
    "SpendContext",
    "create_policy",
    # x402 client
    "x402PaymentRequest",
    "x402PaymentResponse",
    "x402PolicyClient",
    "x402BatchClient",
    # ERC-8004
    "AgentInfo",
    "AgentReputation",
    "CrossChainIdentity",
    "ERC8004Reader",
    "ERC8004PaymentIntegration",
    # TAP Aggregator
    "ERC8004Aggregator",
    "TAPResolver",
    "TrustLevel",
    "AggregatedIdentity",
    "TrustScore",
    "ChainRegistration",
    # Session Keys
    "SessionKeyManager",
    "RelayerService",
    "SessionKey",
    "SpendLimit",
    "SessionKeyError",
    "SessionExpiredError",
    "SpendingLimitExceededError",
]