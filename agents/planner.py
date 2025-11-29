from pathlib import Path
from openai import OpenAI
from config.settings import OPENAI_API_KEY #automatically runs when imported


client = OpenAI()

PLANNER_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_prompt.txt"

def load_planner_prompt() -> str:
    return PLANNER_PROMPT_PATH.read_text()

def plan_workflow(ticket_text: str, model: str = "gpt-4.1") -> dict:
    """
    Calls an LLM to produce a JSON workflow plan for the given ticket.
    """
    system_prompt = load_planner_prompt()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ticket_text},
        ],
        response_format={"type": "json_object"}
    )

    # Depending on SDK, parsed JSON may be in message content or a helper field.
    # Here we assume 'message.parsed' exists when using response_format=json_object.
    message = response.choices[0].message
    # Prefer parsed JSON if available (because response_format=json_object)
    if hasattr(message, "parsed") and message.parsed is not None:
        plan = message.parsed
    else:
        import json
        plan = json.loads(message.content)

    # ⭐ ADD THIS: attach original ticket so executor can resolve $ticket
    plan["ticket_text"] = ticket_text

    return plan