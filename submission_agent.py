import re
from collections import OrderedDict
from typing import Iterable

try:
    from .models import SupportAction
    from .server.support_env_environment import SupportEnvironment, TASKS
except ImportError:
    from models import SupportAction
    from server.support_env_environment import SupportEnvironment, TASKS


MIN_REPORTED_SCORE = 0.01
MAX_REPORTED_SCORE = 0.99


def _extract_order_id(ticket_text: str) -> str:
    match = re.search(r"#(\d+)", ticket_text)
    return match.group(1) if match else ""


def normalize_score(score: float) -> float:
    return round(min(MAX_REPORTED_SCORE, max(MIN_REPORTED_SCORE, score)), 2)


def build_plan(ticket_text: str, scenario: str) -> list[SupportAction]:
    order_id = _extract_order_id(ticket_text)

    if scenario == "password_reset":
        return [
            SupportAction(action_type="search_kb", query="password reset"),
            SupportAction(
                action_type="reply",
                message="Use the password reset link to securely reset your password.",
            ),
        ]

    if scenario == "lost_order_refund":
        return [
            SupportAction(action_type="query_db", query=order_id),
            SupportAction(action_type="issue_refund", order_id=order_id),
            SupportAction(
                action_type="reply",
                message="Your order was lost in transit, so I issued a refund right away.",
            ),
        ]

    if scenario == "refund_denial":
        return [
            SupportAction(action_type="query_db", query=order_id),
            SupportAction(action_type="search_kb", query="subscription refund policy 14 days"),
            SupportAction(
                action_type="reply",
                message="I cannot approve the refund because the purchase is outside the 14 day policy window.",
            ),
        ]

    if scenario == "damaged_item_refund":
        return [
            SupportAction(action_type="query_db", query=order_id),
            SupportAction(action_type="search_kb", query="damaged item refund policy"),
            SupportAction(action_type="issue_refund", order_id=order_id),
            SupportAction(
                action_type="reply",
                message="Your damaged item qualifies for a refund, and I have issued it for you.",
            ),
        ]

    return [
        SupportAction(action_type="query_db", query=order_id),
        SupportAction(action_type="search_kb", query="address change shipped order policy"),
        SupportAction(
            action_type="reply",
            message="I cannot change the address because the order has already shipped, so please contact the carrier for rerouting.",
        ),
    ]


def run_task_trace(task_index: int) -> dict:
    env = SupportEnvironment()
    observation = env.reset_to_task(task_index)
    task = TASKS[task_index]
    steps: list[dict] = []

    for action in build_plan(observation.ticket_text, task["scenario"]):
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

    raw_score = round(env.last_score if observation.done else env.cumulative_reward, 2)
    score = normalize_score(raw_score)
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
    for task_index in range(len(TASKS)):
        scores[f"task{task_index + 1}"] = run_task(task_index)
    return scores


def evaluate_all_tasks_with_traces() -> list[dict]:
    return [run_task_trace(task_index) for task_index in range(len(TASKS))]


def average_score(scores: Iterable[float] | OrderedDict[str, float]) -> float:
    values = list(scores.values()) if isinstance(scores, OrderedDict) else list(scores)
    return normalize_score(sum(values) / len(values)) if values else MIN_REPORTED_SCORE
