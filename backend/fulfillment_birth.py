"""Creation-time fulfillment strategy. Not an assignment engine.

Strategy at birth is a product invariant. It is not an Admin setting.
"""
from fulfillment_commit import CAMPAIGN, DIRECT_REBOOK, MULTI_OFFER

BORN_STRATEGIES = frozenset({MULTI_OFFER, DIRECT_REBOOK, CAMPAIGN})


def initial_fulfillment_fields(strategy: str, started_at: str) -> dict:
    """Fields written on the same insert as the new request."""
    if strategy not in BORN_STRATEGIES:
        raise ValueError(f"unknown fulfillment strategy: {strategy}")
    if not started_at:
        raise ValueError("fulfillment strategy start time is required")
    return {
        "fulfillment_strategy": strategy,
        "fulfillment_strategy_started_at": started_at,
    }
