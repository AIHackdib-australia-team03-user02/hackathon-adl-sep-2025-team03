import os

def policy_search(query: str, top: int = 5):
    """Stub: Replace with real Azure Search SDK call. Returns [(title, url_or_id, snippet)]."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index = os.getenv("AZURE_SEARCH_INDEX")
    # TODO: implement real call; for now return empty
    return []
