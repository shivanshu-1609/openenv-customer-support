import os
import asyncio
from openai import AsyncOpenAI
import json

from client import SupportEnv
from models import SupportAction

SYSTEM_PROMPT = """
You are a Customer Support Agent. You have access to four actions. Follow the JSON schema strictly.
Action Types: 'search_kb', 'query_db', 'issue_refund', 'reply'.

Fields:
- action_type (string): The selected action type.
- query (string): Optional search string for search_kb or query_db.
- order_id (string): Optional order ID string for issue_refund.
- message (string): Optional reply string for reply.

Your goal is to solve the ticket in as few steps as possible. Emit ONE JSON object per turn representing your action.
"""

async def run_episode(env: SupportEnv, oai_client: AsyncOpenAI):
    result = await env.reset()
    if not result:
        return 0.0
    obs = result.observation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"New Ticket: {obs.ticket_text}"}
    ]
    print(f"--- STARTING EPISODE ---")
    print(f"Ticket: {obs.ticket_text}")
    
    score = 0.0
    for step in range(10):
        if result.done:
            break
            
        messages.append({"role": "user", "content": f"Feedback: {obs.last_action_feedback}"})
        
        try:
            response = await oai_client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=messages,
                max_tokens=200
            )
            content = response.choices[0].message.content
            print(f"AI Selected Action: {content}")
            action_data = json.loads(content)
            action = SupportAction(**action_data)
        except Exception as e:
            print(f"AI Formatting Error: {e} with content: {content}")
            action = SupportAction(action_type="reply", message="Error generating action.")
            content = json.dumps(action.model_dump(exclude_none=True))
            
        messages.append({"role": "assistant", "content": content})
        result = await env.step(action)
        obs = result.observation
        score += getattr(obs, "reward", 0.0)
        
    score = max(0.0, min(1.0, score))
    print(f"--- EPISODE FINISHED | SCORE: {score} ---")
    return score

async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required to run baseline.py.")
        return

    oai_client = AsyncOpenAI()
    scores = []
    
    try:
        async with SupportEnv(base_url="http://localhost:8000") as env:
            for i in range(5):
                score = await run_episode(env, oai_client)
                scores.append(score)
    except Exception as e:
        print(f"Connection to Env failed. Error: {e}")
        return
        
    print(f"Final Average Score: {sum(scores)/max(len(scores), 1)}")

if __name__ == "__main__":
    asyncio.run(main())
