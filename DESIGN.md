# Architecture & Design

## Overview

This is an MCP (Model Context Protocol) server that exposes GitHub developer tools and Gemini-powered AI analysis over stdio transport. Unlike REST APIs, MCP tools are called directly by AI assistants (Claude Desktop, Cursor, etc.) as native function calls — no HTTP overhead, no endpoint routing, no auth middleware.

## Why MCP Over REST

| Aspect | REST API | MCP Server |
|--------|----------|------------|
| Transport | HTTP (needs server, port, hosting) | stdio (runs as subprocess) |
| Discovery | OpenAPI spec / docs | Tool schemas auto-discovered |
| Auth | Bearer tokens, OAuth flows | Inherited from host process |
| AI Integration | Requires API calling logic | Native — AI sees tools directly |
| Deployment | Cloud hosting required | Local process, zero infra |

MCP is the right choice when the consumer is an AI assistant, not a web frontend.

## Tool Taxonomy

The server implements 14 tools across 4 categories:

```
┌──────────────────────────────────────────────────┐
│                  MCP Server                       │
├──────────────┬───────────────┬────────────────────┤
│ Pure GitHub  │  Pure AI      │  Hybrid            │
│ (7 tools)    │  (3 tools)    │  (3 tools)         │
│              │               │                    │
│ repo info    │ code review   │ PR review          │
│ pull requests│ commit msg    │ explain repo       │
│ create issue │ generate issue│ release notes      │
│ list issues  │               │                    │
│ user profile │               ├────────────────────┤
│ compare      │               │  Agentic           │
│ workflow runs│               │  (1 tool)          │
│              │               │                    │
│              │               │  health check      │
│              │               │  (orchestrates 5+  │
│              │               │   parallel calls)  │
└──────────────┴───────────────┴────────────────────┘
```

## Data Flow

```
MCP Client (Claude Desktop / Cursor / VS Code)
    │
    │ JSON-RPC over stdio
    ▼
server.py — @mcp.tool() registrations
    │
    ├──► github_client.py ──► GitHub REST API
    │       _make_request()      (httpx async)
    │
    ├──► ai_tools.py ──► Google Gemini API
    │       _get_client()        (google-genai async)
    │
    └──► models.py ──► Pydantic validation
            CodeReviewResult
            RepoHealthReport
```

## Agentic Tool Chaining

The `ai_full_repo_health_check` tool demonstrates multi-step orchestration:

```
ai_full_repo_health_check(owner, repo)
    │
    │  Phase 1: Parallel Data Gathering
    │  asyncio.gather(return_exceptions=True)
    ├──► get_repo_info()
    ├──► list_issues(state="open")
    ├──► list_pull_requests(state="open")
    ├──► list_workflow_runs()
    └──► get_repo_readme()
    │
    │  Phase 2: Aggregation + Partial Failure Handling
    │  Exceptions become empty defaults, not crashes
    │
    │  Phase 3: AI Analysis
    └──► repo_health_check(aggregated_data)
              │
              └──► Gemini (structured JSON output)
                      │
                      └──► Pydantic validation → RepoHealthReport
```

Key design decisions:
- `return_exceptions=True` means one failing API call doesn't kill the entire health check
- Derived metrics (CI success rate, etc.) are computed before sending to Gemini
- The AI receives structured data, not raw API responses

## Structured Output Strategy

Instead of relying on free-text Gemini responses, key tools use structured output:

1. **Schema injection**: The Pydantic model's JSON schema is embedded in the prompt
2. **Few-shot examples**: One complete example of the expected JSON output
3. **JSON parsing**: Response is parsed with `json.loads()`
4. **Pydantic validation**: Parsed data is validated against the model
5. **Graceful fallback**: If any step fails, the raw text response is returned

```python
# Pattern used in review_code() and repo_health_check()
try:
    data = _parse_json_response(response.text)
    return SomeModel.model_validate(data)
except (json.JSONDecodeError, Exception):
    return response.text  # never crash
```

This ensures AI tools always return something useful, even if Gemini's output doesn't match the schema perfectly.

## Prompt Engineering Approach

| Technique | Where Used | Why |
|-----------|-----------|-----|
| System persona | All AI tools | Consistent role framing ("principal engineer", "DevOps consultant") |
| Few-shot examples | Code review, health check, commit messages | Format consistency — shows the model exactly what we expect |
| Temperature tuning | Per tool | 0.2 for structured output, 0.3 for commit messages, 0.5 for creative tools |
| Output constraints | Code review, health check | "Maximum 5 bugs", "under 72 characters" — prevents verbose output |
| Schema injection | Structured tools | JSON schema in prompt ensures parseable responses |

## Error Handling Strategy

```
Layer 1: github_client.py
    _make_request() maps HTTP errors to ValueError:
    401 → "Authentication failed"
    403 → "Rate limit exceeded" (checks X-RateLimit-Remaining)
    404 → "Not found"

Layer 2: ai_tools.py
    ValueError for missing API keys
    Graceful fallback for JSON parse failures

Layer 3: server.py
    Every @mcp.tool() wraps calls in try/except:
    - ValueError → return "Error: {message}"
    - Exception → return "{tool} failed: {type}: {message}"
    Tools NEVER raise — they always return a string
```

## Testing Strategy

23 tests across 3 files, all running without API keys:

- **test_github_client.py**: Uses `respx` to mock httpx at transport level. Tests success paths, error handling (401/403/404/rate-limit), input validation, and raw response mode.
- **test_ai_tools.py**: Uses `unittest.mock.patch` on `_get_client()`. Tests structured output parsing, markdown fence stripping, fallback on invalid JSON, and missing API key handling.
- **test_server.py**: Tests tool registration count, naming conventions, health check orchestration (verifies all 5 functions are called), and partial failure handling.

```bash
python -m pytest tests/ -v  # No API keys needed
```

## Future Roadmap

- **Response caching**: LRU cache for repeated repo queries (reduce API calls)
- **Pagination**: Support for fetching beyond the current 20-30 result limit
- **OAuth flow**: Multi-user authentication beyond personal access tokens
- **More structured outputs**: Extend Pydantic models to other AI tools
- **Streaming responses**: Stream long AI outputs back to the MCP client
