from autogen import AssistantAgent
from utils.file_io import load_local_texts
from utils.github_io import clone_repo

INGESTION_SYSTEM = (
    "You are IngestionAgent. You fetch/normalise text from local paths or GitHub. "
    "Return a JSON object with keys: 'summary', 'items' where items = list of {path, preview}. "
    "Preview is the first 300 characters of content. Do not invent paths."
)
def make_ingestion_agent(llm_cfg):
    agent = AssistantAgent("ingestion", llm_config=llm_cfg, system_message=INGESTION_SYSTEM)

    @agent.register_for_execution()
    def read_local(paths: list[str]):
        items = []
        for p, text in load_local_texts(paths):
            items.append({"path": p, "preview": text[:300]})
        return {"summary": f"Loaded {len(items)} items", "items": items}

    @agent.register_for_execution()
    def fetch_github(repo_url: str, branch: str = "main", subpaths: list[str] | None = None):
        folder = clone_repo(repo_url, branch)
        targets = [folder] if not subpaths else [f"{folder}/{sp}" for sp in subpaths]
        items = []
        for p, text in load_local_texts(targets):
            items.append({"path": p, "preview": text[:300]})
        return {"summary": f"Loaded {len(items)} items from repo", "items": items}

    return agent
