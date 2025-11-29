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
    Includes token usage needed for cost evaluation.
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

    # Extract the main message
    message = response.choices[0].message

    # Prefer parsed JSON (because response_format=json_object)
    if hasattr(message, "parsed") and message.parsed is not None:
        plan = message.parsed
    else:
        import json
        plan = json.loads(message.content)

    # Attach original ticket text (needed for $ticket resolution)
    plan["ticket_text"] = ticket_text

    # ⭐ ADD THIS: attach usage metadata
    # The evaluator will read this to compute cost.
    usage = response.usage
    plan["_usage"] = {
        "prompt": usage.prompt_tokens,
        "completion": usage.completion_tokens,
        "total": usage.total_tokens,
    }

    return plan
