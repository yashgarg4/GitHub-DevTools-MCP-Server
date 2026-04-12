"""MCP server entry point. Registers all tools and runs the stdio transport."""

import asyncio

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from github_mcp.github_client import (
    get_repo_info,
    list_pull_requests,
    create_github_issue,
    list_issues,
    get_user_profile,
    compare_branches,
    list_workflow_runs,
    get_pr_diff,
    get_repo_readme,
)
from github_mcp.ai_tools import (
    review_code,
    generate_commit_message,
    review_pr_diff,
    generate_issue_from_code,
    explain_repo,
    generate_release_notes,
    repo_health_check,
)
from github_mcp.models import CodeReviewResult, RepoHealthReport

load_dotenv()

mcp = FastMCP("GitHub DevTools")


# --- GitHub Tools ---


@mcp.tool()
async def get_repository_info(owner: str, repo: str) -> str:
    """Get detailed information about a GitHub repository.

    Returns key metrics including stars, forks, open issues count,
    primary language, last push date, and description.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
    """
    try:
        result = await get_repo_info(owner, repo)
        lines = [f"{key}: {value}" for key, value in result.items()]
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def list_repo_pull_requests(
    owner: str, repo: str, state: str = "open"
) -> str:
    """List pull requests for a GitHub repository.

    Returns PR titles, authors, dates, and draft status, filtered by state.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        state: Filter by PR state. Must be 'open', 'closed', or 'all'. Defaults to 'open'.
    """
    try:
        prs = await list_pull_requests(owner, repo, state)
        if not prs:
            return f"No {state} pull requests found for {owner}/{repo}."
        lines = []
        for pr in prs:
            draft_marker = " [DRAFT]" if pr["draft"] else ""
            lines.append(
                f"#{pr['number']} {pr['title']}{draft_marker}\n"
                f"  Author: {pr['author']} | Created: {pr['created_at']}\n"
                f"  URL: {pr['url']}"
            )
        return "\n\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
) -> str:
    """Create a new issue in a GitHub repository.

    Requires a GITHUB_TOKEN with 'repo' scope to be set in the environment.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        title: The issue title.
        body: The issue body/description in Markdown. Defaults to empty.
        labels: Optional list of label names to apply to the issue.
    """
    try:
        result = await create_github_issue(owner, repo, title, body, labels)
        return (
            f"Issue created successfully!\n"
            f"Number: #{result['number']}\n"
            f"Title: {result['title']}\n"
            f"URL: {result['url']}"
        )
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def list_repo_issues(
    owner: str, repo: str, state: str = "open", labels: str | None = None
) -> str:
    """List issues for a GitHub repository, excluding pull requests.

    Returns issue numbers, titles, authors, and labels, filtered by state.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        state: Filter by issue state. Must be 'open', 'closed', or 'all'. Defaults to 'open'.
        labels: Optional comma-separated list of label names to filter by.
    """
    try:
        issues = await list_issues(owner, repo, state, labels)
        if not issues:
            return f"No {state} issues found for {owner}/{repo}."
        lines = []
        for issue in issues:
            label_str = ", ".join(issue["labels"]) if issue["labels"] else "none"
            lines.append(
                f"#{issue['number']} {issue['title']}\n"
                f"  Author: {issue['author']} | Created: {issue['created_at']}\n"
                f"  Labels: {label_str}\n"
                f"  URL: {issue['url']}"
            )
        return "\n\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def get_github_user_profile(username: str) -> str:
    """Get public profile information for a GitHub user.

    Returns the user's name, bio, company, location, repository count,
    and follower/following counts.

    Args:
        username: The GitHub username to look up.
    """
    try:
        result = await get_user_profile(username)
        lines = [f"{key}: {value}" for key, value in result.items()]
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def compare_repo_branches(
    owner: str, repo: str, base: str, head: str
) -> str:
    """Compare two branches, tags, or commits in a GitHub repository.

    Shows the comparison status, commit count, commit messages, and changed files.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        base: The base branch, tag, or commit SHA to compare from.
        head: The head branch, tag, or commit SHA to compare to.
    """
    try:
        result = await compare_branches(owner, repo, base, head)
        lines = [
            f"Status: {result['status']}",
            f"Ahead by: {result['ahead_by']} | Behind by: {result['behind_by']}",
            f"Total commits: {result['total_commits']}",
            "",
            "Commits:",
        ]
        for c in result["commits"]:
            lines.append(f"  {c['sha']} {c['message']}")
        lines.append("")
        lines.append("Changed Files:")
        for f in result["files"]:
            lines.append(f"  {f['status']:10} {f['filename']} (+/- {f['changes']} changes)")
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def list_repo_workflow_runs(
    owner: str, repo: str, status: str | None = None
) -> str:
    """List recent GitHub Actions workflow runs for a repository.

    Returns workflow run names, statuses, conclusions, and branches.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        status: Optional filter by run status. One of 'completed', 'in_progress', 'queued'.
    """
    try:
        runs = await list_workflow_runs(owner, repo, status)
        if not runs:
            return f"No workflow runs found for {owner}/{repo}."
        lines = []
        for run in runs:
            lines.append(
                f"{run['name']}\n"
                f"  Status: {run['status']} | Conclusion: {run['conclusion']} | Branch: {run['branch']}\n"
                f"  Created: {run['created_at']}\n"
                f"  URL: {run['url']}"
            )
        return "\n\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"


