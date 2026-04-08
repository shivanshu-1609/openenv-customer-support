---
title: Customer Support Env
emoji: 🏢
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---
# Customer Support Env

`Customer Support Env` is an OpenEnv environment that simulates a realistic Tier-1 customer support workflow. Agents must gather the right evidence, respect policy constraints, avoid unsafe refunds, and send a customer-facing resolution only after the operational checks are complete.

## Why this is judge-friendly

- It models a real operations workflow instead of a toy game.
- Success depends on correct sequencing, not just keyword matching.
- Irreversible actions such as refunds are safety-gated behind evidence checks.
- The reward logic distinguishes safe process from lucky final answers.

## Task suite

1. Password reset via KB lookup.
2. Lost order investigation followed by refund issuance.
3. Subscription refund denial outside the 14-day window.
4. Damaged-item refund that requires both order verification and policy lookup.
5. Address-change request after shipment that must be safely declined.

## Action space

Agents operate through four structured actions:

- `search_kb`
- `query_db`
- `issue_refund`
- `reply`

This keeps the interface simple while still forcing the model to reason about workflow order and policy compliance.

## Grading logic

The grader rewards evidence-first behavior:

- KB lookups earn credit only when the query matches the right policy topic.
- DB lookups earn credit only when the correct order ID is extracted from the ticket.
- Refunds are penalized if they happen before evidence is gathered or when policy forbids them.
- Final replies are rewarded only when the required evidence has been collected and the resolution message is correct.

This means an agent cannot brute-force a good score by replying early or blindly issuing refunds.

## Example workflows

### Safe refund

```text
query_db -> search_kb -> issue_refund -> reply
```

### Safe denial

```text
query_db -> search_kb -> reply
```

### Unsafe pattern that is penalized

```text
issue_refund -> reply
```

## Submission behavior

- `inference.py` uses the injected LiteLLM/OpenAI-compatible proxy variables.
- Structured stdout follows the required `[START]`, `[STEP]`, and `[END]` format.
- Reported task scores stay strictly inside `(0, 1)` for validator compliance.

## Local usage

```bash
uv sync
uv run server
python inference.py
```

## Repository layout

```text
.
├── Dockerfile
├── inference.py
├── client.py
├── models.py
├── openenv.yaml
├── pyproject.toml
├── submission_agent.py
└── server/
    ├── app.py
    └── support_env_environment.py
```
