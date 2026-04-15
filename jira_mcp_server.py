# jira_mcp_server.py
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

# Import FastMCP from the official MCP Python SDK
from mcp.server.fastmcp import FastMCP

# Create FastMCP server
mcp = FastMCP("jira_mcp_server")

# Configurable custom field IDs (different JIRA instances may use different field IDs)
# Check your JIRA instance's field configuration via /rest/api/2/field to find the correct IDs
def get_rank_field_id() -> str:
    """Get the rank custom field ID from environment or use default."""
    return os.getenv("JIRA_RANK_FIELD", "customfield_10000")

def get_team_field_id() -> str:
    """Get the team custom field ID from environment or use default."""
    return os.getenv("JIRA_TEAM_FIELD", "customfield_10803")


def get_team_id_by_name(
    team_name: str,
    token: str = None,
    jira_url: str = None,
    max_issues_to_search: int = 1000
) -> Dict[str, Any]:
    """
    Look up a JIRA team's ID by its display name.

    The Team field in JIRA stores data as {"id": "uuid", "name": "Team Name"}.
    When updating issues, JIRA requires the team ID, not the name.
    This helper searches for issues with teams assigned and extracts the team ID
    from the raw field data. Uses pagination to find teams that may only have
    a few issues assigned.

    Args:
        team_name: The display name of the team (e.g., "Platform Team")
        token: JIRA API token (optional, uses env var if not provided)
        jira_url: JIRA server URL (optional, uses env var if not provided)
        max_issues_to_search: Maximum issues to search through (default: 1000)

    Returns:
        dict: On success: {"status": "success", "team_id": "...", "team_name": "..."}
              On failure: {"status": "error", "message": "..."}
    """
    # Get credentials from params or environment
    if not token:
        token = os.getenv("JIRA_API_TOKEN")
    if not jira_url:
        jira_url = os.getenv("JIRA_SERVER_URL")

    if not token:
        return {"status": "error", "message": "JIRA_API_TOKEN not found"}
    if not jira_url:
        return {"status": "error", "message": "JIRA_SERVER_URL not found"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    team_field = get_team_field_id()
    team_name_lower = team_name.lower().strip()

    # Search for issues with teams assigned
    # Note: JQL Team filtering doesn't work by name, so we search for non-empty
    # teams and filter client-side
    endpoint = f"{jira_url}/rest/api/2/search"

    # Track all unique teams found during pagination
    found_teams = {}  # name -> id mapping

    start_at = 0
    batch_size = 100  # Fetch 100 issues per API call
    total_issues = None
    total_searched = 0

    try:
        # Paginate through issues until we find the team or hit limits
        while total_searched < max_issues_to_search:
            params = {
                "jql": "Team is not EMPTY ORDER BY updated DESC",
                "startAt": start_at,
                "maxResults": batch_size,
                "fields": team_field
            }

            response = requests.get(endpoint, headers=headers, params=params)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"JIRA API error: {response.status_code}"
                }

            data = response.json()

            # Get total on first request
            if total_issues is None:
                total_issues = data.get("total", 0)

            issues = data.get("issues", [])

            # No more results
            if not issues:
                break

            total_searched += len(issues)

            # Search through this batch of issues
            for issue in issues:
                fields = issue.get("fields", {})
                team_obj = fields.get(team_field)

                if isinstance(team_obj, dict) and team_obj.get("name"):
                    found_name = team_obj.get("name", "")
                    team_id = team_obj.get("id", "")

                    # Track this team
                    if found_name not in found_teams:
                        found_teams[found_name] = team_id

                    # Check for match
                    if found_name.lower().strip() == team_name_lower:
                        return {
                            "status": "success",
                            "team_id": team_id,
                            "team_name": found_name
                        }

            # Move to next batch
            start_at += batch_size

            # Stop if we've searched all available issues
            if start_at >= total_issues:
                break

        # Team not found - provide helpful message with all discovered teams
        available_teams = sorted(found_teams.keys())

        return {
            "status": "error",
            "message": f"Team '{team_name}' not found after searching {total_searched} issues. Available teams ({len(available_teams)} found): {', '.join(available_teams)}"
        }

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}


