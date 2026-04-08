import os
import json

from openai import OpenAI

try:
    from .submission_agent import evaluate_all_tasks_with_traces
except ImportError:
    from submission_agent import evaluate_all_tasks_with_traces


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional - if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")


def build_openai_client() -> OpenAI:
    if HF_TOKEN is None:
        raise RuntimeError("HF_TOKEN is required for LLM-backed inference.")
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


def main() -> None:
    traces = evaluate_all_tasks_with_traces()
    scores: dict[str, float] = {}

    for trace in traces:
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
