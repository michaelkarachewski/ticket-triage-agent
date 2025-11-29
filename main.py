from agents.planner import plan_workflow
from agents.executor import execute_plan

if __name__ == "__main__":

    #test planner
    ticket = "The API returns 500 errors when uploading CSV files in production for EU customers."
    plan = plan_workflow(ticket, model="gpt-4.1") 
    print("PLAN:")
    print(plan)

    #test executor 
    execute = execute_plan(plan, ticket)
    print("EXECUTE:")
    print(execute)
# OUTPUT:
# {
#   "ticket_text": "The API returns 500 errors when uploading CSV files in production for EU customers.",
#   "steps": [
#     {
#       "id": 1,
#       "action": "classify_ticket",
#       "inputs": {
#         "text": "$ticket"
#       }
#     },
#     {
#       "id": 2,
#       "action": "extract_summary",
#       "inputs": {
#         "text": "$ticket"
#       }
#     },
#     {
#       "id": 3,
#       "action": "calculate_priority",
#       "inputs": {
#         "summary": "$summary"
#       }
#     },
#     {
#       "id": 4,
#       "action": "lookup_known_issues",
#       "inputs": {
#         "summary": "$summary"
#       }
#     },
#     {
#       "id": 5,
#       "action": "send_slack_notification",
#       "inputs": {
#         "recipient": "oncall-eng",
#         "message": "$summary"
#       }
#     }
#   ]
# }

    