@mcp.tool()
def search_jira_issues(
    jql_query: str,
    max_results: int = 100,
    include_comments: bool = False,
    team_filter: str = None
) -> Dict[str, Any]:
    """
    Search for JIRA issues using JQL and return matching issues.

    This tool allows Claude to search for JIRA issues using JQL (JIRA Query Language)
    and retrieve details about those issues including summaries, descriptions,
    statuses, and optionally comments.

    Args:
        jql_query (str): A JQL query string to search for issues.
            Example: "project = MYPROJECT AND status != Closed AND type = Request"
        max_results (int, optional): Maximum number of results to return. Defaults to 100.
        include_comments (bool, optional): Whether to include issue comments. Defaults to False.
        team_filter (str, optional): Filter results by team name (case-insensitive partial match).
            Use this instead of Team in JQL since JQL cannot filter by team display name.
            Example: "Platform" matches "Platform Team" or "Platform Services Team"

    Returns:
        dict: A dictionary with matching issues
    """
    # Input validation
    if not jql_query or not isinstance(jql_query, str):
        return {
            "status": "error",
            "message": "Invalid JQL query. Please provide a valid JQL query string."
        }
    
    if not isinstance(max_results, int) or max_results <= 0:
        return {
            "status": "error",
            "message": "Invalid max_results. Please provide a positive integer."
        }
    
    # Get JIRA URL from environment (required)
    jira_url = os.getenv("JIRA_SERVER_URL")

    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL not found in environment variables. Please set this variable to your JIRA instance URL (e.g., https://your-company.atlassian.net)."
        }

    # Get API token from environment variables
    token = os.getenv("JIRA_API_TOKEN")

    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN not found in environment variables. Please set this variable."
        }
    
    # Set up the headers with Bearer authentication
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # API endpoint for search
    endpoint = f"{jira_url}/rest/api/2/search"

    # Get configurable custom field IDs
    rank_field = get_rank_field_id()
    team_field = get_team_field_id()

    # Fields to retrieve - includes description/text field, fixVersions, labels, rank, and team
    fields = f"summary,description,status,assignee,reporter,created,updated,priority,issuetype,fixVersions,labels,{rank_field},{team_field}"
    
    # Helper function to parse a single issue from JIRA response
    def parse_issue(issue: Dict) -> Dict[str, Any]:
        key = issue.get('key')
        issue_fields = issue.get('fields', {})

        # Extract field values with error handling
        summary = issue_fields.get('summary', '')
        description = issue_fields.get('description', '')
        status = issue_fields.get('status', {}).get('name', '') if issue_fields.get('status') else ''

        # Handle nullable objects
        assignee = issue_fields.get('assignee', {}).get('displayName', '') if issue_fields.get('assignee') else ''
        reporter = issue_fields.get('reporter', {}).get('displayName', '') if issue_fields.get('reporter') else ''

        # Handle timestamps
        created = issue_fields.get('created', '')
        updated = issue_fields.get('updated', '')

        # Get issue type and priority
        issue_type = issue_fields.get('issuetype', {}).get('name', '') if issue_fields.get('issuetype') else ''
        priority = issue_fields.get('priority', {}).get('name', '') if issue_fields.get('priority') else ''

        # Extract fix versions (convert from array of objects to array of names)
        fix_versions = []
        if issue_fields.get('fixVersions'):
            fix_versions = [version.get('name', '') for version in issue_fields.get('fixVersions', [])]

        # Extract rank - lexographic string for backlog ordering
        rank_value = issue_fields.get(rank_field)
        # Handle case where rank might be a string or None
        if isinstance(rank_value, str):
            rank = rank_value
        else:
            rank = ''

        # Extract team - object with id and name
        team_obj = issue_fields.get(team_field)
        # Handle case where team might be an object with 'name' or might be None/other
        if isinstance(team_obj, dict) and 'name' in team_obj:
            team = team_obj.get('name', '')
        else:
            team = ''

        # Fetch comments if requested
        comments = []
        if include_comments:
            comments = get_issue_comments(key, token, jira_url)

        # Extract labels (array of strings)
        labels = issue_fields.get('labels', [])

        return {
            'key': key,
            'summary': summary,
            'description': description,
            'status': status,
            'type': issue_type,
            'priority': priority,
            'assignee': assignee,
            'reporter': reporter,
            'created': created,
            'updated': updated,
            'fix_versions': fix_versions,
            'labels': labels,
            'rank': rank,
            'team': team,
            'comments': comments if include_comments else None
        }

    try:
        # If team_filter is provided, use pagination to find enough matches
        if team_filter:
            team_filter_lower = team_filter.lower()
            filtered_issues = []
            start_at = 0
            batch_size = 100  # Fetch 100 issues per API call
            total_issues = None
            total_scanned = 0

            # Paginate through results until we have enough matches or exhausted all results
            while len(filtered_issues) < max_results:
                params = {
                    "jql": jql_query,
                    "startAt": start_at,
                    "maxResults": batch_size,
                    "fields": fields
                }

                response = requests.get(endpoint, headers=headers, params=params)

                if response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"JIRA API error: {response.status_code} - {response.text}"
                    }

                data = response.json()

                # Get total on first request
                if total_issues is None:
                    total_issues = data.get('total', 0)

                batch_issues = data.get('issues', [])
                total_scanned += len(batch_issues)

                # No more results
                if not batch_issues:
                    break

                # Parse and filter this batch
                for issue in batch_issues:
                    parsed = parse_issue(issue)
                    if parsed.get('team') and team_filter_lower in parsed['team'].lower():
                        filtered_issues.append(parsed)
                        # Stop if we have enough
                        if len(filtered_issues) >= max_results:
                            break

                # Move to next batch
                start_at += batch_size

                # Stop if we've scanned all issues
                if start_at >= total_issues:
                    break

            # Truncate to max_results (in case we got more)
            filtered_total = len(filtered_issues)
            filtered_issues = filtered_issues[:max_results]
            retrieved_issues = len(filtered_issues)

            return {
                "status": "success",
                "message": f"Retrieved {retrieved_issues} issues (filtered from {filtered_total} matches by team '{team_filter}', scanned {total_scanned} of {total_issues} total)",
                "total_issues": total_issues,
                "filtered_issues": filtered_total,
                "retrieved_issues": retrieved_issues,
                "team_filter": team_filter,
                "issues": filtered_issues
            }

        # No team_filter - simple single request
        params = {
            "jql": jql_query,
            "maxResults": max_results,
            "fields": fields
        }

        response = requests.get(endpoint, headers=headers, params=params)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }

        # Parse the response
        data = response.json()
        total_issues = data.get('total', 0)

        # Create lists to store data
        issue_data = []

        for issue in data.get('issues', []):
            issue_data.append(parse_issue(issue))

        retrieved_issues = len(issue_data)

        # Return structured response (no team filter)
        return {
            "status": "success",
            "message": f"Retrieved {retrieved_issues} issues out of {total_issues} total matches",
            "total_issues": total_issues,
            "retrieved_issues": retrieved_issues,
            "issues": issue_data
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}"
        }

