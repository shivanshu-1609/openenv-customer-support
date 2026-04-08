import json

try:
    from .submission_agent import evaluate_all_tasks_with_traces
except ImportError:
    from submission_agent import evaluate_all_tasks_with_traces


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
