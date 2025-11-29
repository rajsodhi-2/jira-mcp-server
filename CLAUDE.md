# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that enables Claude AI to interact with any JIRA instance for project management and issue tracking. Built with FastMCP framework.

## Key Commands

### Running the Server

```bash
# Standard method (requires JIRA_API_TOKEN env var)
python jira_mcp_tool.py

# Using batch script (Windows)
start_jira_server.bat
```

### Running Tests

```bash
# Using unittest (built-in, no dependencies)
python -m unittest test_jira_mcp_tool.py -v

# Using pytest (if installed)
python -m pytest test_jira_mcp_tool.py -v
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies: `fastmcp==0.4.1`, `mcp==1.5.0`, `requests==2.32.3`

## Architecture

### MCP Tools (Public API)
- `search_jira_issues()` - JQL-based search with optional comments
- `get_jira_issue_details()` - Single issue with subtasks, linked issues, and comments

### Helper Functions (Internal)
- `get_issue_with_relations()` - Fetches issue with expand parameters (subtasks, issuelinks)
- `get_issue_comments()` - Fetches comments for an issue

### Data Flow Pattern
The server uses a single optimized API call pattern:
```
GET /rest/api/2/issue/{key}?expand=subtasks,issuelinks
```
This fetches issue data, subtasks, and linked issues in one request instead of three separate calls.

### JIRA API Integration
- **Authentication**: Bearer token via `JIRA_API_TOKEN` environment variable
- **Base URL**: Configured via `JIRA_SERVER_URL` environment variable (required)
- **API Version**: JIRA REST API v2

## Critical Implementation Details

### JIRA Issue Links Have Direction
Issue links have `inwardIssue` or `outwardIssue` with different semantics:
```python
# jira_mcp_tool.py:323-331
if 'outwardIssue' in link:
    linked_issue = link.get('outwardIssue', {})
    link_description = link_type.get('outward', '')  # "blocks"
elif 'inwardIssue' in link:
    linked_issue = link.get('inwardIssue', {})
    link_description = link_type.get('inward', '')   # "is blocked by"
```

### Null Field Handling Pattern
Many JIRA fields can be null. Use this defensive pattern:
```python
# Safe - checks existence before accessing nested properties
assignee = fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else ''

# Unsafe - will throw AttributeError if assignee is None
assignee = fields.get('assignee', {}).get('displayName', '')
```

Fields that can be null: `assignee`, `reporter`, `description`, `priority`, `status`, custom fields

### Expand Parameters
JIRA's expand parameter is comma-separated, NO spaces:
```python
# Correct
endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}?expand=subtasks,issuelinks"

# Wrong - spaces break it
endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}?expand=subtasks, issuelinks"
```

## Code Conventions

### Type Hints and Docstrings
All functions use:
- Type hints: `def function(param: str, optional: bool = True) -> Dict[str, Any]:`
- Google-style docstrings with Args and Returns sections
- Return type: `Dict[str, Any]` for consistency

### Response Format
All MCP tools return consistent structure:
```python
# Success
{"status": "success", "message": "...", "data": {...}}

# Error
{"status": "error", "message": "..."}
```

### Error Handling Layers
1. HTTP status checks (404, 401, 500, etc.)
2. Data validation
3. Exception catching with try/except

## Testing Strategy

Tests use `unittest.mock` to mock HTTP requests:
```python
@patch('jira_mcp_tool.requests.get')
def test_function(self, mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {...}
    mock_get.return_value = mock_response
```

**Important**: Patch where the function is USED, not where it's defined:
- ✅ `@patch('jira_mcp_tool.requests.get')`
- ❌ `@patch('requests.get')`

Test coverage includes: success cases, error handling (404, API errors, exceptions), null values, optional parameters, backward compatibility.

## Adding New MCP Tools

1. Define with `@mcp.tool()` decorator
2. Add type hints and comprehensive docstring (Claude sees this)
3. Implement with consistent error handling
4. Return `{"status": "success/error", ...}` format
5. Write unit tests with mocked responses
6. Update README.md

Template:
```python
@mcp.tool()
def my_tool(param: str, optional: bool = True) -> Dict[str, Any]:
    """
    Tool description for Claude.

    Args:
        param: Description
        optional: Description (optional)

    Returns:
        dict: Response with status and data
    """
    # Validate input
    if not param:
        return {"status": "error", "message": "Invalid input"}

    # Get credentials
    token = os.getenv("JIRA_API_TOKEN")
    if not token:
        return {"status": "error", "message": "Token not found"}

    try:
        # Implementation
        pass
    except Exception as e:
        return {"status": "error", "message": f"Exception: {str(e)}"}

    return {"status": "success", "data": result}
```

## Configuration

### Environment Variables
- `JIRA_SERVER_URL` (required) - Your JIRA instance URL (e.g., `https://your-company.atlassian.net`)
- `JIRA_API_TOKEN` (required) - Bearer token for authentication
- `ANTHROPIC_API_KEY` (optional) - Only needed for util.py LLM calls

## File Structure

```
├── jira_mcp_tool.py          # Main MCP server (2 tools, 2 helpers)
├── test_jira_mcp_tool.py     # Unit tests with mocks
├── util.py                   # LLM utility functions (llm_call, extract_xml)
├── requirements.txt          # Python dependencies
├── start_jira_server.bat     # Windows batch script to start server
├── README.md                 # User documentation
├── Claude.md                 # Detailed development notes (legacy)
└── *.ipynb                   # Jupyter notebooks for experiments
```

## Common Issues

### Module Not Found Errors
Ensure dependencies are installed: `pip install -r requirements.txt`

### Authentication Errors
- Verify `JIRA_API_TOKEN` is set
- Check token hasn't expired
- Ensure token has permissions: read issues, browse projects, view comments

### 404 Errors
- Verify issue key is correct (e.g., "PROJECT-123")
- Check you have permission to view the issue

## Claude Desktop Integration

Add to `claude_desktop_config.json`:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS/Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jira": {
      "command": "python",
      "args": ["/path/to/jira_mcp_server.py"],
      "env": {
        "JIRA_SERVER_URL": "https://your-company.atlassian.net",
        "JIRA_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Performance Notes

The server optimizes API calls:
- **Before**: 4 API calls (issue + subtasks query + links query + comments)
- **After**: 2 API calls (issue with expand + comments)
- **Savings**: 50% reduction using `?expand=subtasks,issuelinks`

No built-in rate limiting. JIRA Cloud limits: ~300 req/min per user, ~100k req/day per app.