def get_issue_comments(issue_key: str, token: str, jira_url: str) -> List[Dict[str, str]]:
    """
    Fetch comments for a specific Jira issue.
    
    Parameters:
    -----------
    issue_key : str
        The Jira issue key (e.g. 'PROJECT-123')
    token : str
        The Jira API token
    jira_url : str
        The base URL for Jira
    
    Returns:
    --------
    list
        List of comment dictionaries with author, text, and date
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    # API endpoint for comments
    endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}/comment"
    
    try:
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        comments_list = []
        
        for comment in data.get('comments', []):
            author = comment.get('author', {}).get('displayName', '') if comment.get('author') else 'Unknown'
            created = comment.get('created', '')
            body = comment.get('body', '')
            
            comments_list.append({
                'id': comment.get('id', ''),
                'author': author,
                'created': created,
                'body': body
            })
        
        return comments_list
    
    except Exception:
        return []

def get_jira_field_metadata(
    field_name: str = None,
    token: str = None,
    jira_url: str = None
) -> Dict[str, Any]:
    """
    Get metadata about JIRA fields, optionally filtering by field name.

    This function queries the JIRA field API to discover field IDs, especially
    useful for finding custom field IDs like Team which vary between JIRA instances.

    Parameters:
    -----------
    field_name : str, optional
        If provided, filter results to fields containing this name (case-insensitive).
        Example: "Team" would match "Team", "Development Team", etc.
    token : str, optional
        The JIRA API token. If not provided, reads from JIRA_API_TOKEN env var.
    jira_url : str, optional
        The base URL for JIRA. If not provided, reads from JIRA_SERVER_URL env var.

    Returns:
    --------
    dict
        A dictionary with status and list of matching fields:
        {
            "status": "success",
            "fields": [
                {"id": "customfield_10803", "name": "Team", "custom": True, "schema": {...}},
                ...
            ]
        }
    """
    # Get credentials from params or environment
    if not token:
        token = os.getenv("JIRA_API_TOKEN")
    if not jira_url:
        jira_url = os.getenv("JIRA_SERVER_URL")

    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN not found in environment variables."
        }

    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL not found in environment variables."
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    endpoint = f"{jira_url}/rest/api/2/field"

    try:
        response = requests.get(endpoint, headers=headers)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }

        all_fields = response.json()

        # Filter by field name if provided
        if field_name:
            field_name_lower = field_name.lower()
            filtered_fields = [
                {
                    "id": f.get("id", ""),
                    "name": f.get("name", ""),
                    "custom": f.get("custom", False),
                    "schema": f.get("schema", {})
                }
                for f in all_fields
                if field_name_lower in f.get("name", "").lower()
            ]
        else:
            filtered_fields = [
                {
                    "id": f.get("id", ""),
                    "name": f.get("name", ""),
                    "custom": f.get("custom", False),
                    "schema": f.get("schema", {})
                }
                for f in all_fields
            ]

        return {
            "status": "success",
            "message": f"Found {len(filtered_fields)} fields" + (f" matching '{field_name}'" if field_name else ""),
            "fields": filtered_fields
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}"
        }


def get_issue_with_relations(
    issue_key: str,
    token: str,
    jira_url: str,
    include_subtasks: bool = True,
    include_linked_issues: bool = True
) -> Dict[str, Any]:
    """
    Fetch a single JIRA issue with optional subtasks and linked issues expanded.

    This function uses the JIRA issue endpoint with expand parameters to efficiently
    retrieve an issue along with its relationships (subtasks and linked issues) in
    a single API call.

    Parameters:
    -----------
    issue_key : str
        The JIRA issue key (e.g., 'PROJECT-123')
    token : str
        The JIRA API token for authentication
    jira_url : str
        The base URL for JIRA
    include_subtasks : bool, optional
        Whether to include subtasks in the response (default: True)
    include_linked_issues : bool, optional
        Whether to include linked issues in the response (default: True)

    Returns:
    --------
    dict
        A dictionary containing the issue data with the following structure:
        {
            'key': str,
            'summary': str,
            'description': str,
            'status': str,
            'type': str,
            'priority': str,
            'assignee': str,
            'reporter': str,
            'created': str,
            'updated': str,
            'subtasks': list (if include_subtasks=True),
            'linked_issues': list (if include_linked_issues=True)
        }
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Build expand parameter based on options
    expand_params = []
    if include_subtasks:
        expand_params.append("subtasks")
    if include_linked_issues:
        expand_params.append("issuelinks")

    expand_string = ",".join(expand_params) if expand_params else ""

    # API endpoint for single issue with expand
    endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}"
    if expand_string:
        endpoint += f"?expand={expand_string}"

    try:
        response = requests.get(endpoint, headers=headers)

        if response.status_code == 404:
            return {
                "status": "error",
                "message": f"Issue {issue_key} not found."
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }

        data = response.json()
        fields = data.get('fields', {})

        # Extract core field values with error handling
        # Extract fix versions (convert from array of objects to array of names)
        fix_versions = []
        if fields.get('fixVersions'):
            fix_versions = [version.get('name', '') for version in fields.get('fixVersions', [])]

        # Get configurable custom field IDs
        rank_field = get_rank_field_id()
        team_field = get_team_field_id()

        # Extract rank - lexographic string for backlog ordering
        rank_value = fields.get(rank_field)
        # Handle case where rank might be a string or None
        if isinstance(rank_value, str):
            rank = rank_value
        else:
            rank = ''

        # Extract team - object with id and name
        team_obj = fields.get(team_field)
        # Handle case where team might be an object with 'name' or might be None/other
        if isinstance(team_obj, dict) and 'name' in team_obj:
            team = team_obj.get('name', '')
        else:
            team = ''

        issue_data = {
            'key': data.get('key', ''),
            'summary': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'status': fields.get('status', {}).get('name', '') if fields.get('status') else '',
            'type': fields.get('issuetype', {}).get('name', '') if fields.get('issuetype') else '',
            'priority': fields.get('priority', {}).get('name', '') if fields.get('priority') else '',
            'assignee': fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else '',
            'reporter': fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else '',
            'created': fields.get('created', ''),
            'updated': fields.get('updated', ''),
            'fix_versions': fix_versions,
            'labels': fields.get('labels', []),
            'rank': rank,
            'team': team
        }

        # Extract subtasks if requested
        if include_subtasks:
            subtasks = []
            for subtask in fields.get('subtasks', []):
                subtask_fields = subtask.get('fields', {})
                subtasks.append({
                    'key': subtask.get('key', ''),
                    'summary': subtask_fields.get('summary', ''),
                    'status': subtask_fields.get('status', {}).get('name', '') if subtask_fields.get('status') else '',
                    'type': subtask_fields.get('issuetype', {}).get('name', '') if subtask_fields.get('issuetype') else ''
                })
            issue_data['subtasks'] = subtasks

        # Extract linked issues if requested
        if include_linked_issues:
            linked_issues = []
            for link in fields.get('issuelinks', []):
                link_type = link.get('type', {})

                # Determine the link direction and get the linked issue
                if 'outwardIssue' in link:
                    linked_issue = link.get('outwardIssue', {})
                    link_description = link_type.get('outward', '')
                elif 'inwardIssue' in link:
                    linked_issue = link.get('inwardIssue', {})
                    link_description = link_type.get('inward', '')
                else:
                    continue

                linked_fields = linked_issue.get('fields', {})
                linked_issues.append({
                    'link_type': link_description,
                    'key': linked_issue.get('key', ''),
                    'summary': linked_fields.get('summary', ''),
                    'status': linked_fields.get('status', {}).get('name', '') if linked_fields.get('status') else ''
                })
            issue_data['linked_issues'] = linked_issues

        return {
            "status": "success",
            "issue_data": issue_data
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred while fetching issue: {str(e)}"
        }


