"""Gemini-powered AI tool functions with structured output and enhanced prompts."""

import json
import os

from google import genai

from github_mcp.models import CodeReviewResult, RepoHealthReport

_client = None


def _get_client() -> genai.Client:
    """Get or create the Gemini client (lazy initialization)."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _parse_json_response(text: str) -> dict:
    """Parse JSON from Gemini response, stripping markdown fences if present."""
    raw = text.strip()
    if raw.startswith("```"):
        # Strip ```json ... ``` or ``` ... ```
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)

# Code Review — Structured Output with Pydantic

async def review_code(code: str, language: str = "python") -> CodeReviewResult | str:
    """Send code to Gemini for a structured review.

    Returns a validated CodeReviewResult on success, or a free-text string
    as a graceful fallback if JSON parsing fails.
    """
    client = _get_client()
    schema = json.dumps(CodeReviewResult.model_json_schema(), indent=2)

    prompt = f"""You are a principal software engineer with 15 years of experience \
performing a thorough code review. Analyze the following {language} code for bugs, \
security issues, and improvement opportunities.

RULES:
- Maximum 5 bugs and 5 suggestions. Be specific and actionable.
- Every bug must include a severity level.
- Quality score must be justified by the actual code quality.
- Respond with ONLY valid JSON matching the schema below. No markdown fences, no extra text.

JSON SCHEMA:
{schema}

EXAMPLE INPUT:
```python
def divide(a, b):
    return a / b
```

EXAMPLE OUTPUT:
{{"bugs": [{{"line": 2, "severity": "critical", "description": "No check for division by zero — will raise ZeroDivisionError"}}], "suggestions": [{{"description": "Add type hints for parameters and return value", "category": "readability"}}, {{"description": "Consider returning a Result type or Optional for error cases", "category": "best-practice"}}], "quality_score": 4, "summary": "Simple function with a critical unhandled edge case. Needs input validation and type hints."}}

CODE TO REVIEW:
```{language}
{code}
```"""

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={"temperature": 0.2},
    )

    try:
        data = _parse_json_response(response.text)
        return CodeReviewResult.model_validate(data)
    except (json.JSONDecodeError, Exception):
        return response.text  # graceful fallback to free-text


# Commit Message Generation — Enhanced Prompts
# ---------------------------------------------------------------------------

async def generate_commit_message(changes_description: str) -> str:
    """Generate a conventional commit message from a description of changes.

    Uses few-shot examples for consistent format.
    """
    client = _get_client()

    prompt = """You are a meticulous open-source maintainer who writes precise, \
standardized commit messages following the Conventional Commits specification.

FORMAT: type(scope): description
TYPES: feat, fix, docs, style, refactor, test, chore, perf, ci, build

RULES:
- Subject line MUST be under 72 characters
- Use imperative mood ("add" not "added")
- Include a brief body only if the changes are complex
- Return ONLY the commit message, nothing else

EXAMPLES:
Input: "Added a dark mode toggle to the settings page"
Output: feat(settings): add dark mode toggle

Input: "Fixed the divide-by-zero error in calculate_average"
Output: fix(math): handle divide-by-zero in calculate_average

Input: "Moved database config to environment variables and added connection pooling"
Output: refactor(db): externalize config to env vars and add connection pooling

Improves security by removing hardcoded credentials and
adds connection pooling for better resource management.

