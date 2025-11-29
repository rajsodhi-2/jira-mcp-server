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
- ✅ Handling issues with no relations
- ✅ Optional parameter combinations
- ✅ Error handling (404, API errors, exceptions)
- ✅ Input validation
- ✅ Missing authentication token
- ✅ Backward compatibility

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

Avoid:
- Admin permissions
- Issue creation/modification (unless needed)
- Project administration

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

### Version 2.0 (Current)
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
