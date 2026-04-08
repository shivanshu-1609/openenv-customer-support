import re
from collections import OrderedDict
from typing import Iterable

try:
    from .models import SupportAction
    from .server.support_env_environment import SupportEnvironment, TASKS
except ImportError:
    from models import SupportAction
    from server.support_env_environment import SupportEnvironment, TASKS


def _extract_order_id(ticket_text: str) -> str:
    match = re.search(r"#(\d+)", ticket_text)
    return match.group(1) if match else ""


def build_plan(ticket_text: str) -> list[SupportAction]:
    text = ticket_text.lower()

    if "password" in text:
        return [
            SupportAction(action_type="search_kb", query="password reset"),
            SupportAction(
                action_type="reply",
                message="Use the password reset link to securely reset your password.",
            ),
        ]

    order_id = _extract_order_id(ticket_text)

    if "supposed to arrive yesterday" in text:
        return [
            SupportAction(action_type="query_db", query=order_id),
            SupportAction(action_type="issue_refund", order_id=order_id),
            SupportAction(
                action_type="reply",
                message="Your order was lost in transit, so I issued a refund right away.",
            ),
        ]

    return [
        SupportAction(action_type="query_db", query=order_id),
        SupportAction(action_type="search_kb", query="refund policy"),
        SupportAction(
            action_type="reply",
            message="I cannot approve the refund because the purchase was made more than 14 days ago.",
        ),
    ]


def run_task_trace(task_index: int) -> dict:
    env = SupportEnvironment()
    observation = env.reset_to_task(task_index)
    task = TASKS[task_index]
    steps: list[dict] = []

    for action in build_plan(observation.ticket_text):
        observation = env.step(action)
        steps.append(
            {
                "step": len(steps) + 1,
                "action_type": action.action_type,
                "reward": round(observation.reward, 2),
                "done": observation.done,
                "feedback": observation.last_action_feedback,
            }
        )
        if observation.done:
            break

    score = round(env.last_score if observation.done else env.cumulative_reward, 2)
    return {
        "task_key": f"task{task_index + 1}",
        "task_id": task["id"],
        "difficulty": task["difficulty"],
        "steps": steps,
        "score": score,
    }


def run_task(task_index: int) -> float:
    return run_task_trace(task_index)["score"]


def evaluate_all_tasks() -> "OrderedDict[str, float]":
    scores: "OrderedDict[str, float]" = OrderedDict()
    for task_index in range(3):
        scores[f"task{task_index + 1}"] = run_task(task_index)
    return scores


def evaluate_all_tasks_with_traces() -> list[dict]:
    return [run_task_trace(task_index) for task_index in range(3)]


def average_score(scores: Iterable[float] | OrderedDict[str, float]) -> float:
    values = list(scores.values()) if isinstance(scores, OrderedDict) else list(scores)
    return round(sum(values) / len(values), 2) if values else 0.0
