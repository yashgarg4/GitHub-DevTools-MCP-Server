"""Tests for server.py — tool registration and agentic orchestration."""

import pytest
from unittest.mock import patch, AsyncMock

from github_mcp.server import mcp, ai_full_repo_health_check
from github_mcp.models import RepoHealthReport, HealthScore


def test_all_14_tools_registered():
    """Verify all 14 tools are registered."""
    tools = list(mcp._tool_manager._tools.keys())
    assert len(tools) == 14
    assert "get_repository_info" in tools
    assert "ai_code_review" in tools
    assert "ai_full_repo_health_check" in tools


def test_tool_names_are_descriptive():
    """Verify tool names follow naming conventions."""
    tools = list(mcp._tool_manager._tools.keys())
    ai_tools = [t for t in tools if t.startswith("ai_")]
    github_tools = [t for t in tools if not t.startswith("ai_")]
    assert len(ai_tools) >= 6  # 6 AI/hybrid tools
    assert len(github_tools) >= 7  # 7 pure GitHub tools + create_issue


@pytest.mark.asyncio
async def test_health_check_orchestrates_all_calls():
    """Verify the health check calls all 5 data-gathering functions."""
    mock_repo = {"full_name": "t/r", "description": "test", "language": "Py",
                 "stars": 10, "forks": 5, "open_issues": 2,
                 "last_push": "2025-01-01", "default_branch": "main",
                 "url": "https://github.com/t/r"}

    report = RepoHealthReport(
        scores=HealthScore(overall=7, maintenance=8, ci_cd=6,
                          documentation=9, community=7),
        risks=[],
        summary="Healthy repo.",
    )

    with patch("github_mcp.server.get_repo_info", new_callable=AsyncMock, return_value=mock_repo) as m_info, \
         patch("github_mcp.server.list_issues", new_callable=AsyncMock, return_value=[]) as m_issues, \
         patch("github_mcp.server.list_pull_requests", new_callable=AsyncMock, return_value=[]) as m_prs, \
         patch("github_mcp.server.list_workflow_runs", new_callable=AsyncMock, return_value=[]) as m_wf, \
         patch("github_mcp.server.get_repo_readme", new_callable=AsyncMock, return_value="# README") as m_readme, \
         patch("github_mcp.server.repo_health_check", new_callable=AsyncMock, return_value=report):

        result = await ai_full_repo_health_check("t", "r")

        m_info.assert_called_once_with("t", "r")
        m_issues.assert_called_once_with("t", "r", state="open")
        m_prs.assert_called_once_with("t", "r", state="open")
        m_wf.assert_called_once_with("t", "r")
        m_readme.assert_called_once_with("t", "r")

        assert "Health Report: t/r" in result
        assert "7/10" in result


@pytest.mark.asyncio
async def test_health_check_handles_partial_failures():
    """Verify health check works even if some API calls fail."""
    mock_repo = {"full_name": "t/r", "description": "test", "language": "Py",
                 "stars": 10, "forks": 5, "open_issues": 2,
                 "last_push": "2025-01-01", "default_branch": "main",
                 "url": "https://github.com/t/r"}

    with patch("github_mcp.server.get_repo_info", new_callable=AsyncMock, return_value=mock_repo), \
         patch("github_mcp.server.list_issues", new_callable=AsyncMock, return_value=[]), \
         patch("github_mcp.server.list_pull_requests", new_callable=AsyncMock, return_value=[]), \
         patch("github_mcp.server.list_workflow_runs", new_callable=AsyncMock, side_effect=ValueError("No Actions")), \
         patch("github_mcp.server.get_repo_readme", new_callable=AsyncMock, side_effect=ValueError("No README")), \
         patch("github_mcp.server.repo_health_check", new_callable=AsyncMock, return_value="Fallback text report"):

        result = await ai_full_repo_health_check("t", "r")
        # Should not crash — returns fallback text
        assert "Fallback text report" in result
