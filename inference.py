import json

try:
    from .submission_agent import evaluate_all_tasks
except ImportError:
    from submission_agent import evaluate_all_tasks


def main() -> None:
    print(json.dumps({"scores": evaluate_all_tasks()}))


if __name__ == "__main__":
    main()