CHANGES:
""" + changes_description

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={"temperature": 0.3},
    )
    return response.text.strip()


# ---------------------------------------------------------------------------
# PR Diff Review
# ---------------------------------------------------------------------------

async def review_pr_diff(diff: str, pr_title: str) -> str:
    """Review a pull request diff using Gemini.

    Returns a structured review with summary, issues, suggestions, and verdict.
    """
    client = _get_client()
    prompt = (
        "You are a senior staff engineer performing a pull request review. "
        "Be thorough but constructive.\n\n"
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
        config={"temperature": 0.3},
    )
    return response.text


# ---------------------------------------------------------------------------
# Issue Generation from Code
# ---------------------------------------------------------------------------

async def generate_issue_from_code(code: str, language: str = "python") -> str:
    """Analyze buggy code and generate a structured GitHub issue."""
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
        config={"temperature": 0.3},
    )
    return response.text


# ---------------------------------------------------------------------------
# Repository Explanation
# ---------------------------------------------------------------------------

async def explain_repo(repo_info: dict, readme_content: str) -> str:
    """Generate an AI-powered explanation of a repository."""
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
        config={"temperature": 0.5},
    )
    return response.text


# ---------------------------------------------------------------------------
# Release Notes Generation
# ---------------------------------------------------------------------------

async def generate_release_notes(commits: list[dict], repo_name: str) -> str:
    """Generate professional release notes from a list of commits."""
    client = _get_client()
    commit_lines = "\n".join(f"- {c['sha']} {c['message']}" for c in commits)
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
        config={"temperature": 0.5},
    )
    return response.text


# ---------------------------------------------------------------------------
# Repository Health Check — Agentic Structured Output
# ---------------------------------------------------------------------------

async def repo_health_check(data: dict) -> RepoHealthReport | str:
    """Analyze aggregated repository data and produce a scored health report.

    Receives pre-aggregated data from multiple GitHub API calls.
    Returns a validated RepoHealthReport on success, or free-text fallback.
    """
    client = _get_client()
    schema = json.dumps(RepoHealthReport.model_json_schema(), indent=2)

    # Extract and compute metrics for the prompt
    info = data.get("repo_info") or {}
    issues = data.get("open_issues", [])
    prs = data.get("open_prs", [])
    runs = data.get("workflow_runs", [])

    successful_runs = [r for r in runs if r.get("conclusion") == "success"]
    failed_runs = [r for r in runs if r.get("conclusion") == "failure"]
    ci_success_rate = (len(successful_runs) / len(runs) * 100) if runs else 0

    data_summary = f"""Repository: {info.get('full_name', 'unknown')}
Description: {info.get('description', 'none')}
Language: {info.get('language', 'unknown')}
Stars: {info.get('stars', 0)} | Forks: {info.get('forks', 0)}
Last push: {info.get('last_push', 'unknown')}
Default branch: {info.get('default_branch', 'unknown')}
Open issues: {len(issues)}
Open pull requests: {len(prs)}
README exists: {data.get('readme_exists', False)} ({data.get('readme_length', 0)} chars)
CI workflow runs (last 20): {len(runs)} total, {len(successful_runs)} success, {len(failed_runs)} failed
CI success rate: {ci_success_rate:.0f}%
Data collection errors: {data.get('errors', [])}"""

    prompt = f"""You are a DevOps consultant performing a repository health audit. \
Analyze the data below and produce a comprehensive health report.

RULES:
- Every score (1-10) MUST be justified by specific metrics from the data.
- Identify concrete risks with actionable recommendations.
- Be data-driven, not speculative.
- Respond with ONLY valid JSON matching the schema below. No markdown fences, no extra text.

JSON SCHEMA:
{schema}

EXAMPLE OUTPUT:
{{"scores": {{"overall": 7, "maintenance": 8, "ci_cd": 6, "documentation": 9, "community": 7}}, "risks": [{{"area": "CI/CD", "severity": "medium", "description": "3 of last 20 workflow runs failed (85% success rate)", "recommendation": "Investigate failing workflows and add retry logic for flaky tests"}}], "summary": "Well-maintained repository with strong documentation but CI reliability needs attention."}}

REPOSITORY DATA:
{data_summary}"""

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={"temperature": 0.2},
    )

    try:
        parsed = _parse_json_response(response.text)
        return RepoHealthReport.model_validate(parsed)
    except (json.JSONDecodeError, Exception):
        return response.text  # graceful fallback
