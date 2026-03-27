# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""Support Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import SupportAction, SupportObservation
except ImportError:
    from models import SupportAction, SupportObservation


class SupportEnv(EnvClient[SupportAction, SupportObservation, State]):
    """Client for the Customer Support Environment."""

    def _step_payload(self, action: SupportAction) -> Dict:
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict) -> StepResult[SupportObservation]:
        obs_data = payload.get("observation", {})
        observation = SupportObservation(
            ticket_id=obs_data.get("ticket_id", ""),
            ticket_text=obs_data.get("ticket_text", ""),
            last_action_feedback=obs_data.get("last_action_feedback", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
