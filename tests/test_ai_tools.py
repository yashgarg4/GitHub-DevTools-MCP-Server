"""Tests for ai_tools.py — all Gemini calls mocked."""

import json

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from github_mcp.ai_tools import (
    review_code,
    generate_commit_message,
    repo_health_check,
)
from github_mcp.models import CodeReviewResult, RepoHealthReport


def _mock_gemini_response(text: str):
    """Create a mock genai client that returns the given text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = text
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return mock_client


# --- review_code structured output ---


@pytest.mark.asyncio
async def test_review_code_returns_structured_result(mock_github_env):
    structured_json = json.dumps({
        "bugs": [
            {"line": 2, "severity": "critical", "description": "Subtracts instead of adding"}
        ],
        "suggestions": [
            {"description": "Add type hints", "category": "readability"}
        ],
        "quality_score": 3,
        "summary": "Function has a critical logic error.",
    })
    mock_client = _mock_gemini_response(structured_json)

    with patch("github_mcp.ai_tools._get_client", return_value=mock_client):
        result = await review_code("def add(a, b): return a - b", "python")
        assert isinstance(result, CodeReviewResult)
        assert result.quality_score == 3
        assert len(result.bugs) == 1
        assert result.bugs[0].severity == "critical"


@pytest.mark.asyncio
async def test_review_code_handles_markdown_fenced_json(mock_github_env):
    fenced = '```json\n{"bugs": [], "suggestions": [], "quality_score": 8, "summary": "Clean code."}\n```'
    mock_client = _mock_gemini_response(fenced)

    with patch("github_mcp.ai_tools._get_client", return_value=mock_client):
        result = await review_code("print('hello')", "python")
        assert isinstance(result, CodeReviewResult)
        assert result.quality_score == 8


@pytest.mark.asyncio
async def test_review_code_falls_back_on_invalid_json(mock_github_env):
    mock_client = _mock_gemini_response("This is a plain text review, not JSON.")

    with patch("github_mcp.ai_tools._get_client", return_value=mock_client):
        result = await review_code("x = 1", "python")
        assert isinstance(result, str)
        assert "plain text review" in result


# --- generate_commit_message ---


@pytest.mark.asyncio
async def test_generate_commit_message(mock_github_env):
    mock_client = _mock_gemini_response("feat(auth): add JWT-based authentication")

    with patch("github_mcp.ai_tools._get_client", return_value=mock_client):
        result = await generate_commit_message("Added JWT authentication")
        assert "feat(auth)" in result


# --- repo_health_check structured output ---


@pytest.mark.asyncio
async def test_repo_health_check_returns_structured_report(mock_github_env):
    report_json = json.dumps({
        "scores": {
            "overall": 7,
            "maintenance": 8,
            "ci_cd": 6,
            "documentation": 9,
            "community": 7,
        },
        "risks": [
            {
                "area": "CI/CD",
                "severity": "medium",
                "description": "15% failure rate in recent runs",
                "recommendation": "Investigate flaky tests",
            }
        ],
        "summary": "Well-maintained repo with CI concerns.",
    })
    mock_client = _mock_gemini_response(report_json)

    sample_data = {
        "repo_info": {"full_name": "test/repo", "stars": 100, "forks": 20,
                       "language": "Python", "last_push": "2025-01-01",
                       "description": "Test", "default_branch": "main"},
        "open_issues": [{"number": 1}],
        "open_prs": [],
        "workflow_runs": [{"conclusion": "success"}, {"conclusion": "failure"}],
        "readme_exists": True,
        "readme_length": 5000,
        "errors": [],
    }

    with patch("github_mcp.ai_tools._get_client", return_value=mock_client):
        result = await repo_health_check(sample_data)
        assert isinstance(result, RepoHealthReport)
        assert result.scores.overall == 7
        assert len(result.risks) == 1


@pytest.mark.asyncio
async def test_repo_health_check_falls_back_on_bad_json(mock_github_env):
    mock_client = _mock_gemini_response("The repo looks healthy overall.")

    with patch("github_mcp.ai_tools._get_client", return_value=mock_client):
        result = await repo_health_check({"repo_info": {}, "open_issues": [],
                                           "open_prs": [], "workflow_runs": [],
                                           "readme_exists": False, "readme_length": 0,
                                           "errors": []})
        assert isinstance(result, str)


# --- missing API key ---


@pytest.mark.asyncio
async def test_missing_gemini_key_raises_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Reset the cached client
    import github_mcp.ai_tools as mod
    mod._client = None

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        await review_code("x = 1", "python")
