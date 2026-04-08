# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Customer Support Environment Implementation.

This environment models a realistic Tier-1 support workflow:
- retrieve internal context before acting
- respect policy before issuing refunds
- send a customer-facing resolution only after gathering enough evidence
"""

from uuid import uuid4
import random

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import SupportAction, SupportObservation
except ImportError:
    from models import SupportAction, SupportObservation


TASKS = [
    {
        "id": "task_1",
        "scenario": "password_reset",
        "difficulty": "easy",
        "ticket_text": "Hi, I forgot my password. How do I reset it?",
        "description": "Handle a password reset request by searching the KB and sending the reset link.",
        "kb_query_terms": ["password", "reset"],
        "kb_success_feedback": "KB Search Result: Password resets must be completed through the secure reset link.",
        "requires_kb": True,
        "requires_db": False,
        "refund_allowed": False,
        "reply_all_keywords": ["reset", "link"],
        "reply_reward": 0.65,
        "kb_reward": 0.30,
        "success_feedback": "Ticket resolved successfully with the correct password reset guidance.",
        "failure_feedback": "The response did not give the customer the correct reset instructions.",
        "max_steps": 3,
    },
    {
        "id": "task_2",
        "scenario": "lost_order_refund",
        "difficulty": "medium",
        "ticket_text": "Where is my order #12345? It was supposed to arrive yesterday.",
        "description": "Handle a lost order by querying the DB, issuing a refund, and replying.",
        "order_id": "12345",
        "db_success_feedback": "DB Status: Order 12345 is lost in transit. The order is eligible for a refund.",
        "requires_kb": False,
        "requires_db": True,
        "refund_allowed": True,
        "reply_requires_refund": True,
        "reply_all_keywords": ["refund"],
        "reply_any_keywords": ["issued", "processed", "refunded"],
        "db_reward": 0.25,
        "refund_reward": 0.25,
        "reply_reward": 0.45,
        "success_feedback": "Ticket resolved successfully after confirming loss and issuing the refund.",
        "failure_feedback": "The customer was not given a correct lost-order resolution.",
        "max_steps": 5,
    },
    {
        "id": "task_3",
        "scenario": "refund_denial",
        "difficulty": "hard",
        "ticket_text": "I am angry! I want a refund for my Pro subscription (Order #999) purchased 20 days ago.",
        "description": "Deny a refund that falls outside the 14-day subscription refund window.",
        "order_id": "999",
        "db_success_feedback": "DB Status: Order 999 was purchased 20 days ago.",
        "kb_query_terms": ["refund", "policy", "subscription", "14 days"],
        "kb_success_feedback": "KB Search Result: Pro subscription refunds are only allowed within 14 days of purchase.",
        "requires_kb": True,
        "requires_db": True,
        "refund_allowed": False,
        "reply_all_keywords": ["cannot"],
        "reply_any_keywords": ["14 days", "policy", "window"],
        "db_reward": 0.20,
        "kb_reward": 0.15,
        "reply_reward": 0.60,
        "success_feedback": "Correct resolution provided. The refund denial followed the stated policy.",
        "failure_feedback": "The refund denial was incorrect or did not explain the policy reason.",
        "max_steps": 6,
    },
    {
        "id": "task_4",
        "scenario": "damaged_item_refund",
        "difficulty": "hard",
        "ticket_text": "My blender arrived broken today. Order #777 was delivered 3 days ago. Please help.",
        "description": "Refund a damaged item only after checking both order status and the return policy.",
        "order_id": "777",
        "db_success_feedback": "DB Status: Order 777 was delivered 3 days ago and is eligible for a damage-related refund.",
        "kb_query_terms": ["damaged", "return", "refund", "broken"],
        "kb_success_feedback": "KB Search Result: Damaged products delivered within 7 days can be refunded immediately.",
        "requires_kb": True,
        "requires_db": True,
        "refund_allowed": True,
        "reply_requires_refund": True,
        "reply_all_keywords": ["refund"],
        "reply_any_keywords": ["damaged", "broken", "issued"],
        "db_reward": 0.15,
        "kb_reward": 0.15,
        "refund_reward": 0.25,
        "reply_reward": 0.40,
        "success_feedback": "Ticket resolved successfully with a policy-backed damaged-item refund.",
        "failure_feedback": "The damaged-item case was not resolved with the correct safe workflow.",
        "max_steps": 6,
    },
    {
        "id": "task_5",
        "scenario": "address_change_after_shipping",
        "difficulty": "hard",
        "ticket_text": "Can you change the shipping address for order #555? It already shipped this morning.",
        "description": "Decline an address change once an order has already shipped and point the customer to the carrier.",
        "order_id": "555",
        "db_success_feedback": "DB Status: Order 555 has already shipped and the warehouse can no longer edit the address.",
        "kb_query_terms": ["address change", "shipped", "carrier", "shipping"],
        "kb_success_feedback": "KB Search Result: Address changes are blocked after shipment. Customers must contact the carrier for rerouting options.",
        "requires_kb": True,
        "requires_db": True,
        "refund_allowed": False,
        "reply_all_keywords": ["cannot"],
        "reply_any_keywords": ["carrier", "shipped", "rerouting"],
        "db_reward": 0.20,
        "kb_reward": 0.15,
        "reply_reward": 0.60,
        "success_feedback": "Correct resolution provided for the shipped-order address change request.",
        "failure_feedback": "The response did not correctly explain why the address can no longer be edited.",
        "max_steps": 5,
    },
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _reply_matches(task: dict, message: str) -> bool:
    all_keywords = task.get("reply_all_keywords", [])
    any_keywords = task.get("reply_any_keywords", [])
    forbidden_keywords = task.get("reply_forbidden_keywords", [])

    has_all = all(keyword in message for keyword in all_keywords)
    has_any = True if not any_keywords else _contains_any(message, any_keywords)
    has_forbidden = _contains_any(message, forbidden_keywords) if forbidden_keywords else False
    return has_all and has_any and not has_forbidden


class SupportEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.task_idx = 0
        self.done = False
        self.cumulative_reward = 0.0
        self.last_score = 0.0
        self.kb_verified = False
        self.db_verified = False
        self.refund_issued = False

    def _reset_episode_state(self) -> None:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.done = False
        self.cumulative_reward = 0.0
        self.last_score = 0.0
        self.kb_verified = False
        self.db_verified = False
        self.refund_issued = False

    def reset(self) -> SupportObservation:
        self._reset_episode_state()
        self.task_idx = random.randint(0, len(TASKS) - 1)
        task = TASKS[self.task_idx]

        return SupportObservation(
            ticket_id=task["id"],
            ticket_text=task["ticket_text"],
            last_action_feedback="New ticket assigned. Gather evidence before taking an irreversible action.",
            done=False,
            reward=0.0,
        )

    def reset_to_task(self, task_idx: int) -> SupportObservation:
        self._reset_episode_state()
        self.task_idx = task_idx
        task = TASKS[self.task_idx]

        return SupportObservation(
            ticket_id=task["id"],
            ticket_text=task["ticket_text"],
            last_action_feedback="New ticket assigned. Gather evidence before taking an irreversible action.",
            done=False,
            reward=0.0,
        )

    def step(self, action: SupportAction) -> SupportObservation:  # type: ignore[override]
        if self.done:
            return SupportObservation(
                ticket_id=TASKS[self.task_idx]["id"],
                ticket_text="",
                last_action_feedback="Episode already done.",
                done=True,
                reward=0.0,
            )

        self._state.step_count += 1
        reward = 0.0
        feedback = "Action executed."
        task = TASKS[self.task_idx]
        act = action.action_type

        if act == "search_kb":
            query = str(action.query or "").lower()
            expected_terms = task.get("kb_query_terms", [])
            if expected_terms and _contains_any(query, expected_terms):
                if not self.kb_verified:
                    reward += task.get("kb_reward", 0.15)
                self.kb_verified = True
                feedback = task["kb_success_feedback"]
            else:
                reward -= 0.05
                feedback = "No relevant KB articles found."

        elif act == "query_db":
            if str(action.query or "") == task.get("order_id"):
                if not self.db_verified:
                    reward += task.get("db_reward", 0.20)
                self.db_verified = True
                feedback = task["db_success_feedback"]
            else:
                reward -= 0.05
                feedback = "DB Status: Order not found in the system."

        elif act == "issue_refund":
            if not task.get("refund_allowed", False):
                reward -= 0.20
                feedback = "Refund is not permitted for this case."
            elif str(action.order_id or "") != task.get("order_id"):
                reward -= 0.15
                feedback = "Refund failed because the order ID is invalid."
            elif task.get("requires_db") and not self.db_verified:
                reward -= 0.15
                feedback = "Refund blocked: query the order record before issuing a refund."
            elif task.get("requires_kb") and not self.kb_verified:
                reward -= 0.10
                feedback = "Refund blocked: consult the relevant policy before issuing a refund."
            elif self.refund_issued:
                reward -= 0.05
                feedback = "Refund was already issued for this ticket."
            else:
                self.refund_issued = True
                reward += task.get("refund_reward", 0.25)
                feedback = "Refund issued successfully."

        elif act == "reply":
            self.done = True
            message = str(action.message or "").lower()
            missing_steps = []

            if task.get("requires_db") and not self.db_verified:
                missing_steps.append("database check")
            if task.get("requires_kb") and not self.kb_verified:
                missing_steps.append("policy lookup")
            if task.get("reply_requires_refund") and not self.refund_issued:
                missing_steps.append("refund issuance")

            if missing_steps:
                reward -= 0.30
                feedback = f"Reply was premature; missing {', '.join(missing_steps)}."
            elif _reply_matches(task, message):
                reward += task.get("reply_reward", 0.55)
                feedback = task["success_feedback"]
            else:
                reward -= 0.40
                feedback = task["failure_feedback"]

        else:
            reward -= 0.10
            feedback = "System Error: Invalid action type provided."

        if self._state.step_count >= task["max_steps"] and not self.done:
            self.done = True
            reward -= 0.25
            feedback = "Max steps exceeded. The ticket was not resolved in time."

        self.cumulative_reward += reward
        final_reward = round(reward, 2)
        if self.done:
            self.last_score = max(0.0, min(1.0, round(self.cumulative_reward, 2)))

        return SupportObservation(
            ticket_id=task["id"],
            ticket_text=task["ticket_text"],
            last_action_feedback=feedback,
            done=self.done,
            reward=final_reward,
            metadata={
                "step": self._state.step_count,
                "kb_verified": self.kb_verified,
                "db_verified": self.db_verified,
                "refund_issued": self.refund_issued,
            },
        )

    @property
    def state(self) -> State:
        return self._state