# --- Formatting Helpers ---


def _format_code_review(review: CodeReviewResult) -> str:
    """Format a structured CodeReviewResult into readable text."""
    lines = [f"## Quality Score: {review.quality_score}/10", "", review.summary, ""]
    if review.bugs:
        lines.append("## Bugs & Issues")
        for bug in review.bugs:
            loc = f"Line {bug.line}: " if bug.line else ""
            lines.append(f"- [{bug.severity.upper()}] {loc}{bug.description}")
        lines.append("")
    if review.suggestions:
        lines.append("## Suggestions")
        for s in review.suggestions:
            lines.append(f"- [{s.category}] {s.description}")
    return "\n".join(lines)


def _format_health_report(report: RepoHealthReport, owner: str, repo: str) -> str:
    """Format a structured RepoHealthReport into readable text."""
    s = report.scores
    lines = [
        f"# Health Report: {owner}/{repo}",
        "",
        f"## Scores",
        f"  Overall:       {'=' * s.overall}{'.' * (10 - s.overall)} {s.overall}/10",
        f"  Maintenance:   {'=' * s.maintenance}{'.' * (10 - s.maintenance)} {s.maintenance}/10",
        f"  CI/CD:         {'=' * s.ci_cd}{'.' * (10 - s.ci_cd)} {s.ci_cd}/10",
        f"  Documentation: {'=' * s.documentation}{'.' * (10 - s.documentation)} {s.documentation}/10",
        f"  Community:     {'=' * s.community}{'.' * (10 - s.community)} {s.community}/10",
        "",
        report.summary,
    ]
    if report.risks:
        lines.append("")
        lines.append("## Risks & Recommendations")
        for risk in report.risks:
            lines.append(f"- [{risk.severity.upper()}] {risk.area}: {risk.description}")
            lines.append(f"  Recommendation: {risk.recommendation}")
    return "\n".join(lines)


# --- AI Tools ---


@mcp.tool()
async def ai_code_review(code: str, language: str = "python") -> str:
    """Review a code snippet using Gemini AI.

    Analyzes code for bugs, suggests improvements, and provides a
    quality score out of 10. Returns structured results with severity
    levels and categorized suggestions. Powered by Gemini Flash.

    Args:
        code: The source code to review.
        language: The programming language of the code. Defaults to 'python'.
    """
    try:
        result = await review_code(code, language)
        if isinstance(result, CodeReviewResult):
            return _format_code_review(result)
        return result  # free-text fallback
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"AI review failed: {type(e).__name__}: {e}"


@mcp.tool()
async def ai_commit_message(changes_description: str) -> str:
    """Generate a conventional commit message using Gemini AI.

    Produces a commit message in conventional commits format
    (type(scope): description) based on a description of changes.

    Args:
        changes_description: A description of the code changes to summarize.
    """
    try:
        return await generate_commit_message(changes_description)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Commit message generation failed: {type(e).__name__}: {e}"


