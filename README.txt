TICKET TRIAGE AGENT – BUILT FROM SCRATCH

This project implements an end-to-end ticket triage agent system, built without managed services or orchestration frameworks to gain deeper understanding.

The goal is to showcase:

• LLM-based planning best practices
• Agent/executor loops
• Agent runtime guardrails
• Variable-based workflow state
• Deterministic tool calling and plan execution in code
• Agent-level evaluation (correctness, cost, latency)
• Model comparison across OpenAI models

------------------------------------------------------------------

The system contains three major parts:

- Planner Agent (LLM)

- Executor (deterministic Python)

- Evaluator (agent-level eval harness)

------------------------------------------------------------------

PLANNER AGENT (LLM-DRIVEN)

The planner receives a raw support ticket and returns a structured sequence of tool calls in JSON format.

The planner prompt defines:

• Persona and instructions
• Output schema (JSON-only)
• Allowed tool names
• Each tool’s input and output signature, descriptions
• Variable-based state ($ticket, $summary, $priority)
• Safety and formatting rules

Example planner output:

{
"steps": [
{ "id": 1, "action": "classify_ticket", "inputs": { "text": "$ticket" } },
{ "id": 2, "action": "extract_summary", "inputs": { "text": "$ticket" } },
{ "id": 3, "action": "calculate_priority", "inputs": { "summary": "$summary" } },
{ "id": 4, "action": "lookup_known_issues", "inputs": { "summary": "$summary" } }
],
"ticket_text": "The API returns 500 errors when uploading CSV files in production for EU customers."
}

------------------------------------------------------------------

EXECUTOR (DETERMINISTIC PYTHON)

The executor is not an agent. It is a deterministic workflow runner that:

• Loads the JSON plan
• Resolves $variables using a shared context dictionary
• Calls Python tool functions
• Stores each tool’s output back into the context
• Logs each execution step

Example tool output:

{ "summary": "CSV upload failure in EU production" }

This becomes available for future steps as $summary.

------------------------------------------------------------------

EVALUATOR (AGENT-LEVEL EVALS)

The evaluation harness measures:

A. Plan Correctness (Rule-Based)
• We’re not testing what steps the plan contains (requiring ground truth, deterministic), but whether the plan adheres to the system designed 
• Valid JSON
• Allowed actions only
• Correct number of steps
• Proper use of variables
• No hallucinated fields

B. Execution Correctness
• Tools executed in the correct order as the plan, validated by logs 
• Context updated correctly (summary, priority, related_issue)

C. Performance
• End-to-end latency
• Cost based on token usage and model pricing

Why agent evals are different:
Agent workflows can have complex branching logic, so evals aren't trying to match plan steps exactly from ground truth.
Instead, I'm testing whether the plan adheres to designed system by checking if the end result matches expected variable state. For example, was a notification dispatched for a high priority ticket. 

Recommended number of evals:

• 10 → MVP
• 50 → Pre-launch
• 100–200 → Production

------------------------------------------------------------------

EVAL RESULTS

Model: gpt-4.1
• Accuracy: 0.96
• Latency: 1.6 sec
• Cost: $0.004
• Best general-purpose model

Model: gpt-4.1-mini
• Accuracy: 0.96
• Latency: 2.3 sec
• Cost: $0.001
• Best cost efficiency

Model: o3-mini
• Accuracy: 0.96
• Latency: 6.4 sec
• Cost: $0.016
• Not ideal for this workflow

Model: o1
• Accuracy: 0.96
• Latency: 4.5 sec
• Cost: $0.097
• Overkill for structured planning

Summary:
Reasoning models do not improve accuracy for structured tool workflows, but cost significantly more.
The best production choices are gpt-4.1 and gpt-4.1-mini.
