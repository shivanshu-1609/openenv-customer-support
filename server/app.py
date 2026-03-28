# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""FastAPI application for the Customer Support Environment."""

import os
import subprocess

from fastapi.responses import HTMLResponse

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

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    scores = evaluate_all_tasks()
    average = average_score(scores)
    task_items = "".join(
        f"<li><strong>{task['difficulty'].title()}</strong>: {task['description']}</li>"
        for task in TASKS
    )
    score_items = "".join(
        f"<li><strong>{task_id}</strong>: {score:.2f}</li>"
        for task_id, score in scores.items()
    )

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Customer Support Env</title>
        <style>
            :root {{
                color-scheme: dark;
                --bg: #07111f;
                --panel: #0f1b2d;
                --panel-border: #1f3350;
                --text: #ecf4ff;
                --muted: #9eb2cc;
                --accent: #5eead4;
                --accent-2: #60a5fa;
            }}
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                min-height: 100vh;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                color: var(--text);
                background:
                    radial-gradient(circle at top left, rgba(96, 165, 250, 0.24), transparent 32%),
                    radial-gradient(circle at top right, rgba(94, 234, 212, 0.18), transparent 28%),
                    linear-gradient(180deg, #050b14 0%, var(--bg) 100%);
            }}
            .wrap {{
                max-width: 960px;
                margin: 0 auto;
                padding: 48px 20px 56px;
            }}
            .hero {{
                background: rgba(15, 27, 45, 0.88);
                border: 1px solid var(--panel-border);
                border-radius: 24px;
                padding: 28px;
                box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
            }}
            .badge {{
                display: inline-block;
                padding: 8px 12px;
                border-radius: 999px;
                background: rgba(94, 234, 212, 0.12);
                color: var(--accent);
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }}
            h1 {{
                margin: 18px 0 12px;
                font-size: clamp(32px, 5vw, 52px);
                line-height: 1.05;
            }}
            p {{
                color: var(--muted);
                font-size: 18px;
                line-height: 1.65;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 18px;
                margin-top: 26px;
            }}
            .card {{
                background: rgba(7, 17, 31, 0.84);
                border: 1px solid var(--panel-border);
                border-radius: 18px;
                padding: 20px;
            }}
            .card h2 {{
                margin: 0 0 14px;
                font-size: 18px;
            }}
            .score {{
                font-size: 40px;
                font-weight: 800;
                color: var(--accent);
                margin: 0;
            }}
            ul {{
                margin: 0;
                padding-left: 20px;
                color: var(--muted);
                line-height: 1.7;
            }}
            a {{
                color: var(--accent-2);
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .links {{
                display: flex;
                flex-wrap: wrap;
                gap: 14px;
                margin-top: 22px;
            }}
            .links a {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-height: 44px;
                padding: 0 16px;
                border-radius: 999px;
                background: rgba(96, 165, 250, 0.14);
                border: 1px solid rgba(96, 165, 250, 0.28);
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <main class="wrap">
            <section class="hero">
                <span class="badge">OpenEnv Submission Ready</span>
                <h1>Customer Support Env</h1>
                <p>
                    A realistic Tier-1 customer support environment for agent evaluation.
                    Agents must retrieve policy context, query internal records, decide when refunds
                    are allowed, and finish with the correct customer-facing resolution.
                </p>
                <div class="grid">
                    <article class="card">
                        <h2>Current Evaluated Score</h2>
                        <p class="score">{average:.2f}</p>
                        <ul>{score_items}</ul>
                    </article>
                    <article class="card">
                        <h2>Task Coverage</h2>
                        <ul>{task_items}</ul>
                    </article>
                </div>
                <div class="links">
                    <a href="/docs">API Docs</a>
                    <a href="/tasks">Tasks JSON</a>
                    <a href="/grader">Grader JSON</a>
                    <a href="/health">Health Check</a>
                </div>
            </section>
        </main>
    </body>
    </html>
    """

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
