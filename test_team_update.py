"""Quick test script for Team field updates - bypasses MCP server"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # Check environment variables first
    if not os.getenv("JIRA_SERVER_URL"):
        print("ERROR: JIRA_SERVER_URL not set")
        print("Run with: set JIRA_SERVER_URL=https://your-jira.atlassian.net")
        return
    if not os.getenv("JIRA_API_TOKEN"):
        print("ERROR: JIRA_API_TOKEN not set")
        print("Run with: set JIRA_API_TOKEN=your_token")
        return

    print(f"Using JIRA_SERVER_URL: {os.getenv('JIRA_SERVER_URL')}")
    print()

    # Import after env check to avoid import errors
    from jira_mcp_server import get_team_id_by_name, update_jira_issue, get_jira_issue_details
    # Test 1: Check what get_team_id_by_name returns
    print("=" * 60)
    print("TEST: get_team_id_by_name('Security Team')")
    print("=" * 60)
    result = get_team_id_by_name("Security Team")
    print(f"Result: {result}")
    print()

    if result.get("status") == "error":
        print("Team lookup failed, cannot proceed with update test")
        return

    # Test 2: Try updating the team field
    print("=" * 60)
    print("TEST: update_jira_issue('PROJECT-123', team='Security Team')")
    print("=" * 60)
    result = update_jira_issue("PROJECT-123", team="Security Team")
    print(f"Result: {result}")
    print()

    # Test 3: Verify the update by fetching the issue
    print("=" * 60)
    print("TEST: get_jira_issue_details('PROJECT-123') - verify team")
    print("=" * 60)
    result = get_jira_issue_details("PROJECT-123", include_comments=False, include_subtasks=False, include_linked_issues=False)
    if result.get("status") == "success":
        issue = result.get("issue", {})
        print(f"Team value: {issue.get('team')}")
        print(f"Summary: {issue.get('summary')}")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    main()
