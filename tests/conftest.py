"""Shared test fixtures for mocking GitHub API and Gemini responses."""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_github_env(monkeypatch):
    """Set fake API keys for tests."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_test_token")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")


@pytest.fixture
def mock_gemini_client():
    """Return a mock genai.Client that returns predetermined text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "mock response"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return mock_client


# --- Realistic GitHub API response fixtures ---


@pytest.fixture
def sample_repo_response():
    return {
        "full_name": "octocat/Hello-World",
        "description": "A test repository",
        "language": "Python",
        "stargazers_count": 100,
        "forks_count": 50,
        "open_issues_count": 10,
        "pushed_at": "2025-01-01T00:00:00Z",
        "default_branch": "main",
        "html_url": "https://github.com/octocat/Hello-World",
    }


@pytest.fixture
def sample_issues_response():
    """GitHub issues response — includes a PR (to test filtering)."""
    return [
        {
            "number": 1,
            "title": "Bug: login fails",
            "user": {"login": "alice"},
            "state": "open",
            "created_at": "2025-01-01T00:00:00Z",
            "labels": [{"name": "bug"}],
            "html_url": "https://github.com/octocat/Hello-World/issues/1",
        },
        {
            "number": 2,
            "title": "Add dark mode",
            "user": {"login": "bob"},
            "state": "open",
            "created_at": "2025-01-02T00:00:00Z",
            "labels": [],
            "html_url": "https://github.com/octocat/Hello-World/issues/2",
            "pull_request": {"url": "https://api.github.com/repos/octocat/Hello-World/pulls/2"},
        },
    ]


@pytest.fixture
def sample_user_response():
    return {
        "login": "octocat",
        "name": "The Octocat",
        "bio": "GitHub mascot",
        "company": "GitHub",
        "location": "San Francisco",
        "public_repos": 8,
        "followers": 5000,
        "following": 10,
        "created_at": "2011-01-25T18:44:36Z",
        "html_url": "https://github.com/octocat",
    }


@pytest.fixture
def sample_workflow_runs_response():
    return {
        "workflow_runs": [
            {
                "name": "CI",
                "status": "completed",
                "conclusion": "success",
                "head_branch": "main",
                "created_at": "2025-01-01T00:00:00Z",
                "html_url": "https://github.com/octocat/Hello-World/actions/runs/1",
            },
            {
                "name": "CI",
                "status": "completed",
                "conclusion": "failure",
                "head_branch": "feature",
                "created_at": "2025-01-02T00:00:00Z",
                "html_url": "https://github.com/octocat/Hello-World/actions/runs/2",
            },
        ]
    }
