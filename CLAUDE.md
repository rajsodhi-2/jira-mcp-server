# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that enables Claude AI to interact with any JIRA instance for project management and issue tracking. Built with FastMCP framework.

## Key Commands

### Running the Server

```bash
# Standard method (requires JIRA_API_TOKEN and JIRA_SERVER_URL env vars)
python jira_mcp_server.py

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
- `search_jira_issues()` - JQL-based search with optional comments, returns rank and team. Supports `team_filter` for client-side filtering by team name.
- `get_jira_issue_details()` - Single issue with subtasks, linked issues, comments, rank and team
- `add_jira_comment()` - Add a comment to an issue (uses JIRA wiki markup)
- `edit_jira_comment()` - Edit an existing comment on an issue
- `update_jira_issue()` - Update issue fields (summary, description, priority, assignee, labels, fix_versions, team)
- `rank_jira_issues()` - Rank issues before/after a reference issue using JIRA's Agile ranking API
- `reorder_jira_issues()` - Convenience function to reorder multiple issues into a specific sequence

### JQL Team Filtering Limitation
JIRA's Team field is an object type that cannot be filtered by display name in JQL queries. Queries like `Team = "Team Name"` or `Team ~ "partial"` will return 0 results.

**Solution**: Use the `team_filter` parameter in `search_jira_issues()` for client-side filtering:
```python
# Instead of JQL: Team = "Platform Team" (doesn't work)
search_jira_issues(
    jql_query="project = MYPROJECT AND status != Closed",
    max_results=25,
    team_filter="Platform"  # Case-insensitive partial match
)
```

**Pagination**: When `team_filter` is used, the function paginates through JIRA results (100 at a time) until it finds `max_results` matching issues or exhausts all results. This ensures sparse team matches are found even when spread across many pages.

**Response includes**:
- `total_issues`: Total JIRA issues matching the JQL
- `filtered_issues`: Number of issues matching the team filter (found before stopping)
- `retrieved_issues`: Number of issues returned (≤ max_results)
- `team_filter`: The filter string used

### Fields Returned
Both search and detail tools return these fields:
- Core: `key`, `summary`, `description`, `status`, `type`, `priority`, `assignee`, `reporter`, `created`, `updated`
- `fix_versions` - Array of version names
- `labels` - Array of label strings (e.g., `["BETA6", "JC_Validation_Clear"]`). Note: Labels use underscores instead of spaces (JIRA displays underscores as spaces in the web UI)
- `rank` - Lexographic string for backlog ordering (configurable field ID)
- `team` - Team name (configurable field ID)

### Helper Functions (Internal)
- `get_issue_with_relations()` - Fetches issue with expand parameters (subtasks, issuelinks)
- `get_issue_comments()` - Fetches comments for an issue
- `get_jira_field_metadata()` - Discovers custom field IDs by name (useful for finding Team field ID)

### update_jira_issue() Details
Updates issue fields. Only provided fields are updated; omitted fields remain unchanged.

**Parameters:**
- `issue_key` (required) - JIRA issue key (e.g., "PROJECT-123")
- `summary` - Issue title
- `description` - Uses JIRA wiki markup (NOT markdown)
- `priority` - "Highest", "High", "Medium", "Low", "Lowest"
- `assignee` - Username. Use empty string `""` to unassign
- `labels` - Array of strings. REPLACES all existing labels. Use underscores for multi-word labels (e.g., `"JC_Validation_Clear"` not `"JC Validation Clear"`)
- `fix_versions` - Array of version names. REPLACES existing. ⚠️ Coordinate with release managers
- `team` - Team name. Uses custom field ID from `JIRA_TEAM_FIELD` env var

**Example:**
```python
# Update single field
update_jira_issue("PROJECT-123", summary="New Title")

# Update multiple fields
update_jira_issue("PROJECT-123",
    summary="Updated Title",
    priority="High",
    labels=["urgent", "bug"])

# Unassign issue
update_jira_issue("PROJECT-123", assignee="")
```

**Returns:** Updated issue data on success, or error message on failure

### rank_jira_issues() Details
Ranks issues before or after a reference issue using JIRA's Agile ranking API (`PUT /rest/agile/1.0/issue/rank`).

**Parameters:**
- `issue_keys` (required) - List of issue keys to move (max 50)
- `rank_before` - Place issues BEFORE this issue (higher priority)
- `rank_after` - Place issues AFTER this issue (lower priority)

Note: Specify exactly one of `rank_before` or `rank_after`.

**Example:**
```python
# Move single issue before another
rank_jira_issues(["PROJECT-100"], rank_before="PROJECT-50")

