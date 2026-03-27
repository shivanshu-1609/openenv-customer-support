# Building the "Customer Support Env": A Developer's Process

Hey there! If you're reading this, you are probably taking a look at how I put together this OpenEnv project. Honestly, I wanted to build something that felt distinctly "human." While building sandboxes for AI agents like ChatGPT or Llama to play in, it's easy to default to simple grid-world games. But real life isn't a game of chess; it's navigating frustrating refund policies and poorly written knowledge-base articles.

So, I decided to build a **Tier 1 Customer Support Simulator**. 

Here’s a breakdown of the thinking process behind the project, how I wired it up, and the challenges I solved along the way.

## Why Customer Support?
When I looked at the Hackathon's criteria, the biggest penalty was for building "toys." Meta and Hugging Face want environments that simulate tasks *humans actually do daily*. 
The workflow of a customer support agent is highly structured yet heavily reliant on context:
1. They receive a ticket.
2. They query internal databases (DBs).
3. They look up policies in the Knowledge Base (KB).
4. They make a final decision, execute an action (like a refund), and reply to the user.

This loop maps perfectly to the `Agent -> Action -> Environment -> Observation` paradigm in Reinforcement Learning.

## Step 1: Designing the Sandbox Models (`models.py`)
I didn't want the AI to just chat freely. If an AI is going to act like a real agent, it needs to be constrained by strict internal APIs. 
Using `Pydantic`, I designed `SupportAction` to force the AI to choose from specific buttons:
- `search_kb`
- `query_db`
- `issue_refund`
- `reply`

By forcing the model to adhere to these structured JSON actions, evaluating its intelligence becomes entirely mathematical rather than subjective.

## Step 2: Coding the Referee Engine (`support_env_environment.py`)
This was the most critical part: writing the Python class that grades the AI. 
I built three distinct tasks representing three difficulty tiers:
1. **Easy Tier:** A simple password reset. The agent just hits the KB and sends a link. 
2. **Medium Tier:** A missing order check. The agent has to query the database, parse the JSON response "Lost in Transit", and issue a refund.
3. **Hard Tier:** A refund request by an angry customer who purchased his membership 20 days ago. The agent has to lookup the company policy (14-day limit), calculate that 20 is greater than 14, and politely deny the refund despite the customer's aggression.

### The Reward Shaping Philosophy
If you build an environment that only gives a reward at the very end (sparse rewards), frontier models might struggle to learn the intermediate steps. I wrote the `step()` function to provide dense, incremental rewards:
- Successfully finding documentation in the KB? *+0.2 points.*
- Querying a non-existent database record? *-0.1 points.*
- Successfully resolving the ticket? *+0.8 points.*
- Getting stuck in an infinite loop? *-0.5 points (and forced episode termination).*

This ensures that the score (clamped strictly between 0.0 and 1.0) mathematically represents *exactly* how well the AI diagnosed the issue.

## Step 3: API Endpoints and OpenEnv Validation (`app.py`)
OpenEnv uses FastAPI under the hood to manage WebSocket connections so multiple AI agents can test simultaneously. I extended the base `app.py` wrapper to inject custom REST endpoints (`/grader`, `/baseline`, `/tasks`) as required by the hackathon submission portal. 

One funny quirk I ran into was that the OpenEnv `validate` CLI tool used a strict regex parser to check for a `main()` function string. I had to format the AST of `app.py` in a very specific way just to satisfy the linter, but it was a great learning experience in dealing with automated validation pipelines!

## Step 4: Testing the Baselines
Finally, to prove that this sandbox actually works, I wrote two baseline scripts (`baseline.py` for OpenAI and `gemini_baseline.py` using Google's generative-ai SDK). 
When testing an early version of the medium task, I noticed the Gemini agent was querying the DB with complete English sentences (`"delivery_date for order #12345"`) instead of just the exact `order_id` string. The environment strictly penalized it for bad formatting and awarded a 0.0!

This was the "aha!" moment. Building a strict environment isn't a bug; it's a feature. If an AI isn't smart enough to extract the exact integer ID to pass into a mock SQL lookup, it *should* fail. 

## Final Thoughts
I'm incredibly proud of how this turned out. It's clean, robust, and handles edge cases perfectly without needing massive external dependencies. The code is heavily annotated, so feel free to peek into `support_env_environment.py` if you want to see exactly how the grading logic operates under the hood!
