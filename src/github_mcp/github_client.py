"""GitHub REST API client functions (async, httpx-based)."""

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from github_mcp.cache import cached

GITHUB_API_BASE = "https://api.github.com"


def _get_headers() -> dict[str, str]:
    """Build authorization headers from the GITHUB_TOKEN env var."""
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-dev-tools-mcp/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _make_request(
    method: str, path: str, *, raw: bool = False, **kwargs: Any
) -> dict | list | str:
    """Central request dispatcher with error handling.

    Handles: 401 (bad token), 403 (rate limit / forbidden),
    404 (not found), and network errors.
    Set raw=True to return response.text instead of JSON (for diffs, READMEs).
    Raises ValueError with a human-readable message on failure.
    """
    try:
        async with httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers=_get_headers(),
            timeout=30.0,
        ) as client:
            response = await client.request(method, path, **kwargs)
    except httpx.ConnectError:
        raise ValueError("Could not connect to GitHub API. Check your network connection.")
    except httpx.TimeoutException:
        raise ValueError("GitHub API request timed out after 30 seconds.")

    if response.status_code in range(200, 300):
        if raw:
            return response.text
        return response.json()

    if response.status_code == 401:
        raise ValueError("Authentication failed. Check your GITHUB_TOKEN.")

    if response.status_code == 403:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            reset_ts = int(response.headers.get("X-RateLimit-Reset", "0"))
            reset_time = datetime.fromtimestamp(reset_ts, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
            raise ValueError(f"GitHub API rate limit exceeded. Resets at {reset_time}.")
        raise ValueError("Access forbidden for this resource.")

    if response.status_code == 404:
        raise ValueError(f"Not found: {path}")

    raise ValueError(
        f"GitHub API error {response.status_code}: {response.text[:200]}"
    )


@cached(ttl=300)  # 5 minutes
async def get_repo_info(owner: str, repo: str) -> dict:
    """Fetch key metadata for a GitHub repository.

    Returns a dict with: full_name, description, language, stars, forks,
    open_issues, last_push, default_branch, url.
    """
    data = await _make_request("GET", f"/repos/{owner}/{repo}")
    return {
        "full_name": data["full_name"],
        "description": data.get("description") or "No description",
        "language": data.get("language") or "Not specified",
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "last_push": data["pushed_at"],
        "default_branch": data["default_branch"],
        "url": data["html_url"],
    }


@cached(ttl=120)  # 2 minutes
async def list_pull_requests(
    owner: str, repo: str, state: str = "open"
) -> list[dict]:
    """List pull requests for a repository, filtered by state.

    Args:
        owner: Repository owner (user or org).
        repo: Repository name.
        state: One of 'open', 'closed', or 'all'. Defaults to 'open'.

    Returns a list of dicts with: number, title, author, state,
    created_at, updated_at, draft, url.
    """
    if state not in ("open", "closed", "all"):
        raise ValueError(f"Invalid state '{state}'. Must be 'open', 'closed', or 'all'.")

    data = await _make_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls",
        params={"state": state, "per_page": 30},
    )
    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "state": pr["state"],
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"],
            "draft": pr.get("draft", False),
            "url": pr["html_url"],
        }
        for pr in data
    ]


async def create_github_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
) -> dict:
    """Create a new issue in a GitHub repository.

    Requires a GITHUB_TOKEN with 'repo' scope.

    Returns a dict with: number, title, url, state.
    """
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    data = await _make_request(
        "POST",
        f"/repos/{owner}/{repo}/issues",
        json=payload,
    )
    return {
        "number": data["number"],
        "title": data["title"],
        "url": data["html_url"],
        "state": data["state"],
    }


