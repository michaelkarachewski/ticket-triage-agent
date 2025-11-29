def extract_summary(text: str) -> dict:
    """
    Pretend to summarize ticket text.
    In a real system you'd use GPT-4.1 or o3-mini.
    This mock is deterministic.
    """
    if len(text) > 120:
        summary = text[:120] + "..."
    else:
        summary = text

    return {"summary": summary}