@mcp.tool()
def add_jira_comment(
    issue_key: str,
    comment_body: str
) -> Dict[str, Any]:
    """
    Add a comment to a JIRA issue.

    IMPORTANT: JIRA uses wiki markup, NOT markdown. Use these formatting rules:
    - Numbered lists: Use # for level 1, ## for level 2 (NOT "1." style)
    - Bullet lists: Use * for level 1, ** for level 2
    - Headers: h1. h2. h3. (with space after dot)
    - Bold: *bold text*
    - Italic: _italic text_
    - Code inline: {{code}}
    - Code block: {code}...{code}
    - Links: [link text|http://url]
    - Quotes: {quote}text{quote}

    Args:
        issue_key (str): The JIRA issue key (e.g., "PROJECT-123")
        comment_body (str): The comment text in JIRA wiki markup format

    Returns:
        dict: A dictionary with the created comment details
    """
    # Input validation
    if not issue_key or not isinstance(issue_key, str):
        return {
            "status": "error",
            "message": "Invalid issue key. Please provide a valid JIRA issue key."
        }

    if not comment_body or not isinstance(comment_body, str):
        return {
            "status": "error",
            "message": "Invalid comment body. Please provide comment text."
        }

    # Get JIRA URL from environment
    jira_url = os.getenv("JIRA_SERVER_URL")
    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL not found in environment variables."
        }

    # Get API token from environment
    token = os.getenv("JIRA_API_TOKEN")
    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN not found in environment variables."
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}/comment"

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json={"body": comment_body}
        )

        if response.status_code == 404:
            return {
                "status": "error",
                "message": f"Issue {issue_key} not found."
            }

        if response.status_code not in [200, 201]:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }

        data = response.json()
        return {
            "status": "success",
            "message": f"Comment added to {issue_key}",
            "comment": {
                "id": data.get("id"),
                "author": data.get("author", {}).get("displayName", ""),
                "created": data.get("created", ""),
                "body": data.get("body", "")
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}"
        }


