# JIRA MCP Server

A Model Context Protocol (MCP) server that enables Claude AI to interact with JIRA for project management, issue tracking, and release planning. This server provides seamless integration between Claude and your JIRA instance.

## Features

### MCP Tools

#### 1. `search_jira_issues`
Search for JIRA issues using JQL (JIRA Query Language).

**Parameters:**
- `jql_query` (str, required): JQL query string
- `max_results` (int, optional): Maximum number of results (default: 100)
- `include_comments` (bool, optional): Include issue comments (default: False)

**Example:**
```python
search_jira_issues(
    jql_query="project = MYPROJECT AND status != Closed",
    max_results=50,
    include_comments=True
)
```

#### 2. `get_jira_issue_details` (Enhanced)
Get comprehensive details about a specific JIRA issue, including subtasks and linked issues.

**Parameters:**
- `issue_key` (str, required): JIRA issue key (e.g., "PROJECT-123")
- `include_comments` (bool, optional): Include comments (default: True)
- `include_subtasks` (bool, optional): Include child issues/subtasks (default: True)
- `include_linked_issues` (bool, optional): Include related issues with link types (default: True)

**Returns:**
```json
{
  "status": "success",
  "message": "Retrieved issue PROJECT-123",
  "issue": {
    "key": "PROJECT-123",
    "summary": "Implement New Feature",
    "description": "Add support for the new feature...",
    "status": "In Progress",
    "type": "Story",
    "priority": "High",
    "assignee": "John Doe",
    "reporter": "Jane Smith",
    "created": "2025-01-01T10:00:00.000+0000",
    "updated": "2025-01-15T15:30:00.000+0000",
    "fix_versions": ["Release 1.0", "Release 2.0"],
    "labels": ["BETA6", "JC_Validation_Clear"],
    "comments": [
      {
        "author": "John Doe",
        "created": "2025-01-10T12:00:00.000+0000",
        "body": "Started implementation"
      }
    ],
    "subtasks": [
      {
        "key": "PROJECT-124",
        "summary": "Design API",
        "status": "Done",
        "type": "Sub-task"
      },
      {
        "key": "PROJECT-125",
        "summary": "Implement Parser",
        "status": "In Progress",
        "type": "Sub-task"
      }
    ],
    "linked_issues": [
      {
        "link_type": "blocks",
        "key": "PROJECT-100",
        "summary": "Hardware Support",
        "status": "Open"
      },
      {
        "link_type": "relates to",
        "key": "PROJECT-200",
        "summary": "Related Feature",
        "status": "In Progress"
      }
    ]
  }
}
```

**Example:**
```python
# Get full issue details with all relationships
get_jira_issue_details("PROJECT-123")

# Get issue without comments
get_jira_issue_details("PROJECT-123", include_comments=False)

# Get only basic issue info (no relations)
get_jira_issue_details(
    "PROJECT-123",
    include_comments=False,
    include_subtasks=False,
    include_linked_issues=False
)
```

#### 3. `add_jira_comment`
Add a comment to a JIRA issue.

**Parameters:**
- `issue_key` (str, required): JIRA issue key (e.g., "PROJECT-123")
- `comment_body` (str, required): Comment text in JIRA wiki markup format

**Note:** JIRA uses wiki markup, NOT markdown. See formatting rules in the docstring.

#### 4. `edit_jira_comment`
Edit an existing comment on a JIRA issue.

**Parameters:**
- `issue_key` (str, required): JIRA issue key
- `comment_id` (str, required): The ID of the comment to edit
- `comment_body` (str, required): New comment text in JIRA wiki markup format

#### 5. `update_jira_issue`
Update fields on a JIRA issue. Only fields that are explicitly provided will be updated.

