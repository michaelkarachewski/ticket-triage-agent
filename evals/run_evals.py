import json
import time
from typing import Dict, Any, List

from agents.planner import plan_workflow
from agents.executor import execute_plan, TOOL_REGISTRY

# ---- Pricing (USD per 1K tokens) ----
# From https://openai.com/api/pricing/

MODEL_PRICES = {
    "gpt-4.1": {
        "prompt": 0.003,
        "completion": 0.012
    },
    "gpt-4.1-mini": {
        "prompt": 0.0008,
        "completion": 0.0032,
    },
    "o3-mini": {
        "prompt": 0.004,
        "completion": 0.016,
    },
    "o1": {
        "prompt": 0.015,
        "completion": 0.12,
    },
}


# ---- Helpers for scoring booleans ----

def score_bool_dict(d: Dict[str, Any]) -> float:
    """
    Take a dict of name -> bool and return fraction that are True.
    Ignores non-bool values.
    """
    bool_vals = [v for v in d.values() if isinstance(v, bool)]
    if not bool_vals:
        return 0.0
    return sum(1 for v in bool_vals if v) / len(bool_vals)


# ---- Plan validation (no ground truth needed) ----

ALLOWED_VARS = {"ticket", "summary", "priority", "category", "related_issue"}


def _iter_values_recursively(obj):
    """Yield all leaf values from a nested dict."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_values_recursively(v)
    else:
        yield obj


def validate_plan(plan: Dict[str, Any]) -> Dict[str, bool]:
    findings: Dict[str, bool] = {}

    steps = plan.get("steps")
    findings["has_steps"] = isinstance(steps, list)

    if not isinstance(steps, list) or not steps:
        # If no steps, most other checks are meaningless
        findings["step_count_valid"] = False
        findings["starts_with_classify"] = False
        findings["only_allowed_actions"] = False
        findings["valid_step_schema"] = False
        findings["valid_variable_refs"] = False
        return findings

    # 2–5 steps
    findings["step_count_valid"] = 2 <= len(steps) <= 5

    # First step must be classify_ticket
    findings["starts_with_classify"] = (steps[0].get("action") == "classify_ticket")

    # Only allowed actions from TOOL_REGISTRY
    allowed_actions = set(TOOL_REGISTRY.keys())
    findings["only_allowed_actions"] = all(
        step.get("action") in allowed_actions for step in steps
    )

    # Simple schema check
    allowed_step_keys = {"id", "action", "inputs"}
    findings["valid_step_schema"] = all(
        isinstance(step, dict) and set(step.keys()).issubset(allowed_step_keys)
        for step in steps
    )

    # Variable references must be from ALLOWED_VARS when using "$var"
    valid_var_refs = True
    for step in steps:
        inputs = step.get("inputs", {})
        for val in _iter_values_recursively(inputs):
            if isinstance(val, str) and val.startswith("$"):
                var_name = val[1:]
                if var_name not in ALLOWED_VARS:
                    valid_var_refs = False
                    break
        if not valid_var_refs:
            break
    findings["valid_variable_refs"] = valid_var_refs

    return findings


# ---- Execution log validation (no ground truth needed) ----

REQUIRED_OUTPUT_KEYS = {
    "classify_ticket": ["category"],
    "extract_summary": ["summary"],
    "calculate_priority": ["priority"],
    "lookup_known_issues": ["related_issue"],
    "send_slack_notification": ["slack_sent"],
}


def validate_execution(plan: Dict[str, Any], log: List[Dict[str, Any]]) -> Dict[str, bool]:
    findings: Dict[str, bool] = {}

    steps = plan.get("steps", [])
    findings["all_steps_executed"] = len(log) == len(steps)

    # Actions follow plan order
    if len(log) == len(steps):
        findings["correct_order"] = all(
            log[i].get("action") == steps[i].get("action") for i in range(len(steps))
        )
    else:
        findings["correct_order"] = False

    # Outputs are dicts and not None
    findings["outputs_are_dicts"] = all(
        isinstance(entry.get("output"), dict) for entry in log
    )

    findings["no_none_outputs"] = all(
        entry.get("output") is not None for entry in log
    )

    # All tools in log are allowed
    allowed_actions = set(TOOL_REGISTRY.keys())
    findings["all_tools_allowed"] = all(
        entry.get("action") in allowed_actions for entry in log
    )

    # Required keys present in each tool output
    required_keys_ok = True
    for entry in log:
        action = entry.get("action")
        output = entry.get("output", {})
        if action in REQUIRED_OUTPUT_KEYS:
            for key in REQUIRED_OUTPUT_KEYS[action]:
                if key not in output:
                    required_keys_ok = False
                    break
        if not required_keys_ok:
            break
    findings["required_keys_present"] = required_keys_ok

    return findings


# ---- Functional correctness (requires expected labels) ----

def validate_context(final_ctx: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    q: Dict[str, Any] = {}

    # Priority correctness
    q["priority_expected"] = expected.get("priority")
    q["priority_got"] = final_ctx.get("priority")
    q["priority_correct"] = (q["priority_got"] == q["priority_expected"])

    # Slack alert correctness
    exp_alert = expected.get("should_alert")
    got_alert = final_ctx.get("slack_sent", False)
    q["alert_expected"] = exp_alert
    q["alert_got"] = got_alert
    q["alert_correct"] = (got_alert == exp_alert)

    # Known issue correctness (presence/absence)
    exp_match = expected.get("should_match_known_issue")
    got_match = final_ctx.get("related_issue") is not None
    q["known_issue_expected"] = exp_match
    q["known_issue_got"] = got_match
    q["known_issue_correct"] = (got_match == exp_match)

    # Overall functional score
    bool_checks = [
        q["priority_correct"],
        q["alert_correct"],
        q["known_issue_correct"],
    ]
    q["functional_score"] = sum(1 for v in bool_checks if v) / len(bool_checks)

    return q


# ---- Single-case runner ----

def evaluate_case(case: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    ticket = case["ticket"]
    expected = case.get("expected", {})
    name = case.get("name", ticket[:40] + "...")

    result: Dict[str, Any] = {
        "name": name,
        "model": model_name,
        "ticket": ticket,
    }

    # 1. Planner
    t0 = time.time()
    plan = plan_workflow(ticket, model=model_name)
    t1 = time.time()
    result["planner_latency_sec"] = t1 - t0

    # ---- Cost evaluation ----
    usage = plan.get("_usage", {})
    prompt_tokens = usage.get("prompt", 0)
    completion_tokens = usage.get("completion", 0)
    total_tokens = usage.get("total", prompt_tokens + completion_tokens)

    # Lookup pricing for this model
    pricing = MODEL_PRICES.get(model_name, {"prompt": 0.0, "completion": 0.0})

    prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * pricing["completion"]
    total_cost = prompt_cost + completion_cost

    result["cost"] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_cost_usd": prompt_cost,
        "completion_cost_usd": completion_cost,
        "total_cost_usd": total_cost,
    }

    # Plan validation
    plan_eval = validate_plan(plan)
    result["plan_eval"] = plan_eval
    result["plan_eval_score"] = score_bool_dict(plan_eval)

    # 2. Executor
    t2 = time.time()
    exec_output = execute_plan(plan, ticket)
    t3 = time.time()
    result["executor_latency_sec"] = t3 - t2

    final_ctx = exec_output["results"]
    log = exec_output["log"]

    # Execution validation
    exec_eval = validate_execution(plan, log)
    result["execution_eval"] = exec_eval
    result["execution_eval_score"] = score_bool_dict(exec_eval)

    # 3. Functional correctness (uses expected labels)
    func_eval = validate_context(final_ctx, expected)
    result["functional_eval"] = func_eval

    # Aggregate overall score (simple average of three scores)
    overall_score = (
        result["plan_eval_score"]
        + result["execution_eval_score"]
        + func_eval["functional_score"]
    ) / 3.0
    result["overall_score"] = overall_score

    return result


# ---- Running across all cases & models ----

def run_all_for_model(model_name: str) -> List[Dict[str, Any]]:
    with open("evals/test_cases.json") as f:
        cases = json.load(f)

    results = []
    for case in cases:
        print(f"\n=== Evaluating case '{case.get('name', case['ticket'][:40])}' with model {model_name} ===")
        r = evaluate_case(case, model_name)
        results.append(r)
        print(json.dumps(r, indent=2))
    return results


def compare_models(models: List[str]) -> None:
    summary: Dict[str, Any] = {}

    for m in models:
        print(f"\n\n##### Running evals for model: {m} #####")
        results = run_all_for_model(m)
        summary[m] = results

    print("\n\n===== MODEL COMPARISON SUMMARY =====")
    for m, rs in summary.items():
        if not rs:
            continue
        avg_overall = sum(r["overall_score"] for r in rs) / len(rs)
        avg_latency = sum(
            r["planner_latency_sec"] + r["executor_latency_sec"] for r in rs
        ) / len(rs)
        print(f"\nModel: {m}")
        print(f"  Avg overall score: {avg_overall:.2f}")
        print(f"  Avg end-to-end latency: {avg_latency:.2f} sec")
        avg_cost = sum(
            r["cost"]["total_cost_usd"] for r in rs
        ) / len(rs)

        print(f"  Avg cost per run: ${avg_cost:.6f}")



if __name__ == "__main__":
    # You can tweak this list to compare different planner models.
    compare_models(["gpt-4.1", "gpt-4.1-mini", "o3-mini", "o1"])
    