# Move multiple issues after a reference
rank_jira_issues(["PROJECT-5", "PROJECT-6"], rank_after="PROJECT-2")
```

**Returns:**
- `status: "success"` - All issues ranked successfully
- `status: "partial"` - Some issues failed (207 response), includes `successes` and `failures` arrays
- `status: "error"` - Complete failure with error message

**Permissions:** Requires "Schedule Issues" permission in JIRA.

### reorder_jira_issues() Details
Convenience function to reorder multiple issues into a specific sequence by chaining rank operations.

**Parameters:**
- `issue_keys` (required) - Issues in desired order (first = highest priority)
- `after_issue` (optional) - Reference issue to place all issues after

**Example:**
```python
# Reorder issues in sequence (first issue becomes highest priority)
reorder_jira_issues([
    "PROJECT-100",  # First (highest priority)
    "PROJECT-101",  # Second
    "PROJECT-102",  # Third
])

# Place issues after a reference point
reorder_jira_issues(["PROJECT-5", "PROJECT-6"], after_issue="PROJECT-1")
```

**Returns:** Success/error status with `operations_completed` count

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
- `JIRA_RANK_FIELD` (optional) - Custom field ID for rank (default: `customfield_10000`)
- `JIRA_TEAM_FIELD` (optional) - Custom field ID for team (default: `customfield_10803`)
- `ANTHROPIC_API_KEY` (optional) - Only needed for util.py LLM calls

### Custom Field IDs by JIRA Instance
Different JIRA instances use different custom field IDs for rank and team. To discover your instance's field IDs, query `/rest/api/2/field` and look for fields named "Rank" and "Team".

Example configurations:
| JIRA Instance | Rank Field | Team Field |
|---------------|------------|------------|
| Primary instance | `customfield_10000` | `customfield_10803` |
| Secondary instance | `customfield_10100` | `customfield_11204` |

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

### Primary JIRA Instance
```json
{
  "mcpServers": {
    "jira": {
      "command": "path/to/venv/Scripts/python.exe",
      "args": ["path/to/jira_mcp_server.py"],
      "env": {
        "JIRA_SERVER_URL": "https://your-jira-instance.atlassian.net",
        "JIRA_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Secondary JIRA Instance (with custom field IDs)
If your second JIRA instance uses different custom field IDs:
```json
{
  "mcpServers": {
    "jira-secondary": {
      "command": "path/to/venv/Scripts/python.exe",
      "args": ["path/to/jira_mcp_server.py"],
      "env": {
        "JIRA_SERVER_URL": "https://your-secondary-jira.atlassian.net",
        "JIRA_API_TOKEN": "your_token_here",
        "JIRA_RANK_FIELD": "customfield_XXXXX",
        "JIRA_TEAM_FIELD": "customfield_YYYYY"
      }
    }
  }
}
```

## Claude Code Integration

Claude Code stores global MCP server settings in:

**Windows**: `C:\Users\<username>\.claude.json` (in the `mcpServers` section)
**macOS/Linux**: `~/.claude.json`

You can also use per-project settings in `.claude/settings.local.json` within your project directory.

### Primary JIRA Instance
Add to the `mcpServers` section:
```json
{
  "mcpServers": {
    "jira": {
      "type": "stdio",
      "command": "path/to/venv/Scripts/python.exe",
      "args": ["path/to/jira_mcp_server.py"],
      "env": {
        "JIRA_SERVER_URL": "https://your-jira-instance.atlassian.net",
        "JIRA_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Secondary JIRA Instance (with custom field IDs)
If your second JIRA instance uses different custom field IDs:
```json
{
  "mcpServers": {
    "jira-secondary": {
      "type": "stdio",
      "command": "path/to/venv/Scripts/python.exe",
      "args": ["path/to/jira_mcp_server.py"],
      "env": {
        "JIRA_SERVER_URL": "https://your-secondary-jira.atlassian.net",
        "JIRA_API_TOKEN": "your_token_here",
        "JIRA_RANK_FIELD": "customfield_XXXXX",
        "JIRA_TEAM_FIELD": "customfield_YYYYY"
      }
    }
  }
}
```

**Note**: You can configure multiple JIRA instances simultaneously - use different server names (e.g., `jira` vs `jira-secondary`).

## Performance Notes

The server optimizes API calls:
- **Before**: 4 API calls (issue + subtasks query + links query + comments)
- **After**: 2 API calls (issue with expand + comments)
- **Savings**: 50% reduction using `?expand=subtasks,issuelinks`

No built-in rate limiting. JIRA Cloud limits: ~300 req/min per user, ~100k req/day per app.
