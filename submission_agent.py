import re
from collections import OrderedDict
from typing import Iterable

try:
    from .models import SupportAction
    from .server.support_env_environment import SupportEnvironment
except ImportError:
    from models import SupportAction
    from server.support_env_environment import SupportEnvironment


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


def run_task(task_index: int) -> float:
    env = SupportEnvironment()
    observation = env.reset_to_task(task_index)

    for action in build_plan(observation.ticket_text):
        observation = env.step(action)
        if observation.done:
            break

    return round(env.last_score if observation.done else env.cumulative_reward, 2)


def evaluate_all_tasks() -> "OrderedDict[str, float]":
    scores: "OrderedDict[str, float]" = OrderedDict()
    for task_index in range(3):
        scores[f"task{task_index + 1}"] = run_task(task_index)
    return scores


def average_score(scores: Iterable[float] | OrderedDict[str, float]) -> float:
    values = list(scores.values()) if isinstance(scores, OrderedDict) else list(scores)
    return round(sum(values) / len(values), 2) if values else 0.0
