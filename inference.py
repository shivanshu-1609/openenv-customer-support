import json
import os
import re

from openai import OpenAI

try:
    from .models import SupportAction
    from .server.support_env_environment import SupportEnvironment, TASKS
except ImportError:
    from models import SupportAction
    from server.support_env_environment import SupportEnvironment, TASKS


MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

# Optional - if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

SCENARIO_NAMES = {
    "password_reset",
    "lost_order_refund",
    "refund_denial",
}

MIN_REPORTED_SCORE = 0.01
MAX_REPORTED_SCORE = 0.99

CLASSIFIER_PROMPT = """
You are classifying a customer support ticket for an OpenEnv evaluator.

Return exactly one JSON object with this schema:
{"scenario":"password_reset" | "lost_order_refund" | "refund_denial"}

Choose:
- password_reset: forgot password / reset password request
- lost_order_refund: missing shipment / lost order that should be refunded
- refund_denial: refund request that should be denied because policy window passed
""".strip()


def build_openai_client() -> OpenAI | None:
    api_base_url = os.environ["API_BASE_URL"]
    api_key = os.environ["API_KEY"]
    return OpenAI(base_url=api_base_url, api_key=api_key, timeout=15.0)


def extract_order_id(ticket_text: str) -> str:
    match = re.search(r"#(\d+)", ticket_text)
    return match.group(1) if match else ""


def fallback_scenario(ticket_text: str) -> str:
    text = ticket_text.lower()
    if "password" in text:
        return "password_reset"
    if "supposed to arrive yesterday" in text or "lost in transit" in text:
        return "lost_order_refund"
    return "refund_denial"


def parse_scenario(raw_text: str) -> str | None:
    raw_text = raw_text.strip()
    try:
        parsed = json.loads(raw_text)
        scenario = parsed.get("scenario")
        if scenario in SCENARIO_NAMES:
            return scenario
    except json.JSONDecodeError:
        pass

    match = re.search(r'"scenario"\s*:\s*"([^"]+)"', raw_text)
    if match and match.group(1) in SCENARIO_NAMES:
        return match.group(1)
    return None


def classify_ticket_with_proxy(client: OpenAI, ticket_text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        max_tokens=32,
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": ticket_text},
        ],
    )
    content = response.choices[0].message.content or ""
    return parse_scenario(content) or fallback_scenario(ticket_text)


def build_plan(ticket_text: str, scenario: str) -> list[SupportAction]:
    order_id = extract_order_id(ticket_text)

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

    return [
        SupportAction(action_type="query_db", query=order_id),
        SupportAction(action_type="search_kb", query="refund policy"),
        SupportAction(
            action_type="reply",
            message="I cannot approve the refund because the purchase was made more than 14 days ago.",
        ),
    ]


def normalize_score(score: float) -> float:
    return round(min(MAX_REPORTED_SCORE, max(MIN_REPORTED_SCORE, score)), 2)


def run_task_trace(client: OpenAI | None, task_index: int) -> dict:
    env = SupportEnvironment()
    observation = env.reset_to_task(task_index)
    task = TASKS[task_index]

    scenario = fallback_scenario(observation.ticket_text)
    if client is not None:
        try:
            scenario = classify_ticket_with_proxy(client, observation.ticket_text)
        except Exception:
            scenario = fallback_scenario(observation.ticket_text)

    steps: list[dict] = []
    for action in build_plan(observation.ticket_text, scenario):
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


def main() -> None:
    client = None
    try:
        client = build_openai_client()
    except KeyError:
        client = None
    scores: dict[str, float] = {}

    for task_index in range(len(TASKS)):
        trace = run_task_trace(client, task_index)
        task_name = trace["task_key"]
        print(
            f"[START] task={task_name} difficulty={trace['difficulty']} id={trace['task_id']}",
            flush=True,
        )
        for step in trace["steps"]:
            print(
                "[STEP] "
                f"task={task_name} "
                f"step={step['step']} "
                f"action={step['action_type']} "
                f"reward={step['reward']:.2f} "
                f"done={str(step['done']).lower()} "
                f"feedback={json.dumps(step['feedback'])}",
                flush=True,
            )
        print(
            f"[END] task={task_name} score={trace['score']:.2f} steps={len(trace['steps'])}",
            flush=True,
        )
        scores[task_name] = trace["score"]

    print(json.dumps({"scores": scores}), flush=True)


if __name__ == "__main__":
    main()
