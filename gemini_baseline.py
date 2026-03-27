import os
import asyncio
import json
from google import genai
from google.genai import types

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

Your goal is to solve the ticket in as few steps as possible. Emit exactly ONE JSON object per turn representing your action.
"""

async def run_episode(env: SupportEnv, client: genai.Client):
    result = await env.reset()
    if not result:
        return 0.0
    obs = result.observation
    
    history = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"New Ticket: {obs.ticket_text}")])
    ]
    
    print(f"--- STARTING EPISODE ---")
    print(f"Ticket: {obs.ticket_text}")
    
    score = 0.0
    for step in range(10):
        if result.done:
            break
            
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            content = response.text
            print(f"AI Action: {content.strip()}")
            action_data = json.loads(content)
            action = SupportAction(**action_data)
        except Exception as e:
            print(f"AI Error: {e}")
            action = SupportAction(action_type="reply", message="Error generating action.")
            content = json.dumps(action.model_dump(exclude_none=True))
            
        history.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
        result = await env.step(action)
        obs = result.observation
        score += getattr(obs, "reward", 0.0)
        
        history.append(types.Content(role="user", parts=[types.Part.from_text(text=f"Feedback: {obs.last_action_feedback}")]))
        
    score = max(0.0, min(1.0, score))
    print(f"--- EPISODE FINISHED | SCORE: {score} ---")
    return score

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found.")
        return

    client = genai.Client(api_key=api_key)
    scores = []
    
    try:
        async with SupportEnv(base_url="http://localhost:8000") as env:
            for i in range(3): 
                score = await run_episode(env, client)
                scores.append(score)
    except Exception as e:
        print(f"Error: {e}")
        return
        
    print(f"Final Average Score: {sum(scores)/max(len(scores), 1)}")

if __name__ == "__main__":
    asyncio.run(main())
