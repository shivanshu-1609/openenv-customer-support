# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Data models for the Customer Support Environment.
"""

from typing import Optional

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class SupportAction(Action):
    """Action for the Customer Support Environment."""
    action_type: str = Field(
        ...,
        description="One of: 'search_kb', 'query_db', 'issue_refund', or 'reply'.",
    )
    query: Optional[str] = Field(
        None,
        description="Knowledge-base query text or the order identifier used by 'query_db'.",
    )
    order_id: Optional[str] = Field(
        None,
        description="Order ID required when the action_type is 'issue_refund'.",
    )
    message: Optional[str] = Field(
        None,
        description="Customer-facing response content used when the action_type is 'reply'.",
    )


class SupportObservation(Observation):
    """Observation from the Customer Support Environment."""
    ticket_id: str = Field(..., description="ID of the current ticket")
    difficulty: str = Field(..., description="Difficulty level for the current task.")
    ticket_text: str = Field(..., description="Content of the customer ticket")
    available_actions: list[str] = Field(
        default_factory=list,
        description="Valid structured actions that the agent can take in the current state.",
    )
    requires_policy_check: bool = Field(
        ...,
        description="Whether the ticket requires a KB or policy lookup before the final reply.",
    )
    requires_order_lookup: bool = Field(
        ...,
        description="Whether the ticket requires querying the internal order record.",
    )
    policy_checked: bool = Field(
        ...,
        description="Whether the agent has already gathered the relevant policy evidence.",
    )
    order_verified: bool = Field(
        ...,
        description="Whether the agent has already verified the order in the internal database.",
    )
    refund_issued: bool = Field(
        ...,
        description="Whether a refund has already been issued in the current episode.",
    )
    remaining_steps: int = Field(
        ...,
        description="How many steps remain before the episode times out.",
    )
    last_action_feedback: str = Field(..., description="Feedback from the last action taken")