@mcp.tool()
def edit_jira_comment(
    issue_key: str,
    comment_id: Union[str, int],
    comment_body: str
) -> Dict[str, Any]:
    """
    Edit an existing comment on a JIRA issue.

    Use get_jira_issue_details with include_comments=True to find the comment ID.

    IMPORTANT: JIRA uses wiki markup, NOT markdown. Use these formatting rules:
    - Numbered lists: Use # for level 1, ## for level 2 (NOT "1." style)
    - Bullet lists: Use * for level 1, ** for level 2
    - Headers: h1. h2. h3. (with space after dot)
    - Bold: *bold text*
    - Italic: _italic text_
    - Code inline: {{code}}
    - Code block: {code}...{code}
    - Links: [link text|http://url]
    - Quotes: {quote}text{quote}

    Args:
        issue_key (str): The JIRA issue key (e.g., "PROJECT-123")
        comment_id (str or int): The ID of the comment to edit (from get_jira_issue_details).
            Accepts both string and numeric formats.
        comment_body (str): The new comment text in JIRA wiki markup format

    Returns:
        dict: A dictionary with the updated comment details
    """
    # Input validation
    if not issue_key or not isinstance(issue_key, str):
        return {
            "status": "error",
            "message": "Invalid issue key. Please provide a valid JIRA issue key."
        }

    # Coerce comment_id to string (MCP clients may send as int)
    comment_id = str(comment_id) if comment_id is not None else ""

    if not comment_id:
        return {
            "status": "error",
            "message": "Invalid comment ID. Please provide a valid comment ID."
        }

    if not comment_body or not isinstance(comment_body, str):
        return {
            "status": "error",
            "message": "Invalid comment body. Please provide comment text."
        }

    # Get JIRA URL from environment
    jira_url = os.getenv("JIRA_SERVER_URL")
    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL not found in environment variables."
        }

    # Get API token from environment
    token = os.getenv("JIRA_API_TOKEN")
    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN not found in environment variables."
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}/comment/{comment_id}"

    try:
        response = requests.put(
            endpoint,
            headers=headers,
            json={"body": comment_body}
        )

        if response.status_code == 404:
            return {
                "status": "error",
                "message": f"Issue {issue_key} or comment {comment_id} not found."
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }

        data = response.json()
        return {
            "status": "success",
            "message": f"Comment {comment_id} updated on {issue_key}",
            "comment": {
                "id": data.get("id"),
                "author": data.get("author", {}).get("displayName", ""),
                "updated": data.get("updated", ""),
                "body": data.get("body", "")
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}"
        }


