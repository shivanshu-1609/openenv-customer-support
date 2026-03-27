# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Data models for the Customer Support Environment.
"""

from openenv.core.env_server.types import Action, Observation
from pydantic import Field
from typing import Optional


class SupportAction(Action):
    """Action for the Customer Support Environment."""
    action_type: str = Field(..., description="Action type: 'search_kb', 'query_db', 'issue_refund', 'reply'")
    query: Optional[str] = Field(None, description="Search query or DB query parameter")
    order_id: Optional[str] = Field(None, description="Order ID to issue_refund")
    message: Optional[str] = Field(None, description="Reply message to the customer")


class SupportObservation(Observation):
    """Observation from the Customer Support Environment."""
    ticket_id: str = Field(..., description="ID of the current ticket")
    ticket_text: str = Field(..., description="Content of the customer ticket")
    last_action_feedback: str = Field(..., description="Feedback from the last action taken")
