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

@mcp.tool()
def search_jira_issues(
    jql_query: str, 
    max_results: int = 100, 
    include_comments: bool = False
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
    
    # Fields to retrieve - includes description/text field and fixVersions
    fields = "summary,description,status,assignee,reporter,created,updated,priority,issuetype,fixVersions"
    
    # Request parameters
    params = {
        "jql": jql_query,
        "maxResults": max_results,
        "fields": fields
    }
    
    try:
        # Make the request
        response = requests.get(endpoint, headers=headers, params=params)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"JIRA API error: {response.status_code} - {response.text}"
            }
        
        # Parse the response
        data = response.json()
        total_issues = data.get('total', 0)
        retrieved_issues = len(data.get('issues', []))
        
        # Create lists to store data
        issue_data = []
        
        for issue in data.get('issues', []):
            key = issue.get('key')
            fields = issue.get('fields', {})
            
            # Extract field values with error handling
            summary = fields.get('summary', '')
            description = fields.get('description', '')
            status = fields.get('status', {}).get('name', '') if fields.get('status') else ''
            
            # Handle nullable objects
            assignee = fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else ''
            reporter = fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else ''
            
            # Handle timestamps
            created = fields.get('created', '')
            updated = fields.get('updated', '')
            
            # Get issue type and priority
            issue_type = fields.get('issuetype', {}).get('name', '') if fields.get('issuetype') else ''
            priority = fields.get('priority', {}).get('name', '') if fields.get('priority') else ''

            # Extract fix versions (convert from array of objects to array of names)
            fix_versions = []
            if fields.get('fixVersions'):
                fix_versions = [version.get('name', '') for version in fields.get('fixVersions', [])]

            # Fetch comments if requested
            comments = []
            if include_comments:
                comments = get_issue_comments(key, token, jira_url)
            
            # Add to our data list
            issue_data.append({
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
                'comments': comments if include_comments else None
            })
        
        # Return structured response
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
                'author': author,
                'created': created,
                'body': body
            })
        
        return comments_list
    
    except Exception:
        return []

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
            'fix_versions': fix_versions
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

# Add server entry point
if __name__ == "__main__":
    # print("Starting JIRA MCP Server...")
    mcp.run()

