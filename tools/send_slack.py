def send_slack_notification(recipient: str, message: str) -> dict:
    """
    Mock Slack sender.
    Instead of actually calling Slack, we mimic it.
    """
    print(f"[MOCK SLACK] Sent to {recipient}: {message}")
    return {"slack_sent": True}