---
title: Customer Support Env
emoji: 🏢
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---
# 👨‍💻 Building the "Customer Support Env": A Developer's Process

Hey there! If you're reading this, you are probably checking out my OpenEnv project for the Meta/Hugging Face Hackathon. 

I wanted to build something that felt distinctly "human." While building sandboxes for AI agents (like Llama or ChatGPT) to play in, it's easy to default to simple grid-world games. But real life isn't a board game; it's navigating frustrating refund policies and rigid SQL databases. That's why I built a **Tier-1 Customer Support Simulator**.

## 🧠 The Thought Process

### Why Customer Support?
The Hackathon's biggest penalty is for building "toys." Judges want environments that simulate tasks *humans actually do daily*. 
The workflow of a customer support agent is highly structured:
1. They receive a ticket.
2. They query internal databases (DBs).
3. They look up policies in the Knowledge Base (KB).
4. They perform an action (like a refund) and reply to the user.

This loop maps perfectly to the `Agent -> Action -> Environment -> Observation` pattern.

### Designing the Sandbox (`models.py`)
I didn't want the AI to just chat freely. Using `Pydantic`, I designed `SupportAction` to force the AI to choose from specific buttons: `search_kb`, `query_db`, `issue_refund`, and `reply`. By forcing the model to adhere to these structured JSON APIs, grading its intelligence becomes purely mathematical.

### The Referee Engine & Reward Logic
I wrote the `step()` function to provide dense, incremental rewards bounded strictly between `0.0` and `1.0`. 
- Successfully finding documentation in the KB? *+0.2 points.*
- Querying a database with invalid strings? *-0.1 points.*
- Successfully resolving the ticket? *+0.8 points.*
- Getting stuck in an infinite loop? *-0.5 points (and forced episode termination).*

If a small AI model queries the database with a full English sentence (`"query": "delivery_date for order #12345"`) instead of just the strict integer ID (`"12345"`), it gets penalized! Building a strict environment isn't a bug; it's a feature. If an AI isn't smart enough to extract the exact integer ID to pass into a mock SQL lookup, it *should* fail. 

***

# 🛠️ Setup & Installation Instructions

This environment strictly adheres to the OpenEnv API specifications and is completely ready for automated multi-mode deployment.

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
Or you can use the standard OpenEnv script:
```bash
openenv serve
```

### 3. Run the Baseline Agent
This environment comes with a reproducible baseline script. Wait for the server to load, export your API key, and run the evaluation:
```bash
export OPENAI_API_KEY="sk-..."
python baseline.py
```
*(There is also an included `gemini_baseline.py` script provided natively in the repo to run testing completely for free using Google's generative-ai SDK).*

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

## Agent Graders & Tasks
1. **Easy:** Password Reset (Information Retrieval via KB Search)
2. **Medium:** Lost Order Refund (State Mutation via DB Search and Action)
3. **Hard:** Policy-based Refund Denial (Conditional Math Logic via DB and KB Search)

## Docker Deployments
Deploys natively to Hugging Face Spaces using the included `Dockerfile`.

```bash
docker build -t openenv-support:latest -f server/Dockerfile .
docker run -p 8000:8000 openenv-support:latest
```