@mcp.tool()
async def ai_pr_review(owner: str, repo: str, pr_number: int) -> str:
    """Fetch a pull request diff and review it using Gemini AI.

    Retrieves the actual code diff for the specified PR and sends it
    to Gemini for a structured review with summary, issues, suggestions,
    and an approve/request-changes verdict.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        pr_number: The pull request number to review.
    """
    try:
        diff = await get_pr_diff(owner, repo, pr_number)
        return await review_pr_diff(diff, f"PR #{pr_number} in {owner}/{repo}")
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"AI PR review failed: {type(e).__name__}: {e}"


@mcp.tool()
async def ai_generate_issue(code: str, language: str = "python") -> str:
    """Analyze buggy code and generate a structured GitHub issue using Gemini AI.

    Returns a pre-formatted issue with title, description, reproduction steps,
    and suggested fix. Does NOT create the issue -- review the output first.

    Args:
        code: The source code to analyze for bugs.
        language: The programming language of the code. Defaults to 'python'.
    """
    try:
        return await generate_issue_from_code(code, language)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Issue generation failed: {type(e).__name__}: {e}"


@mcp.tool()
async def ai_explain_repo(owner: str, repo: str) -> str:
    """Fetch repository metadata and README, then generate an AI-powered explanation.

    Retrieves repo info and README content from GitHub, then uses Gemini
    to produce a plain-language summary of what the project is, its features,
    tech stack, and how to get started.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
    """
    try:
        repo_info = await get_repo_info(owner, repo)
        try:
            readme = await get_repo_readme(owner, repo)
        except ValueError:
            readme = "No README found."
        return await explain_repo(repo_info, readme)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Repo explanation failed: {type(e).__name__}: {e}"


@mcp.tool()
async def ai_release_notes(
    owner: str, repo: str, base: str, head: str
) -> str:
    """Generate AI-powered release notes from commits between two refs.

    Fetches all commits between the base and head refs (tags, branches,
    or SHAs), then uses Gemini to format them into professional release notes.

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
        base: The base ref (tag, branch, or SHA) -- typically the previous release.
        head: The head ref (tag, branch, or SHA) -- typically the new release.
    """
    try:
        comparison = await compare_branches(owner, repo, base, head)
        commits = comparison["commits"]
        if not commits:
            return f"No commits found between {base} and {head}."
        return await generate_release_notes(commits, f"{owner}/{repo}")
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Release notes generation failed: {type(e).__name__}: {e}"


# --- Agentic Tools ---


@mcp.tool()
async def ai_full_repo_health_check(owner: str, repo: str) -> str:
    """Run a comprehensive AI-powered health check on a GitHub repository.

    This is an agentic tool that orchestrates multiple GitHub API calls
    in parallel to gather repo metadata, issues, pull requests, CI/CD
    workflow runs, and README content. All data is then sent to Gemini
    for a scored health report with risks and recommendations.

    Scores returned: Overall, Maintenance, CI/CD, Documentation, Community (each 1-10).

    Args:
        owner: The GitHub username or organization that owns the repository.
        repo: The repository name.
    """
    try:
        # Phase 1: Parallel data gathering via asyncio.gather
        results = await asyncio.gather(
            get_repo_info(owner, repo),
            list_issues(owner, repo, state="open"),
            list_pull_requests(owner, repo, state="open"),
            list_workflow_runs(owner, repo),
            get_repo_readme(owner, repo),
            return_exceptions=True,
        )

        repo_data, issues, prs, workflows, readme = results

        # Phase 2: Aggregate data, handling partial failures gracefully
        aggregated = {
            "repo_info": repo_data if not isinstance(repo_data, Exception) else {},
            "open_issues": issues if not isinstance(issues, Exception) else [],
            "open_prs": prs if not isinstance(prs, Exception) else [],
            "workflow_runs": workflows if not isinstance(workflows, Exception) else [],
            "readme_exists": not isinstance(readme, Exception),
            "readme_length": len(readme) if not isinstance(readme, Exception) else 0,
            "errors": [str(r) for r in results if isinstance(r, Exception)],
        }

        # Phase 3: AI analysis of aggregated data
        result = await repo_health_check(aggregated)

        if isinstance(result, RepoHealthReport):
            return _format_health_report(result, owner, repo)
        return result  # free-text fallback

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Health check failed: {type(e).__name__}: {e}"


def main():
    """Synchronous entry point for the MCP server."""
    import sys

    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Server fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
