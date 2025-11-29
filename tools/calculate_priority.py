def calculate_priority(summary: str) -> dict:
    """
    Mock priority calculator.
    """
    lower = summary.lower()

    if "production" in lower or "500" in lower or "down" in lower:
        priority = "critical"
    elif "error" in lower:
        priority = "high"
    else:
        priority = "normal"

    return {"priority": priority}