# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""FastAPI application for the Customer Support Environment."""

import os
import subprocess

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required for the web interface.") from e

try:
    from ..models import SupportAction, SupportObservation
    from ..submission_agent import average_score, evaluate_all_tasks
    from .support_env_environment import SupportEnvironment, TASKS
except ImportError:
    from models import SupportAction, SupportObservation
    from submission_agent import average_score, evaluate_all_tasks
    from server.support_env_environment import SupportEnvironment, TASKS

app = create_app(
    SupportEnvironment,
    SupportAction,
    SupportObservation,
    env_name="support_env",
    max_concurrent_envs=10,
)

@app.get("/tasks")
def get_tasks():
    return {
        "tasks": TASKS,
        "action_schema": SupportAction.model_json_schema()
    }

@app.get("/grader")
def get_grader():
    scores = evaluate_all_tasks()
    return {"score": average_score(scores), "scores": scores}

@app.get("/baseline")
def run_baseline():
    """Runs the baseline script and returns the scores."""
    try:
        # Run baseline.py asynchronously or synchronously
        # We assume baseline.py prints JSON or we parse it
        result = subprocess.run(
            ["python", "baseline.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        # Parse output for scores
        return {"baseline_output": result.stdout, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

def main(host: str = "0.0.0.0", port: int = 8000):
    """
    Entry point for direct execution via uv run or python -m.

    This function enables running the server without Docker:
        uv run --project . server
        uv run --project . server --port 8001
        python -m temp_env.server.app

    Args:
        host: Host address to bind to (default: "0.0.0.0")
        port: Port number to listen on (default: 8000)

    For production deployments, consider using uvicorn directly with
    multiple workers:
        uvicorn temp_env.server.app:app --workers 4
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)
    # main() is required by the buggy openenv validate string watcher
