---
title: Customer Support Env
emoji: 🏢
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---
# Customer Support Env

`Customer Support Env` is an OpenEnv environment that simulates a Tier-1 customer support workflow. An agent receives a ticket, uses a small action set to query internal tools, and must finish with the correct customer-facing resolution.

## Why this is a strong OpenEnv task

- It models a real operational workflow instead of a toy game.
- The action space is structured and testable: `search_kb`, `query_db`, `issue_refund`, and `reply`.
- The reward logic is dense enough to guide learning while still enforcing correct end-to-end resolution.
- The task set spans retrieval, tool use, state mutation, and policy reasoning.

## Task suite

1. Password reset via knowledge-base lookup.
2. Lost-order investigation followed by a refund.
3. Subscription refund denial based on policy and purchase age.

## Reward design

- Correct tool usage gives partial reward.
- Invalid database or refund actions are penalized.
- The final reply determines whether the episode is successfully resolved.
- Scores are clipped to the OpenEnv-safe range of `0.0` to `1.0`.

## Submission files

- `Dockerfile`: repo-root deployment entrypoint for Hugging Face Spaces.
- `inference.py`: deterministic submission runner that evaluates all tasks with no API keys.
- `server/app.py`: OpenEnv-compatible FastAPI server.
- `server/support_env_environment.py`: task definitions and grading logic.

## Local usage

```bash
uv sync
uv run server
python inference.py
```

`baseline.py` is an optional OpenAI-powered baseline for manual experimentation. It is not required for submission.

## Repository layout

```text
.
├── Dockerfile
├── inference.py
├── baseline.py
├── client.py
├── models.py
├── openenv.yaml
├── pyproject.toml
└── server/
    ├── app.py
    └── support_env_environment.py
```
