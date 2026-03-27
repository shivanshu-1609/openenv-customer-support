# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Customer Support Environment Implementation.
This class acts as our referee/game-engine for testing Agentic AI on customer tickets.
"""
from uuid import uuid4
import random

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import SupportAction, SupportObservation
except ImportError:
    from models import SupportAction, SupportObservation

# We define three distinct tasks here: Easy, Medium, and Hard
# This ensures we can test if the AI is capable of executing both simple searches
# and more complex logic (like checking dates before issuing refunds).
TASKS = [
    {
        "id": "task_1",
        "difficulty": "easy",
        "ticket_text": "Hi, I forgot my password. How do I reset it?",
        "expected_kb_query": "password",
        "resolution_keyword": "reset",
        "max_steps": 3,
        "description": "Handle a password reset request by searching the KB and sending the reset link."
    },
    {
        "id": "task_2",
        "difficulty": "medium",
        "ticket_text": "Where is my order #12345? It was supposed to arrive yesterday.",
        "expected_db_query": "12345",
        "requires_refund": True,
        "max_steps": 5,
        "description": "Handle a lost order by querying the DB, issuing a refund, and replying."
    },
    {
        "id": "task_3",
        "difficulty": "hard",
        "ticket_text": "I am angry! I want a refund for my Pro subscription (Order #999) purchased 20 days ago.",
        "expected_db_query": "999",
        "requires_refund": False,
        "max_steps": 7,
        "description": "Handle a refund request for a Pro subscription by checking the policy and user purchase date. Deny if > 14 days."
    }
]


class SupportEnvironment(Environment):
    # Required by OpenEnv to handle multiple users simultaneously hitting the server via WebSockets
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        # We start by initializing the state and scores to zero
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.task_idx = 0
        self.done = False
        self.cumulative_reward = 0.0
        self.last_score = 0.0

    def reset(self) -> SupportObservation:
        """
        Runs whenever a new episode starts. Picks a random ticket and returns it.
        """
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.done = False
        self.cumulative_reward = 0.0
        self.last_score = 0.0
        
        # Pick a random ticket from our TASKS list
        self.task_idx = random.randint(0, len(TASKS) - 1)
        task = TASKS[self.task_idx]

        return SupportObservation(
            ticket_id=task["id"],
            ticket_text=task["ticket_text"],
            last_action_feedback="New ticket assigned. Waiting for agent action.",
            done=False,
            reward=0.0
        )

    def reset_to_task(self, task_idx: int) -> SupportObservation:
        """
        Helper method to force a specific task (useful for strict debugging/testing).
        """
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.done = False
        self.cumulative_reward = 0.0
        self.last_score = 0.0
        self.task_idx = task_idx
        task = TASKS[self.task_idx]

        return SupportObservation(
            ticket_id=task["id"],
            ticket_text=task["ticket_text"],
            last_action_feedback="New ticket assigned.",
            done=False,
            reward=0.0
        )

    def step(self, action: SupportAction) -> SupportObservation:  # type: ignore[override]
        """
        The core engine. Evaluates the agent's action and computes the reward.
        """
        # If the episode is already over, don't let the agent do anything else
        if self.done:
            return SupportObservation(
                ticket_id=TASKS[self.task_idx]["id"],
                ticket_text="",
                last_action_feedback="Episode already done.",
                done=True,
                reward=0.0
            )

        self._state.step_count += 1
        reward = 0.0
        feedback = "Action executed."
        task = TASKS[self.task_idx]

        # Extract the action type from the Pydantic model
        act = action.action_type
        
        # 1. Searching the Knowledge Base
        if act == "search_kb":
            if task["difficulty"] == "easy" and task["expected_kb_query"] in str(action.query).lower():
                feedback = "KB Search Result: Send the user a 'reset' link to complete the password reset."
                reward += 0.2  # Small reward to encourage proper tool usage
            elif task["difficulty"] == "hard" and "refund" in str(action.query).lower():
                feedback = "KB Search Result: Refunds are allowed ONLY within 14 days of original purchase."
                reward += 0.2
            else:
                feedback = "No relevant KB articles found."
                
        # 2. Querying the internal Orders database
        elif act == "query_db":
            # The agent must extract the exact order_id string and pass it.
            if str(action.query) == task.get("expected_db_query"):
                if task["difficulty"] == "medium":
                    feedback = f"DB Status: Order {action.query} is lost in transit. Currently eligible for a refund."
                    reward += 0.2
                elif task["difficulty"] == "hard":
                    feedback = f"DB Status: Order {action.query} was purchased 20 days ago."
                    reward += 0.2
            else:
                feedback = "DB Status: Order not found in the system."
                
        # 3. Issuing a standard refund
        elif act == "issue_refund":
            if task.get("requires_refund") and str(action.order_id) == task.get("expected_db_query"):
                feedback = "Refund issued successfully."
                reward += 0.3
            else:
                feedback = "Warning: Refund failed or is not permitted according to policy."
                reward -= 0.1  # Penalize destructive or unpermitted actions
                
        # 4. Final reply to close the ticket
        elif act == "reply":
            self.done = True
            msg = str(action.message).lower()
            
            # Did the agent solve the specific ticket correctly?
            if task["difficulty"] == "easy" and task["resolution_keyword"] in msg:
                reward += 0.8
                feedback = "Ticket resolved successfully."
            elif task["difficulty"] == "medium" and "refund" in msg:
                reward += 0.5
                feedback = "Ticket resolved successfully."
            elif task["difficulty"] == "hard" and ("cannot" in msg or "deny" in msg or "14 days" in msg):
                reward += 0.8
                feedback = "Correct resolution provided. Policy was accurately upheld."
            else:
                reward -= 0.5
                feedback = "Incorrect resolution provided to the customer."
                
        else:
            feedback = "System Error: Invalid action type provided."
            reward -= 0.1

        # Prevent agents from looping infinitely to farm rewards
        if self._state.step_count >= task["max_steps"] and not self.done:
            self.done = True
            feedback = "Max steps exceeded. Agent failed to resolve the ticket in time."
            reward -= 0.5

        # Accumulate episodic reward
        self.cumulative_reward += reward

        # OpenEnv strictly requires scores bounded [0.0, 1.0] for the grader endpoints
        final_reward = round(reward, 2)
        if self.done:
            self.last_score = max(0.0, min(1.0, self.cumulative_reward))

        return SupportObservation(
            ticket_id=task["id"],
            ticket_text=task["ticket_text"],
            last_action_feedback=feedback,
            done=self.done,
            reward=final_reward,
            metadata={"step": self._state.step_count}
        )

    @property
    def state(self) -> State:
        return self._state
