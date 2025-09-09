import tempfile
from git import Repo

def clone_repo(url: str, branch: str = "main") -> str:
    tmpdir = tempfile.mkdtemp(prefix="repo_")
    Repo.clone_from(url, tmpdir, branch=branch, depth=1)
    return tmpdir
