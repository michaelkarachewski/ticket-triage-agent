from tools.classify_ticket import classify_ticket
from tools.extract_summary import extract_summary
from tools.calculate_priority import calculate_priority
from tools.retrieve_docs import lookup_known_issues
from tools.send_slack import send_slack_notification


# Map action names → Python functions
TOOL_REGISTRY = {
    "classify_ticket": classify_ticket,
    "extract_summary": extract_summary,
    "calculate_priority": calculate_priority,
    "lookup_known_issues": lookup_known_issues,
    "send_slack_notification": send_slack_notification,
}


def resolve_value(val, context):
    """
    Resolves "$variable" into context["variable"].
    """
    if isinstance(val, str) and val.startswith("$"):
        key = val[1:]  # strip the "$"
        return context.get(key)
    return val


def resolve_inputs(inputs: dict, context: dict) -> dict:
    """
    Resolves inputs for tools, turning nested "$var" references into real values.
    """
    resolved = {}
    for k, v in inputs.items():
        if isinstance(v, dict):
            resolved[k] = resolve_inputs(v, context)
        else:
            resolved[k] = resolve_value(v, context)
    return resolved

def execute_plan(plan: dict, ticket: str) -> dict:
    """
    Executes a workflow produced by the planner.

    Returns:
    {
        "results": { ...final context... },
        "log": [
            {
                "step": 1,
                "action": "...",
                "inputs": { ... },
                "output": { ... }
            },
            ...
        ]
    }
    """
    # Start execution context with original ticket text
    context = {"ticket": ticket}

    log = []

    for step in plan["steps"]:
        action = step["action"]
        inputs = step["inputs"]

        if action not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {action}")

        tool_fn = TOOL_REGISTRY[action]

        # Resolve "$var" references
        resolved_inputs = resolve_inputs(inputs, context)

        print("CONTEXT:", context)
        print("ACTION:", action)
        # Run the tool
        output = tool_fn(**resolved_inputs) #shorthand for tool_fn(text="The API returns 500 errors...")
        print("OUTPUT:", output)
        print()

        # Store the outputs back into context
        if isinstance(output, dict):
            for key, value in output.items():
                context[key] = value

        # Append detailed logs
        log.append({
            "step": step["id"],
            "action": action,
            "inputs": resolved_inputs,
            "output": output,
        })

    return {
        "results": context,
        "log": log
    }