**Parameters:**
- `issue_key` (str, required): JIRA issue key (e.g., "PROJECT-123")
- `summary` (str, optional): New issue title/summary
- `description` (str, optional): New description in JIRA wiki markup format
- `priority` (str, optional): Priority name - "Highest", "High", "Medium", "Low", "Lowest"
- `assignee` (str, optional): Username or account ID. Use empty string `""` to unassign
- `labels` (list, optional): Array of label strings. **REPLACES** all existing labels
  - Note: JIRA labels cannot contain spaces — use underscores (e.g., `"JC_Validation_Clear"`). JIRA's web UI displays underscores as spaces.
- `fix_versions` (list, optional): Array of version names. **REPLACES** existing versions
  - ⚠️ **WARNING:** Fix versions are typically managed by release managers
- `team` (str, optional): Team name (uses configurable custom field ID)

**Example:**
```python
# Update single field
update_jira_issue("PROJECT-123", summary="New Title")

# Update multiple fields
update_jira_issue(
    "PROJECT-123",
    summary="Updated Title",
    priority="High",
    description="New description with *bold* text"
)

# Update labels (replaces all existing)
update_jira_issue("PROJECT-123", labels=["bug", "urgent"])

# Unassign issue
update_jira_issue("PROJECT-123", assignee="")

# Update team
update_jira_issue("PROJECT-123", team="Platform Team")
```

**Returns:**
```json
{
  "status": "success",
  "message": "Updated PROJECT-123: summary, priority",
  "updated_fields": ["summary", "priority"],
  "issue": {
    "key": "PROJECT-123",
    "summary": "Updated Title",
    ...
  }
}
```

#### 6. `rank_jira_issues`
Rank (reorder) one or more JIRA issues relative to another issue using JIRA's Agile ranking API.

**Parameters:**
- `issue_keys` (list, required): List of issue keys to move (max 50)
- `rank_before` (str, optional): Rank the issues BEFORE this issue key (higher priority)
- `rank_after` (str, optional): Rank the issues AFTER this issue key (lower priority)

**Note:** Specify exactly one of `rank_before` or `rank_after`.

**Example:**
```python
# Move single issue to top of backlog (before first issue)
rank_jira_issues(["PROJECT-10"], rank_before="PROJECT-1")

# Move multiple issues after a specific issue
rank_jira_issues(["PROJECT-5", "PROJECT-6", "PROJECT-7"], rank_after="PROJECT-2")
```

**Returns:**
- `status: "success"` - All issues ranked successfully
- `status: "partial"` - Some issues failed (includes `successes` and `failures` arrays)
- `status: "error"` - Complete failure with error message

**Permissions:** Requires "Schedule Issues" permission in JIRA.

#### 7. `reorder_jira_issues`
Convenience function to reorder multiple issues into a specific sequence by chaining rank operations.

**Parameters:**
- `issue_keys` (list, required): Issues in desired order (first = highest priority)
- `after_issue` (str, optional): Reference issue to place all issues after

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

### Key Enhancements

#### 🎯 Single API Call Efficiency
The enhanced `get_jira_issue_details` uses JIRA's expand parameters to fetch issue details, subtasks, and linked issues in a single API call, reducing latency and API usage.

#### 🔗 Automatic Relationship Resolution
No need for separate JQL queries like:
- ❌ `parent = PROJECT-123` (for subtasks)
- ❌ `issue in linkedIssues(PROJECT-123)` (for linked issues)

Everything is fetched automatically!

#### 🎛️ Flexible Options
Choose exactly what data you need with granular control over comments, subtasks, and linked issues.

## Installation

### Prerequisites
- Python 3.8+
- JIRA API Bearer token

### Setup

1. **Clone or download the repository**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Key dependencies:
- `fastmcp==0.4.1` - MCP server framework
- `mcp==1.5.0` - Model Context Protocol SDK
- `requests==2.32.3` - HTTP client for JIRA API

3. **Set up environment variables:**

Create a `.env` file or set environment variables:
```bash
export JIRA_SERVER_URL="https://your-jira-instance.atlassian.net"
export JIRA_API_TOKEN="your_jira_bearer_token_here"
```