@mcp.tool()
def get_jira_issue_details(
    issue_key: str,
    include_comments: bool = True,
    include_subtasks: bool = True,
    include_linked_issues: bool = True
) -> Dict[str, Any]:
    """
    Get detailed information about a specific JIRA issue by its key.

    This tool fetches complete information for a single JIRA issue including
    its summary, description, status, comments, subtasks, and linked issues.
    This eliminates the need for separate API calls to fetch related issues.

    Args:
        issue_key (str): The JIRA issue key (e.g., "PROJECT-123")
        include_comments (bool, optional): Whether to include comments. Defaults to True.
        include_subtasks (bool, optional): Whether to include subtasks. Defaults to True.
        include_linked_issues (bool, optional): Whether to include linked issues. Defaults to True.

    Returns:
        dict: A dictionary with detailed issue information including:
            - Basic fields: key, summary, description, status, type, priority, assignee, reporter, created, updated
            - comments: List of comments (if include_comments=True)
            - subtasks: List of child issues (if include_subtasks=True)
            - linked_issues: List of related issues with link types (if include_linked_issues=True)
    """
    # Input validation
    if not issue_key or not isinstance(issue_key, str):
        return {
            "status": "error",
            "message": "Invalid issue key. Please provide a valid JIRA issue key."
        }

    # Get JIRA URL from environment (required)
    jira_url = os.getenv("JIRA_SERVER_URL")

    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL not found in environment variables. Please set this variable to your JIRA instance URL (e.g., https://your-company.atlassian.net)."
        }

    # Get API token from environment variables
    token = os.getenv("JIRA_API_TOKEN")

    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN not found in environment variables. Please set this variable."
        }

    # Fetch issue with relations
    result = get_issue_with_relations(
        issue_key=issue_key,
        token=token,
        jira_url=jira_url,
        include_subtasks=include_subtasks,
        include_linked_issues=include_linked_issues
    )

    # Check if there was an error
    if result.get("status") == "error":
        return result

    issue_data = result.get("issue_data", {})

    # Fetch comments if requested
    if include_comments:
        comments = get_issue_comments(issue_key, token, jira_url)
        issue_data['comments'] = comments

    # Return the issue
    return {
        "status": "success",
        "message": f"Retrieved issue {issue_key}",
        "issue": issue_data
    }

@mcp.tool()
def update_jira_issue(
    issue_key: str,
    summary: str = None,
    description: str = None,
    priority: str = None,
    assignee: str = None,
    labels: List[str] = None,
    fix_versions: List[str] = None,
    team: str = None
) -> Dict[str, Any]:
    """
    Update fields on a JIRA issue.

    Only fields that are explicitly provided will be updated. Omitted fields
    will remain unchanged. This allows you to update a single field without
    affecting others.

    IMPORTANT: Description uses JIRA wiki markup, NOT markdown. Use these rules:
    - Numbered lists: Use # for level 1, ## for level 2 (NOT "1." style)
    - Bullet lists: Use * for level 1, ** for level 2
    - Headers: h1. h2. h3. (with space after dot)
    - Bold: *bold text*
    - Italic: _italic text_
    - Code inline: {{code}}
    - Code block: {code}...{code}
    - Links: [link text|http://url]
    - Quotes: {quote}text{quote}

    Args:
        issue_key (str): The JIRA issue key (e.g., "PROJECT-123")
        summary (str, optional): New issue title/summary
        description (str, optional): New description in JIRA wiki markup format
        priority (str, optional): Priority name - typically "Highest", "High", "Medium", "Low", "Lowest"
        assignee (str, optional): Assignee username or account ID. Use empty string "" to unassign.
        labels (list, optional): Array of label strings. This REPLACES all existing labels.
            Note: JIRA labels cannot contain spaces. Use underscores instead (e.g.,
            "JC_Validation_Clear"). JIRA's web UI displays underscores as spaces, so
            "My_Label" appears as "My Label" in the browser. When reading labels via
            get_jira_issue_details, they will contain underscores.
        fix_versions (list, optional): Array of version names. This REPLACES all existing fix versions.
            ⚠️ WARNING: Fix versions are typically managed by release managers. Changing this
            field may affect release planning and should be coordinated with the team.
        team (str, optional): Team name (e.g., "Platform Team"). The name is automatically
            converted to a team ID by searching for existing issues with that team assigned.
            Uses the Team custom field configured via JIRA_TEAM_FIELD environment variable.

    Returns:
        dict: A dictionary with the updated issue details including:
            - status: "success" or "error"
            - message: Description of what was updated
            - issue: The updated issue data (on success)
    """
    # Input validation
    if not issue_key or not isinstance(issue_key, str):
        return {
            "status": "error",
            "message": "Invalid issue key. Please provide a valid JIRA issue key."
        }

    # Check that at least one field is provided to update
    if all(v is None for v in [summary, description, priority, assignee, labels, fix_versions, team]):
        return {
            "status": "error",
            "message": "No fields provided to update. Please provide at least one field to update."
        }

    # Get JIRA URL from environment
    jira_url = os.getenv("JIRA_SERVER_URL")
    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL not found in environment variables."
        }

    # Get API token from environment
    token = os.getenv("JIRA_API_TOKEN")
    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN not found in environment variables."
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Build the fields object with only provided values
    fields_to_update = {}
    updated_fields_list = []

    if summary is not None:
        fields_to_update["summary"] = summary
        updated_fields_list.append("summary")

    if description is not None:
        fields_to_update["description"] = description
        updated_fields_list.append("description")

    if priority is not None:
        fields_to_update["priority"] = {"name": priority}
        updated_fields_list.append("priority")

    if assignee is not None:
        if assignee == "":
            # Unassign the issue
            fields_to_update["assignee"] = None
            updated_fields_list.append("assignee (unassigned)")
        else:
            # JIRA Server uses "name", JIRA Cloud uses "accountId"
            # Try name first as this is likely JIRA Server based on Bearer token auth
            fields_to_update["assignee"] = {"name": assignee}
            updated_fields_list.append("assignee")

    if labels is not None:
        if not isinstance(labels, list):
            return {
                "status": "error",
                "message": "Labels must be an array of strings."
            }
        fields_to_update["labels"] = labels
        updated_fields_list.append("labels")

    if fix_versions is not None:
        if not isinstance(fix_versions, list):
            return {
                "status": "error",
                "message": "Fix versions must be an array of version names."
            }
        # Convert version names to objects with name property
        fields_to_update["fixVersions"] = [{"name": v} for v in fix_versions]
        updated_fields_list.append("fix_versions")

    if team is not None:
        # Get the team field ID from environment
        team_field_id = get_team_field_id()

        # Team field requires looking up the team ID by name first
        team_lookup = get_team_id_by_name(team, token, jira_url)
        if team_lookup.get("status") == "error":
            return {
                "status": "error",
                "message": f"Team lookup failed: {team_lookup.get('message')}"
            }

        team_id = team_lookup.get("team_id")
        # Team field expects the ID as a string
        fields_to_update[team_field_id] = str(team_id)
        updated_fields_list.append("team")

    # Make the update request
    endpoint = f"{jira_url}/rest/api/2/issue/{issue_key}"

    try:
        response = requests.put(
            endpoint,
            headers=headers,
            json={"fields": fields_to_update}
        )

        if response.status_code == 404:
            return {
                "status": "error",
                "message": f"Issue {issue_key} not found."
            }

        if response.status_code == 400:
            # Bad request - usually means invalid field value
            error_data = response.json() if response.text else {}
            errors = error_data.get("errors", {})
            error_messages = error_data.get("errorMessages", [])

            error_detail = ""
            if errors:
                error_detail = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            if error_messages:
                error_detail = "; ".join(error_messages) + ("; " + error_detail if error_detail else "")

            return {
                "status": "error",
                "message": f"Invalid field value: {error_detail if error_detail else response.text}"
            }

        if response.status_code == 403:
            return {
                "status": "error",
                "message": f"Permission denied. You don't have permission to edit {issue_key}."
            }

        if response.status_code not in [200, 204]:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }

        # Success! Now fetch the updated issue to return it
        updated_issue = get_issue_with_relations(
            issue_key=issue_key,
            token=token,
            jira_url=jira_url,
            include_subtasks=False,
            include_linked_issues=False
        )

        if updated_issue.get("status") == "error":
            # Update succeeded but couldn't fetch updated issue
            return {
                "status": "success",
                "message": f"Updated {issue_key}: {', '.join(updated_fields_list)}. Could not fetch updated issue details.",
                "updated_fields": updated_fields_list
            }

        return {
            "status": "success",
            "message": f"Updated {issue_key}: {', '.join(updated_fields_list)}",
            "updated_fields": updated_fields_list,
            "issue": updated_issue.get("issue_data", {})
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}"
        }


