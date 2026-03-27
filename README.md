# Meta Hackathon Round 1: Customer Support Environment

A real-world OpenEnv environment simulating a Tier 1 Customer Support Agent. The agent interacts with a mocked knowledge base and order database to resolve customer tickets (ranging from password resets to complex refund policy verifications).

## Domains & Task Types
1. **Easy:** Password Reset (Information Retrieval via KB Search)
2. **Medium:** Lost Order Refund (State Mutation via DB Search and Action)
3. **Hard:** Policy-based Refund Denial (Conditional Logic via DB and KB Search)

## Setup and Usage

### 1. Installation
Install the environment from the repository:
```bash
pip install -e .
```

### 2. Run the Environment Server Locally 
The environment is powered by FastAPI and Uvicorn.
```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```
Or you can use the standard OpenEnv run command:
```bash
openenv serve
```

### 3. Run the Baseline Agent
This environment comes with a reproducible baseline script using the OpenAI client. Wait for the server to load, export your API key, and run the evaluation:
```bash
export OPENAI_API_KEY="sk-..."
python baseline.py
```

## Action & Observation Spaces
### Action (`SupportAction`)
A JSON-serializable `Pydantic` model with the following fields:
- `action_type` (str): One of `'search_kb'`, `'query_db'`, `'issue_refund'`, `'reply'`.
- `query` (str, optional): Search or DB query parameter.
- `order_id` (str, optional): The ID of the order to refund.
- `message` (str, optional): Text to send to the customer.

### Observation (`SupportObservation`)
- `ticket_id` (str): Current ticket identifier.
- `ticket_text` (str): Full text of the customer inquiry.
- `last_action_feedback` (str): Result of the previous action (e.g., KB results or DB results).
- `reward` (float): Accumulated or step reward.
- `done` (bool): Whether the episode is finished.

## Agent Graders & Rewards
Grading provides a dense reward signal between `-0.5` and `+1.0`.
- Valid intermediate DB/KB searches yield partial progress rewards (`+0.2`).
- Invalid or destructive commands yield minor penalties (`-0.1`).
- Resolving a ticket correctly gives a major completion bonus (`+0.8` to `+1.0`).
- The grader ensures that bounds logic strictly clamps cumulative total episode score between `0.0` and `1.0`.

## Docker and Deployment
Deploys natively to Hugging Face Spaces using the included `Dockerfile`.

```bash
docker build -t openenv-support:latest -f server/Dockerfile .
docker run -p 8000:8000 openenv-support:latest
```
