def lookup_known_issues(summary: str) -> dict:
    """
    Mock known-issues lookup.
    In a real production agent, this might do:
    - embeddings search
    - vector store lookup
    - internal database query
    """
    summary_lower = summary.lower()

    if "csv" in summary_lower:
        return {"related_issue": "Known CSV upload regression #1245"}
    if "auth" in summary_lower:
        return {"related_issue": "Frequent auth token expiration issue"}
    
    return {"related_issue": "No known issues found"}