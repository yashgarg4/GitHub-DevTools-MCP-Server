"""Gemini-powered AI tool functions."""

import os

from google import genai

_client = None


def _get_client() -> genai.Client:
    """Get or create the Gemini client (lazy initialization)."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Get a key at https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
    return _client


async def review_code(code: str, language: str = "python") -> str:
    """Send code to Gemini Flash for a structured review.

    Returns a review with: bugs found, suggestions, and a quality score (1-10).
    """
    client = _get_client()
    prompt = (
        f"You are an expert code reviewer. Review the following {language} code.\n"
        f"Provide your review in this exact format:\n\n"
        f"## Bugs & Issues\n- List any bugs or potential issues\n\n"
        f"## Suggestions\n- List improvement suggestions\n\n"
        f"## Quality Score\nX/10 - Brief justification\n\n"
        f"Code to review:\n```{language}\n{code}\n```"
    )
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text


async def generate_commit_message(changes_description: str) -> str:
    """Generate a conventional commit message from a description of changes.

    Returns a message in the format: type(scope): description
    Where type is one of: feat, fix, docs, style, refactor, test, chore, perf, ci, build.
    """
    client = _get_client()
    prompt = (
        "Generate a conventional commit message for the following changes. "
        "Use the conventional commits format: type(scope): description\n"
        "Where type is one of: feat, fix, docs, style, refactor, test, chore, perf, ci, build.\n"
        "Return ONLY the commit message, nothing else. "
        "Include a brief body if the changes are complex.\n\n"
        f"Changes:\n{changes_description}"
    )
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text.strip()


async def review_pr_diff(diff: str, pr_title: str) -> str:
    """Review a pull request diff using Gemini.

    Returns a structured review with summary, issues, suggestions, and verdict.
    """
    client = _get_client()
    prompt = (
        "You are an expert code reviewer performing a pull request review.\n\n"
        f"PR Title: {pr_title}\n\n"
        "Review the following diff and provide feedback in this exact format:\n\n"
        "## Summary\nBrief summary of what this PR does.\n\n"
        "## Issues Found\n- List any bugs, logic errors, or security concerns\n\n"
        "## Suggestions\n- List code quality and design improvement suggestions\n\n"
        "## Verdict\nAPPROVE / REQUEST_CHANGES / COMMENT - Brief justification\n\n"
        f"Diff:\n```diff\n{diff}\n```"
    )
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text


async def generate_issue_from_code(code: str, language: str = "python") -> str:
    """Analyze buggy code and generate a structured GitHub issue.

    Returns a pre-formatted issue with title, description, reproduction steps,
    and suggested fix.
    """
    client = _get_client()
    prompt = (
        f"You are a senior developer analyzing buggy code. Generate a GitHub issue "
        f"for the following {language} code.\n\n"
        "Respond in this exact format:\n\n"
        "## Title\nA clear, concise issue title\n\n"
        "## Description\nDetailed description of the problem found in the code.\n\n"
        "## Steps to Reproduce\n1. Step-by-step reproduction instructions\n\n"
        "## Expected Behavior\nWhat should happen.\n\n"
        "## Actual Behavior\nWhat actually happens (the bug).\n\n"
        "## Suggested Fix\nA brief description or code snippet showing how to fix it.\n\n"
        "## Labels\nComma-separated suggested labels (e.g., bug, priority:high)\n\n"
        f"Code:\n```{language}\n{code}\n```"
    )
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text


async def explain_repo(repo_info: dict, readme_content: str) -> str:
    """Generate an AI-powered explanation of a repository.

    Uses repo metadata and README content to produce a plain-language summary.
    """
    client = _get_client()
    info_str = "\n".join(f"{k}: {v}" for k, v in repo_info.items())
    prompt = (
        "You are a developer advocate explaining a GitHub repository to someone new.\n\n"
        f"Repository metadata:\n{info_str}\n\n"
        f"README content:\n{readme_content}\n\n"
        "Provide a clear explanation in this format:\n\n"
        "## What is this project?\nOne-paragraph summary in plain language.\n\n"
        "## Key Features\n- Bullet list of main features/capabilities\n\n"
        "## Tech Stack\n- Languages, frameworks, and tools used\n\n"
        "## Who is it for?\nTarget audience and use cases.\n\n"
        "## Getting Started\nBrief summary of how to start using it."
    )
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text


async def generate_release_notes(commits: list[dict], repo_name: str) -> str:
    """Generate professional release notes from a list of commits.

    Args:
        commits: List of dicts with 'sha' and 'message' keys.
        repo_name: Repository name for context (e.g., 'owner/repo').
    """
    client = _get_client()
    commit_lines = "\n".join(
        f"- {c['sha']} {c['message']}" for c in commits
    )
    prompt = (
        f"You are a technical writer generating release notes for {repo_name}.\n\n"
        "Based on the following commits, generate professional release notes "
        "in this format:\n\n"
        "## Release Notes\n\n"
        "### Highlights\n- 1-3 sentence summary of the most important changes\n\n"
        "### Features\n- New features added\n\n"
        "### Bug Fixes\n- Bugs that were fixed\n\n"
        "### Other Changes\n- Refactoring, docs, CI, dependency updates, etc.\n\n"
        "Omit any section that has no relevant commits. Be concise.\n\n"
        f"Commits:\n{commit_lines}"
    )
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text