@mcp.tool()
def rank_jira_issues(
    issue_keys: List[str],
    rank_before: str = None,
    rank_after: str = None
) -> Dict[str, Any]:
    """
    Rank (reorder) one or more JIRA issues relative to another issue.

    Uses JIRA's Agile ranking API to move issues in the backlog.
    You must specify exactly one of rank_before or rank_after.
    Up to 50 issues can be ranked in a single call.

    Note: All issues should typically be in the same project. Cross-project
    ranking may fail depending on JIRA configuration.

    Args:
        issue_keys: List of issue keys to move (e.g., ["PROJECT-123", "PROJECT-456"])
        rank_before: Rank the issues BEFORE this issue key (higher priority)
        rank_after: Rank the issues AFTER this issue key (lower priority)

    Returns:
        dict: Success/error status with details on each issue if partial failure

    Examples:
        # Move single issue to top of backlog (before first issue)
        rank_jira_issues(["PROJ-10"], rank_before="PROJ-1")

        # Move multiple issues after a specific issue
        rank_jira_issues(["PROJ-5", "PROJ-6", "PROJ-7"], rank_after="PROJ-2")
    """
    # Validate inputs
    if not issue_keys:
        return {
            "status": "error",
            "message": "issue_keys must be a non-empty list"
        }

    if len(issue_keys) > 50:
        return {
            "status": "error",
            "message": "Maximum 50 issues can be ranked at once"
        }

    if rank_before and rank_after:
        return {
            "status": "error",
            "message": "Specify only one of rank_before or rank_after, not both"
        }

    if not rank_before and not rank_after:
        return {
            "status": "error",
            "message": "Must specify either rank_before or rank_after"
        }

    # Get credentials
    token = os.getenv("JIRA_API_TOKEN")
    jira_url = os.getenv("JIRA_SERVER_URL")

    if not token:
        return {
            "status": "error",
            "message": "JIRA_API_TOKEN environment variable not set"
        }

    if not jira_url:
        return {
            "status": "error",
            "message": "JIRA_SERVER_URL environment variable not set"
        }

    # Build endpoint - use Agile API
    endpoint = f"{jira_url}/rest/agile/1.0/issue/rank"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Build payload
    payload = {"issues": issue_keys}

    if rank_before:
        payload["rankBeforeIssue"] = rank_before
    else:
        payload["rankAfterIssue"] = rank_after

    # Add rank custom field ID if configured
    rank_field = get_rank_field_id()
    if rank_field.startswith("customfield_"):
        try:
            field_id = int(rank_field.replace("customfield_", ""))
            payload["rankCustomFieldId"] = field_id
        except ValueError:
            pass  # Use default if parsing fails

    try:
        response = requests.put(
            endpoint,
            headers=headers,
            json=payload
        )

        # Handle different response codes
        if response.status_code == 204:
            # Complete success
            return {
                "status": "success",
                "message": f"Successfully ranked {len(issue_keys)} issue(s)"
            }

        if response.status_code == 207:
            # Partial success - parse entries
            try:
                data = response.json()
                entries = data.get("entries", [])
                successes = [e for e in entries if e.get("status") in [200, 204]]
                failures = [e for e in entries if e.get("status") not in [200, 204]]

                return {
                    "status": "partial",
                    "message": f"{len(successes)} succeeded, {len(failures)} failed",
                    "successes": [{"issueKey": e.get("issueKey"), "status": e.get("status")} for e in successes],
                    "failures": [{"issueKey": e.get("issueKey"), "status": e.get("status"), "errors": e.get("errors", [])} for e in failures]
                }
            except json.JSONDecodeError:
                return {
                    "status": "partial",
                    "message": "Partial success but could not parse response details"
                }

        if response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("errorMessages", [response.text])[0] if error_data.get("errorMessages") else response.text
            except json.JSONDecodeError:
                error_msg = response.text
            return {
                "status": "error",
                "message": f"Invalid request: {error_msg}"
            }

        if response.status_code == 403:
            return {
                "status": "error",
                "message": "Permission denied. Requires 'Schedule Issues' permission in JIRA."
            }

        if response.status_code == 404:
            return {
                "status": "error",
                "message": "Issue not found. Check that all issue keys are valid."
            }

        # Other errors
        return {
            "status": "error",
            "message": f"JIRA API error (HTTP {response.status_code}): {response.text}"
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}"
        }


