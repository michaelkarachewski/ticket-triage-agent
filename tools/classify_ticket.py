def classify_ticket(text: str) -> dict:
    """
    Very simple mock classifier.
    In production this could use embeddings, heuristics, or an LLM.
    Here we hardcode simple rules.
    """
    text_lower = text.lower()

    if "error" in text_lower or "500" in text_lower or "fail" in text_lower:
        category = "bug"
    elif "feature" in text_lower or "request" in text_lower:
        category = "feature_request"
    else:
        category = "general_inquiry"

    return {"category": category}