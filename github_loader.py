"""
github_loader.py
Fetches files from a GitHub repository via the GitHub API or raw URLs.
Returns a list of Document dicts: {content, metadata}.
"""

import os
import re
import base64
from typing import List, Optional
import requests


def _parse_repo_url(url: str):
    """Extract owner and repo name from a GitHub URL."""
    url = url.strip().rstrip("/")
    # Handle various URL formats
    patterns = [
        r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$",
        r"github\.com/([^/]+)/([^/]+)/tree/[^/]+/?$",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1), m.group(2)
    raise ValueError(f"Cannot parse GitHub URL: {url}")


def load_github_repo(
    repo_url: str,
    extensions: List[str],
    max_files: int = 50,
    github_token: Optional[str] = None,
) -> List[dict]:
    """
    Loads files from a GitHub repo.

    Returns:
        List of {"content": str, "metadata": {"source": str, "path": str}}
    """
    owner, repo = _parse_repo_url(repo_url)

    headers = {"Accept": "application/vnd.github.v3+json"}
    token = github_token or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    # Get the default branch
    repo_info = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        timeout=15,
    )
    repo_info.raise_for_status()
    default_branch = repo_info.json().get("default_branch", "main")

    # Get the full file tree (recursive)
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
    tree_resp = requests.get(tree_url, headers=headers, timeout=30)
    tree_resp.raise_for_status()
    tree = tree_resp.json().get("tree", [])

    # Filter by extension and type=blob
    ext_set = set(extensions)
    blobs = [
        item for item in tree
        if item["type"] == "blob"
        and any(item["path"].endswith(ext) for ext in ext_set)
        and item.get("size", 0) < 200_000  # skip huge files
    ][:max_files]

    if not blobs:
        raise ValueError(
            f"No files with extensions {extensions} found in {owner}/{repo}. "
            "Try adding more file types."
        )

    documents = []
    for item in blobs:
        path = item["path"]
        sha  = item["sha"]
        try:
            blob_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{sha}",
                headers=headers,
                timeout=15,
            )
            blob_resp.raise_for_status()
            blob_data = blob_resp.json()
            encoding  = blob_data.get("encoding", "")
            raw_content = blob_data.get("content", "")

            if encoding == "base64":
                text = base64.b64decode(raw_content).decode("utf-8", errors="replace")
            else:
                text = raw_content

            if text.strip():
                documents.append({
                    "content": text,
                    "metadata": {
                        "source": f"https://github.com/{owner}/{repo}/blob/{default_branch}/{path}",
                        "path": path,
                        "repo": f"{owner}/{repo}",
                    },
                })
        except Exception:
            # Skip files that fail to decode
            continue

    if not documents:
        raise ValueError("No readable documents found in the repository.")

    return documents
