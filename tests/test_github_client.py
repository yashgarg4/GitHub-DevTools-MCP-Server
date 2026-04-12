"""Tests for github_client.py — all GitHub API calls mocked with respx."""

import pytest
import respx
from httpx import Response

from github_mcp.github_client import (
    get_repo_info,
    list_issues,
    get_user_profile,
    list_workflow_runs,
    list_pull_requests,
    _make_request,
)


# --- get_repo_info ---


@pytest.mark.asyncio
async def test_get_repo_info_success(mock_github_env, sample_repo_response):
    with respx.mock:
        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
            return_value=Response(200, json=sample_repo_response)
        )
        result = await get_repo_info("octocat", "Hello-World")
        assert result["full_name"] == "octocat/Hello-World"
        assert result["stars"] == 100
        assert result["forks"] == 50
        assert result["language"] == "Python"


@pytest.mark.asyncio
async def test_get_repo_info_not_found(mock_github_env):
    with respx.mock:
        respx.get("https://api.github.com/repos/octocat/nonexistent").mock(
            return_value=Response(404, text="Not Found")
        )
        with pytest.raises(ValueError, match="Not found"):
            await get_repo_info("octocat", "nonexistent")


# --- list_issues ---


@pytest.mark.asyncio
async def test_list_issues_filters_out_prs(mock_github_env, sample_issues_response):
    with respx.mock:
        respx.get("https://api.github.com/repos/octocat/Hello-World/issues").mock(
            return_value=Response(200, json=sample_issues_response)
        )
        result = await list_issues("octocat", "Hello-World")
        # Issue #2 is a PR and should be filtered out
        assert len(result) == 1
        assert result[0]["number"] == 1
        assert result[0]["title"] == "Bug: login fails"
        assert result[0]["labels"] == ["bug"]


@pytest.mark.asyncio
async def test_list_issues_invalid_state(mock_github_env):
    with pytest.raises(ValueError, match="Invalid state"):
        await list_issues("octocat", "Hello-World", state="invalid")


# --- get_user_profile ---


@pytest.mark.asyncio
async def test_get_user_profile_success(mock_github_env, sample_user_response):
    with respx.mock:
        respx.get("https://api.github.com/users/octocat").mock(
            return_value=Response(200, json=sample_user_response)
        )
        result = await get_user_profile("octocat")
        assert result["login"] == "octocat"
        assert result["name"] == "The Octocat"
        assert result["followers"] == 5000


# --- list_workflow_runs ---


@pytest.mark.asyncio
async def test_list_workflow_runs_success(
    mock_github_env, sample_workflow_runs_response
):
    with respx.mock:
        respx.get(
            "https://api.github.com/repos/octocat/Hello-World/actions/runs"
        ).mock(return_value=Response(200, json=sample_workflow_runs_response))
        result = await list_workflow_runs("octocat", "Hello-World")
        assert len(result) == 2
        assert result[0]["name"] == "CI"
        assert result[0]["conclusion"] == "success"
        assert result[1]["conclusion"] == "failure"


@pytest.mark.asyncio
async def test_list_workflow_runs_invalid_status(mock_github_env):
    with pytest.raises(ValueError, match="Invalid status"):
        await list_workflow_runs("octocat", "Hello-World", status="bad")


# --- _make_request error handling ---


@pytest.mark.asyncio
async def test_make_request_401_auth_error(mock_github_env):
    with respx.mock:
        respx.get("https://api.github.com/test").mock(
            return_value=Response(401, text="Unauthorized")
        )
        with pytest.raises(ValueError, match="Authentication failed"):
            await _make_request("GET", "/test")


@pytest.mark.asyncio
async def test_make_request_403_rate_limit(mock_github_env):
    with respx.mock:
        respx.get("https://api.github.com/test").mock(
            return_value=Response(
                403,
                text="Rate limited",
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "1700000000",
                },
            )
        )
        with pytest.raises(ValueError, match="rate limit"):
            await _make_request("GET", "/test")


@pytest.mark.asyncio
async def test_make_request_403_forbidden(mock_github_env):
    with respx.mock:
        respx.get("https://api.github.com/test").mock(
            return_value=Response(403, text="Forbidden")
        )
        with pytest.raises(ValueError, match="forbidden"):
            await _make_request("GET", "/test")


@pytest.mark.asyncio
async def test_make_request_raw_response(mock_github_env):
    with respx.mock:
        respx.get("https://api.github.com/test").mock(
            return_value=Response(200, text="raw text content")
        )
        result = await _make_request("GET", "/test", raw=True)
        assert result == "raw text content"


# --- list_pull_requests ---


@pytest.mark.asyncio
async def test_list_pull_requests_invalid_state(mock_github_env):
    with pytest.raises(ValueError, match="Invalid state"):
        await list_pull_requests("octocat", "Hello-World", state="bad")