On Windows:
```cmd
set JIRA_SERVER_URL=https://your-jira-instance.atlassian.net
set JIRA_API_TOKEN=your_jira_bearer_token_here
```

### Getting Your JIRA API Token

1. Log in to your JIRA instance
2. Navigate to Profile → Personal Access Tokens
3. Create a new token with appropriate permissions
4. Copy the token and store it securely

**Required Permissions:**
- Read issues
- Browse projects
- View comments

## Usage

### Starting the MCP Server

```bash
python jira_mcp_tool.py
```

The server will start and listen for MCP protocol messages from Claude.

### Using with Claude Desktop

Add to your Claude Desktop MCP configuration:

**macOS/Linux:** `~/.config/claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jira": {
      "command": "python",
      "args": ["/path/to/jira_mcp_server.py"],
      "env": {
        "JIRA_SERVER_URL": "https://your-jira-instance.atlassian.net",
        "JIRA_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Example Workflows

#### 1. Finding and Analyzing Issues
```
User: "Find all high-priority bugs in my project that are still open"

Claude uses: search_jira_issues(
    jql_query="project = MYPROJECT AND type = Bug AND priority = High AND status = Open"
)
```

#### 2. Getting Complete Issue Context
```
User: "Show me all details about PROJECT-123 including what it blocks and its subtasks"

Claude uses: get_jira_issue_details("PROJECT-123")

Result includes:
- Issue details
- All subtasks
- All linked issues (blocks, is blocked by, relates to, etc.)
- Comments
```

#### 3. Release Planning Analysis
```
User: "Analyze the completion status of PROJECT-123 and its dependencies"

Claude uses:
1. get_jira_issue_details("PROJECT-123") - gets issue with all relations
2. Analyzes subtasks completion
3. Checks linked issues status
4. Provides comprehensive report
```

#### 4. Safe Label Operations
```
User: "Add the 'reviewed' label to PROJECT-123 without removing existing labels"

Claude uses:
1. get_jira_issue_details("PROJECT-123") - read current labels
2. Append new label: current_labels + ["reviewed"]
3. update_jira_issue("PROJECT-123", labels=new_labels)

This prevents accidentally wiping out existing labels like "BETA6" or "urgent"
```

#### 5. Backlog Reordering
```
User: "Reorder these issues so they're prioritized in this order: PROJECT-100, PROJECT-101, PROJECT-102"

Claude uses: reorder_jira_issues([
    "PROJECT-100",  # Highest priority
    "PROJECT-101",  # Second
    "PROJECT-102"   # Third
])

Result: Issues are ranked in sequence in the backlog
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────┐
│            Claude AI Assistant                   │
└─────────────────┬───────────────────────────────┘
                  │ MCP Protocol
                  ▼
┌─────────────────────────────────────────────────┐
│          FastMCP Server Framework                │
│  ┌───────────────────────────────────────────┐  │
│  │  @mcp.tool()                              │  │
│  │  - search_jira_issues()                   │  │
│  │  - get_jira_issue_details()               │  │
│  │  - add_jira_comment()                     │  │
│  │  - edit_jira_comment()                    │  │
│  │  - update_jira_issue()                    │  │
│  │  - rank_jira_issues()                     │  │
│  │  - reorder_jira_issues()                  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │ HTTPS/Bearer Token
                  ▼