@mcp.tool()
def reorder_jira_issues(
    issue_keys: List[str],
    after_issue: str = None
) -> Dict[str, Any]:
    """
    Reorder issues so they appear in the given sequence.

    This is a convenience function that chains multiple rank operations
    to achieve a specific ordering. Issues will be ordered in the sequence
    provided, optionally starting after a reference issue.

    Args:
        issue_keys: Issues in desired order (first = highest priority)
        after_issue: Optional reference issue - place all issues after this.
                     If not provided, issues are ordered relative to each other.

    Returns:
        dict: Success/error status with count of operations performed

    Example:
        # Reorder issues in priority sequence
        reorder_jira_issues([
            "PROJECT-100",  # First (highest priority)
            "PROJECT-101",  # Second
            "PROJECT-102",  # Third
        ])

        # Place issues after a specific reference issue
        reorder_jira_issues(["PROJECT-5", "PROJECT-6"], after_issue="PROJECT-1")
    """
    if not issue_keys:
        return {
            "status": "error",
            "message": "issue_keys must be a non-empty list"
        }

    if len(issue_keys) < 2 and not after_issue:
        return {
            "status": "error",
            "message": "Need at least 2 issues to reorder, or specify after_issue for a single issue"
        }

    operations_completed = 0
    failures = []

    try:
        # If after_issue is provided, place the first issue after it
        start_index = 0
        if after_issue:
            result = rank_jira_issues([issue_keys[0]], rank_after=after_issue)
            if result.get("status") == "error":
                return {
                    "status": "error",
                    "message": f"Failed to place {issue_keys[0]} after {after_issue}: {result.get('message')}"
                }
            operations_completed += 1
            start_index = 1

        # Chain the remaining issues - each one goes after the previous
        for i in range(max(start_index, 1), len(issue_keys)):
            result = rank_jira_issues([issue_keys[i]], rank_after=issue_keys[i-1])

            if result.get("status") == "error":
                failures.append({
                    "issue": issue_keys[i],
                    "after": issue_keys[i-1],
                    "error": result.get("message")
                })
            elif result.get("status") == "partial":
                failures.append({
                    "issue": issue_keys[i],
                    "after": issue_keys[i-1],
                    "error": "Partial failure"
                })
            else:
                operations_completed += 1

        if failures:
            return {
                "status": "partial",
                "message": f"{operations_completed} operations succeeded, {len(failures)} failed",
                "operations_completed": operations_completed,
                "failures": failures
            }

        return {
            "status": "success",
            "message": f"Successfully reordered {len(issue_keys)} issues",
            "operations_completed": operations_completed
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred: {str(e)}",
            "operations_completed": operations_completed
        }


# Add server entry point
if __name__ == "__main__":
    # print("Starting JIRA MCP Server...")
    mcp.run()