@cached(ttl=120)  # 2 min
async def list_issues(
    owner: str, repo: str, state: str = "open", labels: str | None = None
) -> list[dict]:
    """List issues for a repository, excluding pull requests.

    Args:
        owner: Repository owner (user or org).
        repo: Repository name.
        state: One of 'open', 'closed', or 'all'. Defaults to 'open'.
        labels: Optional comma-separated label names to filter by.
    """
    if state not in ("open", "closed", "all"):
        raise ValueError(f"Invalid state '{state}'. Must be 'open', 'closed', or 'all'.")

    params: dict[str, Any] = {"state": state, "per_page": 30}
    if labels:
        params["labels"] = labels

    data = await _make_request(
        "GET", f"/repos/{owner}/{repo}/issues", params=params
    )
    return [
        {
            "number": issue["number"],
            "title": issue["title"],
            "author": issue["user"]["login"],
            "state": issue["state"],
            "created_at": issue["created_at"],
            "labels": [l["name"] for l in issue["labels"]],
            "url": issue["html_url"],
        }
        for issue in data
        if "pull_request" not in issue
    ]


@cached(ttl=300)  # 5 minutes
async def get_user_profile(username: str) -> dict:
    """Fetch public profile information for a GitHub user."""
    data = await _make_request("GET", f"/users/{username}")
    return {
        "login": data["login"],
        "name": data.get("name") or "Not specified",
        "bio": data.get("bio") or "No bio",
        "company": data.get("company") or "Not specified",
        "location": data.get("location") or "Not specified",
        "public_repos": data["public_repos"],
        "followers": data["followers"],
        "following": data["following"],
        "created_at": data["created_at"],
        "url": data["html_url"],
    }


@cached(ttl=300)  # 5 minutes
async def compare_branches(
    owner: str, repo: str, base: str, head: str
) -> dict:
    """Compare two branches, tags, or commits in a repository.

    Returns status, commit count, commit messages, and changed files.
    """
    data = await _make_request(
        "GET", f"/repos/{owner}/{repo}/compare/{base}...{head}"
    )
    return {
        "status": data["status"],
        "ahead_by": data["ahead_by"],
        "behind_by": data["behind_by"],
        "total_commits": data["total_commits"],
        "commits": [
            {
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
            }
            for c in data["commits"]
        ],
        "files": [
            {
                "filename": f["filename"],
                "status": f["status"],
                "changes": f["changes"],
            }
            for f in data.get("files", [])
        ],
    }


@cached(ttl=60)  # 1 minute — changes frequently
async def list_workflow_runs(
    owner: str, repo: str, status: str | None = None
) -> list[dict]:
    """List recent GitHub Actions workflow runs for a repository.

    Args:
        owner: Repository owner (user or org).
        repo: Repository name.
        status: Optional filter: 'completed', 'in_progress', or 'queued'.
    """
    valid_statuses = ("completed", "in_progress", "queued", "waiting", "requested")
    if status and status not in valid_statuses:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}."
        )

    params: dict[str, Any] = {"per_page": 20}
    if status:
        params["status"] = status

    data = await _make_request(
        "GET", f"/repos/{owner}/{repo}/actions/runs", params=params
    )
    return [
        {
            "name": run["name"],
            "status": run["status"],
            "conclusion": run.get("conclusion") or "pending",
            "branch": run["head_branch"],
            "created_at": run["created_at"],
            "url": run["html_url"],
        }
        for run in data.get("workflow_runs", [])
    ]


@cached(ttl=300)  # 5 min
async def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the raw diff for a pull request.

    Returns the diff as a string, truncated at 50,000 characters if needed.
    """
    diff = await _make_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pr_number}",
        raw=True,
        headers={"Accept": "application/vnd.github.v3.diff"},
    )
    if len(diff) > 50000:
        return diff[:50000] + "\n\n[Diff truncated due to size]"
    return diff


@cached(ttl=600)  # 10 min
async def get_repo_readme(owner: str, repo: str) -> str:
    """Fetch the raw README content for a repository.

    Returns the README as a string, truncated at 20,000 characters if needed.
    """
    content = await _make_request(
        "GET",
        f"/repos/{owner}/{repo}/readme",
        raw=True,
        headers={"Accept": "application/vnd.github.v3.raw"},
    )
    if len(content) > 20000:
        return content[:20000] + "\n\n[README truncated due to size]"
    return content