┌─────────────────────────────────────────────────┐
│         JIRA REST API v2                         │
│  - /rest/api/2/search (JQL queries)             │
│  - /rest/api/2/issue/{key}?expand=...           │
│  - /rest/api/2/issue/{key}/comment              │
└─────────────────────────────────────────────────┘
```

### API Endpoints Used

| Function | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| `search_jira_issues` | `/rest/api/2/search` | GET | JQL-based issue search |
| `get_issue_with_relations` | `/rest/api/2/issue/{key}?expand=subtasks,issuelinks` | GET | Single issue with relations |
| `get_issue_comments` | `/rest/api/2/issue/{key}/comment` | GET | Issue comments |
| `add_jira_comment` | `/rest/api/2/issue/{key}/comment` | POST | Add comment |
| `edit_jira_comment` | `/rest/api/2/issue/{key}/comment/{id}` | PUT | Edit comment |
| `update_jira_issue` | `/rest/api/2/issue/{key}` | PUT | Update issue fields |
| `rank_jira_issues` | `/rest/agile/1.0/issue/rank` | PUT | Rank issues in backlog |

### Data Flow

```
get_jira_issue_details("PROJECT-123", include_subtasks=True, include_linked_issues=True)
    │
    ├─→ get_issue_with_relations()
    │       │
    │       └─→ GET /rest/api/2/issue/PROJECT-123?expand=subtasks,issuelinks
    │               │
    │               └─→ Returns: issue + subtasks + linked issues
    │
    ├─→ get_issue_comments()
    │       │
    │       └─→ GET /rest/api/2/issue/PROJECT-123/comment
    │               │
    │               └─→ Returns: comments list
    │
    └─→ Combine data and return comprehensive response
```

## Testing

### Running Unit Tests

```bash
# Using pytest
python -m pytest test_jira_mcp_tool.py -v

# Using unittest
python -m unittest test_jira_mcp_tool.py
```

### Test Coverage

The test suite covers:
- ✅ Fetching issues with subtasks
- ✅ Fetching issues with linked issues
- ✅ Fetching issues with labels
- ✅ Handling issues with no relations
- ✅ Optional parameter combinations
- ✅ Error handling (404, API errors, exceptions)
- ✅ Input validation
- ✅ Missing authentication token
- ✅ Backward compatibility
- ✅ Issue ranking (single and bulk)
- ✅ Batch reordering operations

### Manual Testing

Test the server with real JIRA issues:

```bash
# Start the server
python jira_mcp_server.py

# In Claude Desktop, try:
# "Get details about PROJECT-123"
# "Find all open bugs in project MYPROJECT"
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_SERVER_URL` | Yes | Your JIRA instance URL (e.g., `https://your-company.atlassian.net`) |
| `JIRA_API_TOKEN` | Yes | Bearer token for JIRA authentication |

## Development

### Project Structure

```
.
├── jira_mcp_server.py        # Main MCP server implementation
├── test_jira_mcp_tool.py     # Unit tests
├── util.py                   # Utility functions
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── LICENSE                   # MIT License
└── .env                      # Environment variables (git-ignored)
```

### Adding New Tools

To add a new MCP tool:

1. Define function with `@mcp.tool()` decorator:
```python
@mcp.tool()
def my_new_tool(param: str) -> Dict[str, Any]:
    """Tool description for Claude."""
    # Implementation
    return {"status": "success", "data": ...}
```

2. Add tests in `test_jira_mcp_tool.py`

3. Update this README

### Code Style

- Type hints for all function parameters and returns
- Comprehensive docstrings (Google style)
- Error handling with try/except blocks
- Null-safe field extraction from JIRA responses

## Troubleshooting

### Common Issues

#### Authentication Errors
```
Error: JIRA_API_TOKEN not found in environment variables
```
**Solution:** Set the `JIRA_API_TOKEN` environment variable.

#### Connection Errors
```
Error: JIRA API error: 401 - Unauthorized
```
**Solution:**
- Check that your token is valid
- Ensure the token has required permissions
- Verify the token hasn't expired

#### Missing JIRA Server URL
```
Error: JIRA_SERVER_URL not found in environment variables
```
**Solution:** Set the `JIRA_SERVER_URL` environment variable to your JIRA instance URL.

#### 404 Errors
```
Error: Issue PROJECT-123 not found
```
**Solution:**
- Verify the issue key is correct
- Check you have permission to view the issue
- Ensure the issue exists in JIRA

#### Import Errors
```
ModuleNotFoundError: No module named 'fastmcp'
```
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Debug Mode

