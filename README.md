# GitHub DevTools MCP Server

![CI](https://github.com/yashgarg4/GitHub-DevTools-MCP-Server/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tools](https://img.shields.io/badge/MCP%20tools-16-green)
![Tests](https://img.shields.io/badge/tests-33%20passed-brightgreen)

A production-grade **Model Context Protocol (MCP)** server that gives AI assistants like Claude Desktop, Cursor, and VS Code Copilot the ability to interact with GitHub and perform AI-powered code analysis — directly as native tool calls.

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io/) is an open standard by Anthropic that lets AI assistants call external tools natively. Instead of copying data between apps, the AI calls your tools directly over stdio — no REST API, no HTTP server, no endpoints.

This project implements an MCP server that exposes **16 tools** across 5 categories: GitHub data retrieval, AI-powered code analysis, hybrid GitHub+AI workflows, agentic multi-step orchestration, and cache management.

## Why This Project?

Most AI tools are simple API wrappers. This project goes further:

- **Agentic orchestration** — One tool chains 5 parallel API calls, handles partial failures, and feeds aggregated data to AI for reasoning
- **Structured AI output** — Gemini responses are validated against Pydantic schemas, not just trusted as free-text
- **Production patterns** — TTL caching, graceful error handling, 33 mocked tests, CI/CD pipeline

## Project Structure

```
github-dev-tools-mcp/
├── src/github_mcp/
│   ├── server.py          # MCP server + 16 tool registrations
│   ├── github_client.py   # Async GitHub API functions (httpx)
│   ├── ai_tools.py        # Gemini AI functions with structured output
│   ├── models.py          # Pydantic models for AI response validation
│   └── cache.py           # TTL cache decorator for API responses
├── tests/
│   ├── test_github_client.py   # GitHub API tests (mocked with respx)
│   ├── test_ai_tools.py        # AI tool tests (mocked Gemini)
│   ├── test_server.py          # Tool registration + orchestration tests
│   └── test_cache.py           # Cache behavior tests
├── .github/workflows/ci.yml    # GitHub Actions CI (Python 3.11-3.13)
├── DESIGN.md              # Architecture & design decisions
├── pyproject.toml         # Dependencies + build config
└── .env.example           # Required API keys template
```

## Tools (16 total)

### GitHub Tools (7)

These call the GitHub REST API directly. All responses are cached with TTL.

| Tool | Description |
|------|-------------|
| `get_repository_info` | Get stars, forks, open issues, language, and description for any GitHub repo |
| `list_repo_pull_requests` | List PRs with title, author, date, and draft status |
| `create_issue` | Create a new GitHub issue with title, body, and labels |
| `list_repo_issues` | List issues (excluding PRs) with filtering by state and labels |
| `get_github_user_profile` | Get a user's name, bio, company, location, repos, and follower count |
| `compare_repo_branches` | Compare two branches/tags/commits — shows commits and changed files |
| `list_repo_workflow_runs` | List recent GitHub Actions runs with status and conclusion |

### AI-Powered Tools (3)

These use Gemini Flash for analysis. Code review returns structured JSON validated by Pydantic.

| Tool | Description |
|------|-------------|
| `ai_code_review` | Code review with severity-tagged bugs, categorized suggestions, and quality score (1-10). Returns structured output via Pydantic validation with graceful fallback to free-text |
| `ai_commit_message` | Generate conventional commit messages (feat/fix/chore etc.) with few-shot prompting for consistent format |
| `ai_generate_issue` | Analyze buggy code and generate a structured GitHub issue with title, description, reproduction steps, and suggested fix |

### Hybrid Tools (3) — GitHub + AI

These fetch real data from GitHub, then send it to Gemini for AI-powered analysis.

| Tool | Description |
|------|-------------|
| `ai_pr_review` | Fetches the actual PR diff from GitHub, sends it to Gemini for a structured review with summary, issues, suggestions, and APPROVE/REQUEST_CHANGES verdict |
| `ai_explain_repo` | Fetches repo metadata + README content, then generates a plain-language explanation of what the project is, its features, tech stack, and how to get started |
| `ai_release_notes` | Fetches commits between two refs (tags/branches), then generates professional release notes with highlights, features, bug fixes, and other changes |

### Agentic Tool (1) — Multi-Step Orchestration

This is the flagship tool. It demonstrates agentic AI patterns: parallel execution, data aggregation, partial failure handling, and AI reasoning over multiple data sources.

| Tool | Description |
|------|-------------|
| `ai_full_repo_health_check` | Orchestrates 5 parallel GitHub API calls (repo info, issues, PRs, CI/CD runs, README), aggregates all data with graceful handling of partial failures, computes derived metrics (CI success rate, etc.), then sends everything to Gemini for a scored health report |

**Health check output includes:**
- **5 scored dimensions** (1-10 each): Overall, Maintenance, CI/CD, Documentation, Community
- **Identified risks** with severity levels and actionable recommendations
- **Executive summary** of repository health

### Utility Tools (2)

| Tool | Description |
|------|-------------|
| `clear_cache` | Clear the in-memory response cache for GitHub API calls. Use when you need fresh data |
| `cache_stats` | Show cache statistics — entries, hits, misses, and hit rate |

## Key Technical Decisions

| Decision | Why |
|----------|-----|
| **MCP over REST** | AI assistants call tools natively via stdio — no HTTP overhead, no endpoint routing |
| **Structured output (Pydantic)** | AI responses are validated against schemas, not trusted as free-text. Falls back gracefully if parsing fails |
| **`asyncio.gather` with `return_exceptions=True`** | Health check fetches 5 APIs in parallel. If one fails (e.g., repo has no Actions), the rest still work |
| **Decorator-based caching** | `@cached(ttl=300)` on functions — no logic changes, configurable per function, exceptions never cached |
| **Enhanced prompts** | System personas, few-shot examples, temperature tuning (0.2 for structured, 0.5 for creative) |
| **Mocked test suite** | 33 tests run without API keys — GitHub mocked with `respx`, Gemini mocked with `unittest.mock` |

## Setup

### Prerequisites

- Python 3.11 or higher
- A GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))
- A Gemini API Key ([get one here](https://aistudio.google.com/apikey))

### Installation

```bash
git clone https://github.com/yashgarg4/GitHub-DevTools-MCP-Server.git
cd GitHub-DevTools-MCP-Server
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e .
```

### Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
GITHUB_TOKEN=ghp_your_personal_access_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

- **GITHUB_TOKEN**: Needs `repo` scope for creating issues. Read-only tools work without a token (with lower rate limits).
- **GEMINI_API_KEY**: Required only for AI-powered tools. GitHub-only tools work without it.

## Connecting to AI Assistants

### Claude Desktop

Add to your config file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github-dev-tools": {
      "command": "/absolute/path/to/.venv/Scripts/python.exe",
      "args": ["-m", "github_mcp.server"],
      "cwd": "/absolute/path/to/GitHub-DevTools-MCP-Server",
      "env": {
        "GITHUB_TOKEN": "your_token_here",
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

### VS Code (Workspace-level)

Create `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "github-dev-tools": {
      "command": "/absolute/path/to/.venv/Scripts/python.exe",
      "args": ["-m", "github_mcp.server"],
      "cwd": "/absolute/path/to/GitHub-DevTools-MCP-Server",
      "env": {
        "GITHUB_TOKEN": "your_token_here",
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

### VS Code (User-level — available in all projects)

Open Settings JSON (`Ctrl+Shift+P` > "Preferences: Open User Settings (JSON)"):

```json
{
  "mcp": {
    "servers": {
      "github-dev-tools": {
        "command": "/absolute/path/to/.venv/Scripts/python.exe",
        "args": ["-m", "github_mcp.server"],
        "cwd": "/absolute/path/to/GitHub-DevTools-MCP-Server",
        "env": {
          "GITHUB_TOKEN": "your_token_here",
          "GEMINI_API_KEY": "your_key_here"
        }
      }
    }
  }
}
```

> **Note**: Replace all paths with absolute paths to your installation. Use forward slashes even on Windows.

## Testing with MCP Inspector

Test tools interactively without any AI assistant:

```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python -m github_mcp.server
```

This opens a browser UI at `http://localhost:5173` where you can select any tool, fill in inputs, and see results. Requires Node.js.

## Example Prompts

Once connected to an AI assistant, try these:

**GitHub Tools:**
- "Get info about the python/cpython repository"
- "List open PRs on facebook/react"
- "Show me the open issues on expressjs/express"
- "Get the profile of torvalds on GitHub"
- "Compare the v3.12.0 and v3.13.0 tags on python/cpython"
- "Show me the recent GitHub Actions runs for actions/toolkit"
- "Create an issue on my-org/my-repo titled 'Fix login bug' with the label 'bug'"

**AI Tools:**
- "Review this Python code for bugs: `def add(a, b): return a - b`"
- "Generate a commit message for: added dark mode toggle to settings page"
- "Analyze this code and generate a bug report issue for it: `def divide(a, b): return a / b`"

**Hybrid Tools (GitHub + AI):**
- "Review PR #123 on my-org/my-repo"
- "Explain what the expressjs/express repository is about"
- "Generate release notes for python/cpython between v3.12.0 and v3.13.0"

**Agentic Tools:**
- "Run a full health check on python/cpython"
- "How healthy is the expressjs/express repository?"

**Utility:**
- "Clear the cache"
- "Show me cache stats"

## Running Tests

All 33 tests run without API keys — every external call is mocked:

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

**Test coverage:**

| Test File | What It Tests |
|-----------|---------------|
| `test_github_client.py` | All GitHub API functions with mocked HTTP responses (`respx`). Covers success paths, 401/403/404 errors, rate limit detection, and raw response mode |
| `test_ai_tools.py` | AI functions with mocked Gemini. Tests structured output parsing, markdown fence stripping, JSON fallback, and missing API key handling |
| `test_server.py` | Tool registration (all 16), health check orchestration (verifies 5 parallel calls), and partial failure handling |
| `test_cache.py` | TTL cache set/get/expiry/clear/stats, decorator caching behavior, separate keys per args, exceptions not cached, integration with real functions |

## Architecture

See [DESIGN.md](DESIGN.md) for detailed documentation on:
- Why MCP over REST
- Tool taxonomy (Pure GitHub / Pure AI / Hybrid / Agentic)
- Data flow diagrams
- Structured output strategy (Pydantic + JSON schema injection + graceful fallback)
- Prompt engineering approach (persona, few-shot, temperature tuning)
- Caching strategy (per-function TTLs, decorator pattern)
- Error handling (3-layer strategy — tools never crash)
- Testing strategy (respx for HTTP, mock for AI)

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| **MCP SDK** (`mcp`) | Anthropic's official Model Context Protocol SDK — stdio transport |
| **httpx** | Async HTTP client for all GitHub API calls |
| **Google Gemini** (`google-genai`) | AI-powered code review, commit messages, repo analysis |
| **Pydantic** | Structured output validation for AI responses |
| **python-dotenv** | Environment variable management |
| **pytest + respx** | Async test framework with HTTP mocking |
| **GitHub Actions** | CI pipeline testing across Python 3.11, 3.12, 3.13 |
