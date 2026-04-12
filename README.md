# GitHub DevTools MCP Server

An MCP (Model Context Protocol) server that provides GitHub repository tools and Gemini-powered AI helpers for Claude Desktop, Cursor, or any MCP-compatible client.

## Tools

### GitHub Tools

| Tool | Description |
|------|-------------|
| `get_repository_info` | Get stars, forks, open issues, language, and description for any GitHub repo |
| `list_repo_pull_requests` | List PRs with title, author, date, and draft status |
| `create_issue` | Create a GitHub issue with title, body, and labels |
| `list_repo_issues` | List issues (excluding PRs) with filtering by state and labels |
| `get_github_user_profile` | Get a user's name, bio, company, location, repos, and follower count |
| `compare_repo_branches` | Compare two branches/tags/commits — shows commits and changed files |
| `list_repo_workflow_runs` | List recent GitHub Actions runs with status and conclusion |

### AI-Powered Tools

| Tool | Description |
|------|-------------|
| `ai_code_review` | Gemini-powered code review with bugs, suggestions, and quality score |
| `ai_commit_message` | Generate conventional commit messages from change descriptions |
| `ai_generate_issue` | Analyze buggy code and generate a structured GitHub issue |

### Hybrid Tools (GitHub + AI)

| Tool | Description |
|------|-------------|
| `ai_pr_review` | Fetch a real PR diff from GitHub and review it with Gemini AI |
| `ai_explain_repo` | Fetch repo metadata + README and generate an AI-powered explanation |
| `ai_release_notes` | Fetch commits between two refs and generate professional release notes |

## Setup

1. **Clone and install:**

   ```bash
   git clone <repo-url>
   cd github_devTools_mcp
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate

   pip install -e .
   ```

2. **Create `.env` from the example:**

   ```bash
   cp .env.example .env
   ```

3. **Add your API keys to `.env`:**

   ```
   GITHUB_TOKEN=ghp_your_personal_access_token_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

   - **GITHUB_TOKEN**: Go to GitHub > Settings > Developer settings > Personal access tokens > Generate new token. Needs `repo` scope for creating issues.
   - **GEMINI_API_KEY**: Get one at https://aistudio.google.com/apikey

## Claude Desktop Configuration

Add this to your Claude Desktop config file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github-dev-tools": {
      "command": "c:/Users/your_username/self_projects/github_devTools_mcp/.venv/Scripts/python.exe",
      "args": ["-m", "github_mcp.server"],
      "cwd": "c:/Users/your_username/self_projects/github_devTools_mcp",
      "env": {
        "GITHUB_TOKEN": "your_token_here",
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

> **Note**: Replace the paths and API keys with your own values. Use absolute paths to the venv Python executable.

## VS Code Configuration

### Workspace-level (recommended)

Create a `.vscode/mcp.json` file in your project root:

```json
{
  "servers": {
    "github-dev-tools": {
      "command": "c:/Users/your_username/self_projects/github_devTools_mcp/.venv/Scripts/python.exe",
      "args": ["-m", "github_mcp.server"],
      "cwd": "c:/Users/your_username/self_projects/github_devTools_mcp",
      "env": {
        "GITHUB_TOKEN": "your_token_here",
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

### User-level (available in all projects)

Open VS Code Settings JSON (`Ctrl+Shift+P` > "Preferences: Open User Settings (JSON)") and add:

```json
{
  "mcp": {
    "servers": {
      "github-dev-tools": {
        "command": "c:/Users/your_username/self_projects/github_devTools_mcp/.venv/Scripts/python.exe",
        "args": ["-m", "github_mcp.server"],
        "cwd": "c:/Users/your_username/self_projects/github_devTools_mcp",
        "env": {
          "GITHUB_TOKEN": "your_token_here",
          "GEMINI_API_KEY": "your_key_here"
        }
      }
    }
  }
}
```

After adding either config, restart VS Code. The tools will be available in Copilot Chat (agent mode) or Claude Code.

## Testing with MCP Inspector

You can test the server interactively without Claude Desktop:

```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python -m github_mcp.server
```

This opens a browser UI where you can run each tool with custom inputs.

## Example Prompts

Once connected, try these:

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

## Tech Stack

- **MCP SDK** (`mcp`) — Anthropic's official Model Context Protocol SDK
- **httpx** — async HTTP client for GitHub API calls
- **google-genai** — Gemini Flash for AI-powered tools
- **python-dotenv** — environment variable management