To enable debug output, uncomment the print statement in `jira_mcp_server.py`:
```python
if __name__ == "__main__":
    print("Starting JIRA MCP Server...")  # Uncomment for debug
    mcp.run()
```

## Security Considerations

### Token Storage
- ✅ Store tokens in environment variables or secure secret management
- ❌ Never commit tokens to version control
- ❌ Never hardcode tokens in source files

### API Permissions
Grant minimal required permissions:
- Read issues
- Browse projects
- View comments
- Edit issues (required for `update_jira_issue`)
- Add comments (required for `add_jira_comment`)

Avoid:
- Admin permissions
- Issue creation (unless needed)
- Project administration
- Delete permissions

### Network Security
- All API calls use HTTPS
- Bearer token authentication
- No credentials stored in code

## Performance

### API Call Optimization

The enhanced `get_jira_issue_details` reduces API calls:

**Before:**
```
1. GET /rest/api/2/search (get issue)
2. GET /rest/api/2/search?jql=parent=PROJECT-123 (get subtasks)
3. GET /rest/api/2/search?jql=issue in linkedIssues(...) (get links)
4. GET /rest/api/2/issue/{key}/comment (get comments)
Total: 4 API calls
```

**After:**
```
1. GET /rest/api/2/issue/{key}?expand=subtasks,issuelinks (get all)
2. GET /rest/api/2/issue/{key}/comment (get comments)
Total: 2 API calls (50% reduction)
```

### Rate Limiting

JIRA Cloud typically limits:
- ~300 requests per minute per user
- ~100,000 requests per day per app

This server includes no built-in rate limiting. For high-volume usage, consider adding:
- Request throttling
- Response caching
- Exponential backoff

## Changelog

### Version 2.2 (Current)
**Backlog Ranking & Labels Support**
- ✨ Added `rank_jira_issues()` tool for ranking issues using JIRA's Agile API
- ✨ Added `reorder_jira_issues()` convenience tool for batch reordering
- ✨ Added `labels` field to `search_jira_issues()` and `get_jira_issue_details()` responses
- 🎯 Enables safe "read → append → write" workflow for labels
- ⚡ Bulk ranking supports up to 50 issues per call
- ✅ 22 new unit tests for ranking and labels functionality

### Version 2.1
**Issue Editing Capability**
- ✨ Added `update_jira_issue()` tool for updating issue fields
- ✨ Added `get_jira_field_metadata()` helper for discovering custom field IDs
- 🎛️ Supports: summary, description, priority, assignee, labels, fix_versions, team
- ⚠️ Fix versions include warning about release management coordination
- 📝 Only updates provided fields; omitted fields unchanged
- ✅ 17 new unit tests for update functionality

### Version 2.0
**Enhanced get_jira_issue_details**
- ✨ Added automatic subtask retrieval
- ✨ Added automatic linked issues retrieval
- ✨ Added optional parameters for granular control
- ⚡ Optimized to use single API call with expand parameters
- 📝 Comprehensive docstrings and type hints
- ✅ Full test coverage

### Version 1.0
**Initial Release**
- Basic `search_jira_issues` functionality
- Basic `get_jira_issue_details` functionality
- Bearer token authentication

## Contributing

### Guidelines

1. **Code Quality**
   - Add type hints
   - Write docstrings
   - Follow existing patterns

2. **Testing**
   - Add unit tests for new features
   - Ensure all tests pass
   - Maintain >80% coverage

3. **Documentation**
   - Update README for new features
   - Add inline comments for complex logic
   - Include usage examples

### Submitting Changes

1. Test your changes thoroughly
2. Update tests and documentation
3. Submit with clear description of changes

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
- Check the Troubleshooting section
- Review JIRA REST API documentation
- Check MCP protocol documentation at https://modelcontextprotocol.io

## References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [JIRA REST API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v2/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Claude AI](https://claude.ai)

---

**Enabling AI-powered JIRA analysis and project management**
