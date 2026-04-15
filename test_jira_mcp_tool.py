# test_jira_mcp_tool.py
"""
Unit tests for the JIRA MCP Tool

This test suite covers the enhanced functionality of the JIRA MCP server,
specifically testing subtasks and linked issues retrieval.

To run tests:
    python -m pytest test_jira_mcp_tool.py -v
or
    python -m unittest test_jira_mcp_tool.py
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
import json
import os

# Import the functions we're testing
from jira_mcp_server import (
    get_issue_with_relations,
    get_jira_issue_details,
    get_issue_comments,
    search_jira_issues,
    get_jira_field_metadata,
    update_jira_issue,
    get_team_id_by_name,
    rank_jira_issues,
    reorder_jira_issues,
    edit_jira_comment
)


class TestGetIssueWithRelations(unittest.TestCase):
    """Test suite for the get_issue_with_relations helper function."""

    def setUp(self):
        """Set up test fixtures."""
        self.issue_key = "PROJECT-123"
        self.token = "test_token_123"
        self.jira_url = "https://jira.example.com"

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_fix_versions(self, mock_get):
        """Test that fix_versions field is properly extracted and returned."""
        # Mock the API response with fixVersions
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Issue with fix versions',
                'description': 'Test issue description',
                'status': {'name': 'In Progress'},
                'issuetype': {'name': 'Story'},
                'priority': {'name': 'High'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [
                    {
                        'id': '10001',
                        'name': 'Release 1.0',
                        'archived': False,
                        'released': False
                    },
                    {
                        'id': '10002',
                        'name': 'Release 2.0',
                        'archived': False,
                        'released': False
                    }
                ],
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=False,
            include_linked_issues=False
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        self.assertIn('issue_data', result)
        issue_data = result['issue_data']

        # Check that fix_versions field exists and contains correct data
        self.assertIn('fix_versions', issue_data)
        self.assertEqual(len(issue_data['fix_versions']), 2)
        self.assertIn('Release 1.0', issue_data['fix_versions'])
        self.assertIn('Release 2.0', issue_data['fix_versions'])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_empty_fix_versions(self, mock_get):
        """Test that empty fix_versions is handled correctly."""
        # Mock the API response with no fixVersions
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Issue without fix versions',
                'description': 'Test issue description',
                'status': {'name': 'Open'},
                'issuetype': {'name': 'Bug'},
                'priority': {'name': 'Medium'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [],  # Empty array
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=False,
            include_linked_issues=False
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']

        # Check that fix_versions field exists and is an empty list
        self.assertIn('fix_versions', issue_data)
        self.assertEqual(issue_data['fix_versions'], [])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_labels(self, mock_get):
        """Test that labels field is properly extracted and returned."""
        # Mock the API response with labels
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Issue with labels',
                'description': 'Test issue description',
                'status': {'name': 'In Progress'},
                'issuetype': {'name': 'Story'},
                'priority': {'name': 'High'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [],
                'labels': ['BETA6', 'JC Validation Clear', 'urgent'],
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=False,
            include_linked_issues=False
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']

        # Check that labels field exists and contains correct data
        self.assertIn('labels', issue_data)
        self.assertEqual(len(issue_data['labels']), 3)
        self.assertIn('BETA6', issue_data['labels'])
        self.assertIn('JC Validation Clear', issue_data['labels'])
        self.assertIn('urgent', issue_data['labels'])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_empty_labels(self, mock_get):
        """Test that empty labels is handled correctly."""
        # Mock the API response with no labels
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Issue without labels',
                'description': 'Test issue description',
                'status': {'name': 'Open'},
                'issuetype': {'name': 'Bug'},
                'priority': {'name': 'Medium'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [],
                'labels': [],  # Empty array
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=False,
            include_linked_issues=False
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']

        # Check that labels field exists and is an empty list
        self.assertIn('labels', issue_data)
        self.assertEqual(issue_data['labels'], [])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_subtasks(self, mock_get):
        """Test fetching issue with subtasks."""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Parent Issue',
                'description': 'Parent issue description',
                'status': {'name': 'In Progress'},
                'issuetype': {'name': 'Story'},
                'priority': {'name': 'High'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [],  # Add fixVersions to existing test
                'subtasks': [
                    {
                        'key': 'PROJECT-124',
                        'fields': {
                            'summary': 'Subtask 1',
                            'status': {'name': 'Open'},
                            'issuetype': {'name': 'Sub-task'}
                        }
                    },
                    {
                        'key': 'PROJECT-125',
                        'fields': {
                            'summary': 'Subtask 2',
                            'status': {'name': 'Done'},
                            'issuetype': {'name': 'Sub-task'}
                        }
                    }
                ],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=True,
            include_linked_issues=True
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        self.assertIn('issue_data', result)
        issue_data = result['issue_data']

        # Check basic fields
        self.assertEqual(issue_data['key'], 'PROJECT-123')
        self.assertEqual(issue_data['summary'], 'Parent Issue')
        self.assertEqual(issue_data['status'], 'In Progress')

        # Check subtasks
        self.assertIn('subtasks', issue_data)
        self.assertEqual(len(issue_data['subtasks']), 2)
        self.assertEqual(issue_data['subtasks'][0]['key'], 'PROJECT-124')
        self.assertEqual(issue_data['subtasks'][0]['summary'], 'Subtask 1')
        self.assertEqual(issue_data['subtasks'][0]['status'], 'Open')

        # Check linked issues (should be empty list)
        self.assertIn('linked_issues', issue_data)
        self.assertEqual(len(issue_data['linked_issues']), 0)

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('subtasks', call_args[0][0])
        self.assertIn('issuelinks', call_args[0][0])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_linked_issues(self, mock_get):
        """Test fetching issue with linked issues."""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Main Issue',
                'description': 'Main issue description',
                'status': {'name': 'Open'},
                'issuetype': {'name': 'Bug'},
                'priority': {'name': 'Medium'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'subtasks': [],
                'issuelinks': [
                    {
                        'type': {
                            'name': 'Blocks',
                            'inward': 'is blocked by',
                            'outward': 'blocks'
                        },
                        'outwardIssue': {
                            'key': 'PROJECT-100',
                            'fields': {
                                'summary': 'Blocked Issue',
                                'status': {'name': 'Open'}
                            }
                        }
                    },
                    {
                        'type': {
                            'name': 'Relates',
                            'inward': 'relates to',
                            'outward': 'relates to'
                        },
                        'inwardIssue': {
                            'key': 'PROJECT-200',
                            'fields': {
                                'summary': 'Related Issue',
                                'status': {'name': 'In Progress'}
                            }
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=True,
            include_linked_issues=True
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']

        # Check linked issues
        self.assertIn('linked_issues', issue_data)
        self.assertEqual(len(issue_data['linked_issues']), 2)

        # Check first linked issue (outward)
        self.assertEqual(issue_data['linked_issues'][0]['link_type'], 'blocks')
        self.assertEqual(issue_data['linked_issues'][0]['key'], 'PROJECT-100')
        self.assertEqual(issue_data['linked_issues'][0]['summary'], 'Blocked Issue')
        self.assertEqual(issue_data['linked_issues'][0]['status'], 'Open')

        # Check second linked issue (inward)
        self.assertEqual(issue_data['linked_issues'][1]['link_type'], 'relates to')
        self.assertEqual(issue_data['linked_issues'][1]['key'], 'PROJECT-200')

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_no_relations(self, mock_get):
        """Test fetching issue with no subtasks or linked issues."""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Standalone Issue',
                'description': 'Issue with no relations',
                'status': {'name': 'Open'},
                'issuetype': {'name': 'Task'},
                'priority': {'name': 'Low'},
                'assignee': None,
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=True,
            include_linked_issues=True
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']

        # Check that subtasks and linked_issues are empty lists
        self.assertEqual(issue_data['subtasks'], [])
        self.assertEqual(issue_data['linked_issues'], [])

        # Check null handling for assignee
        self.assertEqual(issue_data['assignee'], '')

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_optional_relations_disabled(self, mock_get):
        """Test fetching issue with subtasks and linked issues disabled."""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Issue',
                'description': 'Description',
                'status': {'name': 'Open'},
                'issuetype': {'name': 'Task'},
                'priority': {'name': 'Medium'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000'
            }
        }
        mock_get.return_value = mock_response

        # Call the function with relations disabled
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url,
            include_subtasks=False,
            include_linked_issues=False
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']

        # Check that subtasks and linked_issues are NOT in the response
        self.assertNotIn('subtasks', issue_data)
        self.assertNotIn('linked_issues', issue_data)

        # Verify API call doesn't include expand parameter
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertNotIn('expand=', call_url)

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_not_found(self, mock_get):
        """Test handling of 404 error when issue doesn't exist."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url
        )

        # Assertions
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_api_error(self, mock_get):
        """Test handling of API errors."""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url
        )

        # Assertions
        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA API error', result['message'])
        self.assertIn('500', result['message'])

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_exception_handling(self, mock_get):
        """Test exception handling."""
        # Mock exception
        mock_get.side_effect = Exception('Connection timeout')

        # Call the function
        result = get_issue_with_relations(
            self.issue_key,
            self.token,
            self.jira_url
        )

        # Assertions
        self.assertEqual(result['status'], 'error')
        self.assertIn('Exception occurred', result['message'])
        self.assertIn('Connection timeout', result['message'])


class TestGetJiraIssueDetails(unittest.TestCase):
    """Test suite for the get_jira_issue_details MCP tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.issue_key = "PROJECT-123"
        os.environ['JIRA_API_TOKEN'] = 'test_token_123'
        os.environ['JIRA_SERVER_URL'] = 'https://jira.example.com'

    def tearDown(self):
        """Clean up after tests."""
        if 'JIRA_API_TOKEN' in os.environ:
            del os.environ['JIRA_API_TOKEN']
        if 'JIRA_SERVER_URL' in os.environ:
            del os.environ['JIRA_SERVER_URL']

    @patch('jira_mcp_server.get_issue_comments')
    @patch('jira_mcp_server.get_issue_with_relations')
    def test_get_issue_details_with_all_options(self, mock_get_relations, mock_get_comments):
        """Test getting issue details with all options enabled."""
        # Mock the responses
        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {
                'key': 'PROJECT-123',
                'summary': 'Test Issue',
                'description': 'Test Description',
                'status': 'Open',
                'type': 'Bug',
                'priority': 'High',
                'assignee': 'John Doe',
                'reporter': 'Jane Smith',
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'subtasks': [
                    {'key': 'PROJECT-124', 'summary': 'Subtask 1', 'status': 'Open', 'type': 'Sub-task'}
                ],
                'linked_issues': [
                    {'link_type': 'blocks', 'key': 'PROJECT-100', 'summary': 'Blocked Issue', 'status': 'Open'}
                ]
            }
        }

        mock_get_comments.return_value = [
            {'author': 'John Doe', 'created': '2025-01-10T12:00:00.000+0000', 'body': 'Test comment'}
        ]

        # Call the function
        result = get_jira_issue_details(
            self.issue_key,
            include_comments=True,
            include_subtasks=True,
            include_linked_issues=True
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        self.assertIn('issue', result)
        issue = result['issue']

        # Check all fields are present
        self.assertEqual(issue['key'], 'PROJECT-123')
        self.assertEqual(issue['summary'], 'Test Issue')
        self.assertIn('subtasks', issue)
        self.assertIn('linked_issues', issue)
        self.assertIn('comments', issue)

        # Verify function calls
        mock_get_relations.assert_called_once()
        mock_get_comments.assert_called_once_with(self.issue_key, 'test_token_123', 'https://jira.example.com')

    @patch('jira_mcp_server.get_issue_comments')
    @patch('jira_mcp_server.get_issue_with_relations')
    def test_get_issue_details_without_comments(self, mock_get_relations, mock_get_comments):
        """Test getting issue details without comments."""
        # Mock the response
        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {
                'key': 'PROJECT-123',
                'summary': 'Test Issue',
                'description': 'Test Description',
                'status': 'Open',
                'type': 'Bug',
                'priority': 'High',
                'assignee': 'John Doe',
                'reporter': 'Jane Smith',
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'subtasks': [],
                'linked_issues': []
            }
        }

        # Call the function with include_comments=False
        result = get_jira_issue_details(
            self.issue_key,
            include_comments=False,
            include_subtasks=True,
            include_linked_issues=True
        )

        # Assertions
        self.assertEqual(result['status'], 'success')
        issue = result['issue']
        self.assertNotIn('comments', issue)

        # Verify get_issue_comments was NOT called
        mock_get_comments.assert_not_called()

    def test_get_issue_details_invalid_input(self):
        """Test input validation for invalid issue key."""
        # Test with empty string
        result = get_jira_issue_details("")
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid issue key', result['message'])

        # Test with None
        result = get_jira_issue_details(None)
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid issue key', result['message'])

    def test_get_issue_details_missing_token(self):
        """Test handling of missing JIRA API token."""
        # Remove the token
        del os.environ['JIRA_API_TOKEN']

        # Call the function
        result = get_jira_issue_details(self.issue_key)

        # Assertions
        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_API_TOKEN not found', result['message'])

    @patch('jira_mcp_server.get_issue_with_relations')
    def test_get_issue_details_propagates_errors(self, mock_get_relations):
        """Test that errors from get_issue_with_relations are propagated."""
        # Mock an error response
        mock_get_relations.return_value = {
            'status': 'error',
            'message': 'Issue not found'
        }

        # Call the function
        result = get_jira_issue_details(self.issue_key)

        # Assertions
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Issue not found')


class TestSearchJiraIssues(unittest.TestCase):
    """Test suite for the search_jira_issues MCP tool."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ['JIRA_API_TOKEN'] = 'test_token_123'
        os.environ['JIRA_SERVER_URL'] = 'https://jira.example.com'

    def tearDown(self):
        """Clean up after tests."""
        if 'JIRA_API_TOKEN' in os.environ:
            del os.environ['JIRA_API_TOKEN']
        if 'JIRA_SERVER_URL' in os.environ:
            del os.environ['JIRA_SERVER_URL']

    @patch('jira_mcp_server.requests.get')
    def test_search_with_fix_versions(self, mock_get):
        """Test that search_jira_issues returns fix_versions field."""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 2,
            'issues': [
                {
                    'key': 'PROJECT-123',
                    'fields': {
                        'summary': 'Issue 1',
                        'description': 'Description 1',
                        'status': {'name': 'In Progress'},
                        'issuetype': {'name': 'Story'},
                        'priority': {'name': 'High'},
                        'assignee': {'displayName': 'John Doe'},
                        'reporter': {'displayName': 'Jane Smith'},
                        'created': '2025-01-01T10:00:00.000+0000',
                        'updated': '2025-01-15T15:30:00.000+0000',
                        'fixVersions': [
                            {'id': '10001', 'name': 'Release 1.0'},
                            {'id': '10002', 'name': 'Release 2.0'}
                        ]
                    }
                },
                {
                    'key': 'PROJECT-124',
                    'fields': {
                        'summary': 'Issue 2',
                        'description': 'Description 2',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Bug'},
                        'priority': {'name': 'Medium'},
                        'assignee': None,
                        'reporter': {'displayName': 'Bob Johnson'},
                        'created': '2025-01-05T10:00:00.000+0000',
                        'updated': '2025-01-10T15:30:00.000+0000',
                        'fixVersions': []  # Empty fix versions
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Call the function
        result = search_jira_issues('project = MYPROJECT', max_results=10)

        # Assertions
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_issues'], 2)
        self.assertEqual(result['retrieved_issues'], 2)

        # Check first issue has fix_versions
        issue1 = result['issues'][0]
        self.assertEqual(issue1['key'], 'PROJECT-123')
        self.assertIn('fix_versions', issue1)
        self.assertEqual(len(issue1['fix_versions']), 2)
        self.assertIn('Release 1.0', issue1['fix_versions'])
        self.assertIn('Release 2.0', issue1['fix_versions'])

        # Check second issue has empty fix_versions
        issue2 = result['issues'][1]
        self.assertEqual(issue2['key'], 'PROJECT-124')
        self.assertIn('fix_versions', issue2)
        self.assertEqual(issue2['fix_versions'], [])

    @patch('jira_mcp_server.requests.get')
    def test_search_with_team_filter(self, mock_get):
        """Test that search_jira_issues filters by team name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 4,
            'issues': [
                {
                    'key': 'PROJECT-123',
                    'fields': {
                        'summary': 'Issue 1',
                        'description': 'Description 1',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'},
                        'priority': {'name': 'High'},
                        'assignee': None,
                        'reporter': None,
                        'created': '2025-01-01T10:00:00.000+0000',
                        'updated': '2025-01-15T15:30:00.000+0000',
                        'fixVersions': [],
                        'customfield_10000': '2|a:',
                        'customfield_10803': {'id': 1, 'name': 'Platform Team'}
                    }
                },
                {
                    'key': 'PROJECT-124',
                    'fields': {
                        'summary': 'Issue 2',
                        'description': 'Description 2',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Bug'},
                        'priority': {'name': 'Medium'},
                        'assignee': None,
                        'reporter': None,
                        'created': '2025-01-02T10:00:00.000+0000',
                        'updated': '2025-01-16T15:30:00.000+0000',
                        'fixVersions': [],
                        'customfield_10000': '2|b:',
                        'customfield_10803': {'id': 2, 'name': 'Infrastructure Team'}
                    }
                },
                {
                    'key': 'PROJECT-125',
                    'fields': {
                        'summary': 'Issue 3',
                        'description': 'Description 3',
                        'status': {'name': 'In Progress'},
                        'issuetype': {'name': 'Task'},
                        'priority': {'name': 'Low'},
                        'assignee': None,
                        'reporter': None,
                        'created': '2025-01-03T10:00:00.000+0000',
                        'updated': '2025-01-17T15:30:00.000+0000',
                        'fixVersions': [],
                        'customfield_10000': '2|c:',
                        'customfield_10803': {'id': 1, 'name': 'Platform Team'}
                    }
                },
                {
                    'key': 'PROJECT-126',
                    'fields': {
                        'summary': 'Issue 4',
                        'description': 'Description 4',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'},
                        'priority': {'name': 'High'},
                        'assignee': None,
                        'reporter': None,
                        'created': '2025-01-04T10:00:00.000+0000',
                        'updated': '2025-01-18T15:30:00.000+0000',
                        'fixVersions': [],
                        'customfield_10000': '2|d:',
                        'customfield_10803': None  # No team assigned
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Test filtering by partial team name
        result = search_jira_issues('project = PROJECT', max_results=10, team_filter='Platform')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['retrieved_issues'], 2)
        self.assertEqual(result['team_filter'], 'Platform')
        self.assertIn('filtered_issues', result)

        # Check only Platform team issues are returned
        for issue in result['issues']:
            self.assertIn('Platform', issue['team'])

    @patch('jira_mcp_server.requests.get')
    def test_search_with_team_filter_case_insensitive(self, mock_get):
        """Test that team_filter is case-insensitive."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 2,
            'issues': [
                {
                    'key': 'PROJECT-123',
                    'fields': {
                        'summary': 'Issue 1',
                        'description': '',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'},
                        'priority': None,
                        'assignee': None,
                        'reporter': None,
                        'created': '',
                        'updated': '',
                        'fixVersions': [],
                        'customfield_10000': '2|a:',
                        'customfield_10803': {'id': 1, 'name': 'Infrastructure Team'}
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Test with different case
        result = search_jira_issues('project = PROJECT', max_results=10, team_filter='HARDWARE')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['retrieved_issues'], 1)
        self.assertEqual(result['issues'][0]['team'], 'Infrastructure Team')

    @patch('jira_mcp_server.requests.get')
    def test_search_with_team_filter_no_matches(self, mock_get):
        """Test team_filter when no issues match."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 2,
            'issues': [
                {
                    'key': 'PROJECT-123',
                    'fields': {
                        'summary': 'Issue 1',
                        'description': '',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'},
                        'priority': None,
                        'assignee': None,
                        'reporter': None,
                        'created': '',
                        'updated': '',
                        'fixVersions': [],
                        'customfield_10000': '2|a:',
                        'customfield_10803': {'id': 1, 'name': 'Platform Team'}
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Test with non-matching filter
        result = search_jira_issues('project = PROJECT', max_results=10, team_filter='NonExistentTeam')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['retrieved_issues'], 0)
        self.assertEqual(result['filtered_issues'], 0)
        self.assertEqual(result['issues'], [])

    @patch('jira_mcp_server.requests.get')
    def test_search_with_team_filter_respects_max_results(self, mock_get):
        """Test that team_filter respects max_results limit after filtering.

        Note: With pagination, the function stops early once it finds enough matches,
        so filtered_issues equals retrieved_issues when we stop early.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        # Return many matching issues
        mock_response.json.return_value = {
            'total': 10,
            'issues': [
                {
                    'key': f'PROJECT-{i}',
                    'fields': {
                        'summary': f'Issue {i}',
                        'description': '',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'},
                        'priority': None,
                        'assignee': None,
                        'reporter': None,
                        'created': '',
                        'updated': '',
                        'fixVersions': [],
                        'customfield_10000': f'2|{i}:',
                        'customfield_10803': {'id': 1, 'name': 'Target Team'}
                    }
                }
                for i in range(10)
            ]
        }
        mock_get.return_value = mock_response

        # Request only 3 results
        result = search_jira_issues('project = PROJECT', max_results=3, team_filter='Target')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['retrieved_issues'], 3)
        # With early stopping, filtered_issues equals retrieved_issues
        self.assertEqual(result['filtered_issues'], 3)
        self.assertEqual(len(result['issues']), 3)


class TestRankAndTeamFields(unittest.TestCase):
    """Test suite for rank and team custom fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.issue_key = "PROJECT-123"
        self.token = "test_token_123"
        self.jira_url = "https://jira.example.com"
        os.environ['JIRA_API_TOKEN'] = self.token
        os.environ['JIRA_SERVER_URL'] = self.jira_url

    def tearDown(self):
        """Clean up after tests."""
        if 'JIRA_API_TOKEN' in os.environ:
            del os.environ['JIRA_API_TOKEN']
        if 'JIRA_SERVER_URL' in os.environ:
            del os.environ['JIRA_SERVER_URL']

    @patch('jira_mcp_server.requests.get')
    def test_search_returns_rank_and_team(self, mock_get):
        """Test that search_jira_issues returns rank and team fields."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 2,
            'issues': [
                {
                    'key': 'PROJECT-123',
                    'fields': {
                        'summary': 'Issue with rank and team',
                        'description': 'Description',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Story'},
                        'priority': {'name': 'High'},
                        'assignee': {'displayName': 'John Doe'},
                        'reporter': {'displayName': 'Jane Smith'},
                        'created': '2025-01-01T10:00:00.000+0000',
                        'updated': '2025-01-15T15:30:00.000+0000',
                        'fixVersions': [],
                        'customfield_10000': '2|hpos4o:',  # Rank
                        'customfield_10803': {'id': 386, 'name': 'Platform Team'}  # Team
                    }
                },
                {
                    'key': 'PROJECT-124',
                    'fields': {
                        'summary': 'Issue without team',
                        'description': 'Description',
                        'status': {'name': 'Open'},
                        'issuetype': {'name': 'Bug'},
                        'priority': {'name': 'Medium'},
                        'assignee': None,
                        'reporter': {'displayName': 'Bob'},
                        'created': '2025-01-05T10:00:00.000+0000',
                        'updated': '2025-01-10T15:30:00.000+0000',
                        'fixVersions': [],
                        'customfield_10000': '2|hpos5a:',  # Rank
                        'customfield_10803': None  # No team assigned
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = search_jira_issues('project = PROJECT ORDER BY Rank ASC', max_results=10)

        self.assertEqual(result['status'], 'success')

        # Check first issue has rank and team
        issue1 = result['issues'][0]
        self.assertEqual(issue1['rank'], '2|hpos4o:')
        self.assertEqual(issue1['team'], 'Platform Team')

        # Check second issue has rank but empty team
        issue2 = result['issues'][1]
        self.assertEqual(issue2['rank'], '2|hpos5a:')
        self.assertEqual(issue2['team'], '')

    @patch('jira_mcp_server.requests.get')
    def test_get_issue_with_relations_returns_rank_and_team(self, mock_get):
        """Test that get_issue_with_relations returns rank and team fields."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Issue with rank and team',
                'description': 'Description',
                'status': {'name': 'In Progress'},
                'issuetype': {'name': 'Story'},
                'priority': {'name': 'High'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [{'name': 'Release 1.0'}],
                'customfield_10000': '2|hpoq7g:',  # Rank
                'customfield_10803': {'id': 100, 'name': 'Infrastructure Team'},
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        result = get_issue_with_relations(
            self.issue_key, self.token, self.jira_url,
            include_subtasks=False, include_linked_issues=False
        )

        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']
        self.assertEqual(issue_data['rank'], '2|hpoq7g:')
        self.assertEqual(issue_data['team'], 'Infrastructure Team')

    @patch('jira_mcp_server.requests.get')
    def test_rank_and_team_with_null_values(self, mock_get):
        """Test that null rank and team values are handled correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'PROJECT-123',
            'fields': {
                'summary': 'Unranked issue',
                'description': 'Description',
                'status': {'name': 'Open'},
                'issuetype': {'name': 'Task'},
                'priority': {'name': 'Low'},
                'assignee': None,
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fixVersions': [],
                'customfield_10000': None,  # No rank
                'customfield_10803': None,  # No team
                'subtasks': [],
                'issuelinks': []
            }
        }
        mock_get.return_value = mock_response

        result = get_issue_with_relations(
            self.issue_key, self.token, self.jira_url,
            include_subtasks=False, include_linked_issues=False
        )

        self.assertEqual(result['status'], 'success')
        issue_data = result['issue_data']
        # Null values should become empty strings
        self.assertEqual(issue_data['rank'], '')
        self.assertEqual(issue_data['team'], '')

    @patch('jira_mcp_server.get_issue_comments')
    @patch('jira_mcp_server.get_issue_with_relations')
    def test_get_jira_issue_details_includes_rank_and_team(self, mock_get_relations, mock_get_comments):
        """Test that get_jira_issue_details returns rank and team from the underlying function."""
        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {
                'key': 'PROJECT-123',
                'summary': 'Test Issue',
                'description': 'Description',
                'status': 'Open',
                'type': 'Bug',
                'priority': 'High',
                'assignee': 'John Doe',
                'reporter': 'Jane Smith',
                'created': '2025-01-01T10:00:00.000+0000',
                'updated': '2025-01-15T15:30:00.000+0000',
                'fix_versions': ['Release 1.0'],
                'rank': '2|hpos4o:',
                'team': 'Measurement (EVMC: EVM) Team',
                'subtasks': [],
                'linked_issues': []
            }
        }
        mock_get_comments.return_value = []

        result = get_jira_issue_details(
            self.issue_key,
            include_comments=False,
            include_subtasks=True,
            include_linked_issues=True
        )

        self.assertEqual(result['status'], 'success')
        issue = result['issue']
        self.assertEqual(issue['rank'], '2|hpos4o:')
        self.assertEqual(issue['team'], 'Measurement (EVMC: EVM) Team')


class TestBackwardCompatibility(unittest.TestCase):
    """Test suite to ensure backward compatibility."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ['JIRA_API_TOKEN'] = 'test_token_123'
        os.environ['JIRA_SERVER_URL'] = 'https://jira.example.com'

    def tearDown(self):
        """Clean up after tests."""
        if 'JIRA_API_TOKEN' in os.environ:
            del os.environ['JIRA_API_TOKEN']
        if 'JIRA_SERVER_URL' in os.environ:
            del os.environ['JIRA_SERVER_URL']

    @patch('jira_mcp_server.get_issue_comments')
    @patch('jira_mcp_server.get_issue_with_relations')
    def test_default_parameters_include_all_relations(self, mock_get_relations, mock_get_comments):
        """Test that default parameters include all relations for convenience."""
        # Mock the response
        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {
                'key': 'PROJECT-123',
                'summary': 'Test',
                'description': '',
                'status': 'Open',
                'type': 'Task',
                'priority': 'Medium',
                'assignee': '',
                'reporter': '',
                'created': '',
                'updated': '',
                'subtasks': [],
                'linked_issues': []
            }
        }
        mock_get_comments.return_value = []

        # Call with no optional parameters (should use defaults)
        result = get_jira_issue_details('PROJECT-123')

        # Assertions
        self.assertEqual(result['status'], 'success')

        # Verify that get_issue_with_relations was called with True for both relations
        call_kwargs = mock_get_relations.call_args[1]
        self.assertTrue(call_kwargs['include_subtasks'])
        self.assertTrue(call_kwargs['include_linked_issues'])

        # Verify comments were fetched
        mock_get_comments.assert_called_once()


class TestGetJiraFieldMetadata(unittest.TestCase):
    """Test suite for the get_jira_field_metadata helper function."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ['JIRA_API_TOKEN'] = 'test_token_123'
        os.environ['JIRA_SERVER_URL'] = 'https://jira.example.com'

    def tearDown(self):
        """Clean up after tests."""
        if 'JIRA_API_TOKEN' in os.environ:
            del os.environ['JIRA_API_TOKEN']
        if 'JIRA_SERVER_URL' in os.environ:
            del os.environ['JIRA_SERVER_URL']

    @patch('jira_mcp_server.requests.get')
    def test_get_all_fields(self, mock_get):
        """Test getting all fields without filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "summary", "name": "Summary", "custom": False, "schema": {"type": "string"}},
            {"id": "customfield_10803", "name": "Team", "custom": True, "schema": {"type": "team"}},
            {"id": "customfield_10000", "name": "Rank", "custom": True, "schema": {"type": "string"}}
        ]
        mock_get.return_value = mock_response

        result = get_jira_field_metadata()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['fields']), 3)

    @patch('jira_mcp_server.requests.get')
    def test_filter_by_field_name(self, mock_get):
        """Test filtering fields by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "summary", "name": "Summary", "custom": False, "schema": {"type": "string"}},
            {"id": "customfield_10803", "name": "Team", "custom": True, "schema": {"type": "team"}},
            {"id": "customfield_11000", "name": "Development Team", "custom": True, "schema": {"type": "string"}},
            {"id": "customfield_10000", "name": "Rank", "custom": True, "schema": {"type": "string"}}
        ]
        mock_get.return_value = mock_response

        result = get_jira_field_metadata(field_name="Team")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['fields']), 2)  # "Team" and "Development Team"
        for field in result['fields']:
            self.assertIn('team', field['name'].lower())

    @patch('jira_mcp_server.requests.get')
    def test_case_insensitive_filter(self, mock_get):
        """Test that field name filtering is case-insensitive."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "customfield_10803", "name": "Team", "custom": True, "schema": {}}
        ]
        mock_get.return_value = mock_response

        result = get_jira_field_metadata(field_name="TEAM")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['fields']), 1)

    def test_missing_token(self):
        """Test error when JIRA_API_TOKEN is missing."""
        del os.environ['JIRA_API_TOKEN']

        result = get_jira_field_metadata()

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_API_TOKEN not found', result['message'])

    def test_missing_url(self):
        """Test error when JIRA_SERVER_URL is missing."""
        del os.environ['JIRA_SERVER_URL']

        result = get_jira_field_metadata()

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_SERVER_URL not found', result['message'])

    @patch('jira_mcp_server.requests.get')
    def test_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        result = get_jira_field_metadata()

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA API error', result['message'])


class TestUpdateJiraIssue(unittest.TestCase):
    """Test suite for the update_jira_issue MCP tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.issue_key = "PROJECT-123"
        os.environ['JIRA_API_TOKEN'] = 'test_token_123'
        os.environ['JIRA_SERVER_URL'] = 'https://jira.example.com'

    def tearDown(self):
        """Clean up after tests."""
        if 'JIRA_API_TOKEN' in os.environ:
            del os.environ['JIRA_API_TOKEN']
        if 'JIRA_SERVER_URL' in os.environ:
            del os.environ['JIRA_SERVER_URL']

    def test_invalid_issue_key(self):
        """Test input validation for invalid issue key."""
        result = update_jira_issue("", summary="Test")
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid issue key', result['message'])

        result = update_jira_issue(None, summary="Test")
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid issue key', result['message'])

    def test_no_fields_provided(self):
        """Test error when no fields are provided to update."""
        result = update_jira_issue("PROJECT-123")
        self.assertEqual(result['status'], 'error')
        self.assertIn('No fields provided', result['message'])

    def test_missing_token(self):
        """Test error when JIRA_API_TOKEN is missing."""
        del os.environ['JIRA_API_TOKEN']

        result = update_jira_issue("PROJECT-123", summary="New Summary")

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_API_TOKEN not found', result['message'])

    def test_missing_url(self):
        """Test error when JIRA_SERVER_URL is missing."""
        del os.environ['JIRA_SERVER_URL']

        result = update_jira_issue("PROJECT-123", summary="New Summary")

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_SERVER_URL not found', result['message'])

    @patch('jira_mcp_server.get_issue_with_relations')
    @patch('jira_mcp_server.requests.put')
    def test_update_single_field_summary(self, mock_put, mock_get_relations):
        """Test updating just the summary field."""
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put.return_value = mock_put_response

        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {
                'key': 'PROJECT-123',
                'summary': 'Updated Summary',
                'description': '',
                'status': 'Open',
                'type': 'Task',
                'priority': 'Medium',
                'assignee': '',
                'reporter': '',
                'created': '',
                'updated': '',
                'fix_versions': [],
                'rank': '',
                'team': ''
            }
        }

        result = update_jira_issue("PROJECT-123", summary="Updated Summary")

        self.assertEqual(result['status'], 'success')
        self.assertIn('summary', result['updated_fields'])
        self.assertEqual(result['issue']['summary'], 'Updated Summary')

        # Verify the PUT request was made with correct payload
        call_args = mock_put.call_args
        self.assertIn('fields', call_args[1]['json'])
        self.assertEqual(call_args[1]['json']['fields']['summary'], 'Updated Summary')

    @patch('jira_mcp_server.get_issue_with_relations')
    @patch('jira_mcp_server.requests.put')
    def test_update_multiple_fields(self, mock_put, mock_get_relations):
        """Test updating multiple fields at once."""
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put.return_value = mock_put_response

        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {
                'key': 'PROJECT-123',
                'summary': 'New Summary',
                'description': 'New Description',
                'status': 'Open',
                'type': 'Task',
                'priority': 'High',
                'assignee': 'john.doe',
                'reporter': '',
                'created': '',
                'updated': '',
                'fix_versions': [],
                'rank': '',
                'team': ''
            }
        }

        result = update_jira_issue(
            "PROJECT-123",
            summary="New Summary",
            description="New Description",
            priority="High"
        )

        self.assertEqual(result['status'], 'success')
        self.assertIn('summary', result['updated_fields'])
        self.assertIn('description', result['updated_fields'])
        self.assertIn('priority', result['updated_fields'])

        # Verify the PUT request payload
        call_args = mock_put.call_args
        fields = call_args[1]['json']['fields']
        self.assertEqual(fields['summary'], 'New Summary')
        self.assertEqual(fields['description'], 'New Description')
        self.assertEqual(fields['priority'], {'name': 'High'})

    @patch('jira_mcp_server.get_issue_with_relations')
    @patch('jira_mcp_server.requests.put')
    def test_update_labels(self, mock_put, mock_get_relations):
        """Test updating labels field."""
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put.return_value = mock_put_response

        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {'key': 'PROJECT-123', 'summary': 'Test'}
        }

        result = update_jira_issue("PROJECT-123", labels=["bug", "urgent"])

        self.assertEqual(result['status'], 'success')
        self.assertIn('labels', result['updated_fields'])

        # Verify labels are passed as array
        call_args = mock_put.call_args
        self.assertEqual(call_args[1]['json']['fields']['labels'], ["bug", "urgent"])

    def test_labels_must_be_array(self):
        """Test that labels must be an array."""
        result = update_jira_issue("PROJECT-123", labels="not-an-array")
        self.assertEqual(result['status'], 'error')
        self.assertIn('Labels must be an array', result['message'])

    @patch('jira_mcp_server.get_issue_with_relations')
    @patch('jira_mcp_server.requests.put')
    def test_update_fix_versions(self, mock_put, mock_get_relations):
        """Test updating fix versions field."""
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put.return_value = mock_put_response

        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {'key': 'PROJECT-123', 'fix_versions': ['Release 1.0', 'Release 2.0']}
        }

        result = update_jira_issue("PROJECT-123", fix_versions=["Release 1.0", "Release 2.0"])

        self.assertEqual(result['status'], 'success')
        self.assertIn('fix_versions', result['updated_fields'])

        # Verify fix versions are converted to objects
        call_args = mock_put.call_args
        self.assertEqual(
            call_args[1]['json']['fields']['fixVersions'],
            [{"name": "Release 1.0"}, {"name": "Release 2.0"}]
        )

    def test_fix_versions_must_be_array(self):
        """Test that fix_versions must be an array."""
        result = update_jira_issue("PROJECT-123", fix_versions="not-an-array")
        self.assertEqual(result['status'], 'error')
        self.assertIn('Fix versions must be an array', result['message'])

    @patch('jira_mcp_server.get_issue_with_relations')
    @patch('jira_mcp_server.get_team_id_by_name')
    @patch('jira_mcp_server.requests.put')
    def test_update_team_custom_field(self, mock_put, mock_team_lookup, mock_get_relations):
        """Test updating the Team custom field."""
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put.return_value = mock_put_response

        # Mock team ID lookup - returns team ID for the given name
        mock_team_lookup.return_value = {
            'status': 'success',
            'team_id': 'team-uuid-123',
            'team_name': 'Platform Team'
        }

        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {'key': 'PROJECT-123', 'team': 'Platform Team'}
        }

        result = update_jira_issue("PROJECT-123", team="Platform Team")

        self.assertEqual(result['status'], 'success')
        self.assertIn('team', result['updated_fields'])

        # Verify team lookup was called with the team name
        mock_team_lookup.assert_called_once()

        # Verify team field uses the custom field ID with just the team ID as string
        call_args = mock_put.call_args
        fields = call_args[1]['json']['fields']
        # Default team field ID is customfield_10803
        self.assertIn('customfield_10803', fields)
        # Team field expects just the team ID as a string
        self.assertEqual(fields['customfield_10803'], 'team-uuid-123')

    @patch('jira_mcp_server.get_team_id_by_name')
    def test_update_team_lookup_fails(self, mock_team_lookup):
        """Test error when team lookup fails (team not found)."""
        mock_team_lookup.return_value = {
            'status': 'error',
            'message': "Team 'Nonexistent Team' not found. Available teams include: Team A, Team B"
        }

        result = update_jira_issue("PROJECT-123", team="Nonexistent Team")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Team lookup failed', result['message'])
        self.assertIn('not found', result['message'])

    @patch('jira_mcp_server.get_issue_with_relations')
    @patch('jira_mcp_server.requests.put')
    def test_unassign_issue(self, mock_put, mock_get_relations):
        """Test unassigning an issue by passing empty string for assignee."""
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put.return_value = mock_put_response

        mock_get_relations.return_value = {
            'status': 'success',
            'issue_data': {'key': 'PROJECT-123', 'assignee': ''}
        }

        result = update_jira_issue("PROJECT-123", assignee="")

        self.assertEqual(result['status'], 'success')
        self.assertIn('assignee (unassigned)', result['updated_fields'])

        # Verify assignee is set to None for unassignment
        call_args = mock_put.call_args
        self.assertIsNone(call_args[1]['json']['fields']['assignee'])

    @patch('jira_mcp_server.requests.put')
    def test_issue_not_found(self, mock_put):
        """Test handling of 404 error when issue doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_put.return_value = mock_response

        result = update_jira_issue("PROJECT-999", summary="Test")

        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'])

    @patch('jira_mcp_server.requests.put')
    def test_permission_denied(self, mock_put):
        """Test handling of 403 permission denied error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_put.return_value = mock_response

        result = update_jira_issue("PROJECT-123", summary="Test")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Permission denied', result['message'])

    @patch('jira_mcp_server.requests.put')
    def test_invalid_field_value(self, mock_put):
        """Test handling of 400 bad request with field errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"errors":{"priority":"Invalid priority name"}}'
        mock_response.json.return_value = {
            "errors": {"priority": "Invalid priority name"},
            "errorMessages": []
        }
        mock_put.return_value = mock_response

        result = update_jira_issue("PROJECT-123", priority="InvalidPriority")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid field value', result['message'])
        self.assertIn('priority', result['message'])

    @patch('jira_mcp_server.requests.put')
    def test_api_error(self, mock_put):
        """Test handling of general API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_put.return_value = mock_response

        result = update_jira_issue("PROJECT-123", summary="Test")

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA API error', result['message'])
        self.assertIn('500', result['message'])

    @patch('jira_mcp_server.requests.put')
    def test_exception_handling(self, mock_put):
        """Test exception handling."""
        mock_put.side_effect = Exception('Connection timeout')

        result = update_jira_issue("PROJECT-123", summary="Test")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Exception occurred', result['message'])
        self.assertIn('Connection timeout', result['message'])


class TestGetTeamIdByName(unittest.TestCase):
    """Tests for the get_team_id_by_name helper function."""

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.get')
    def test_team_found(self, mock_get):
        """Test successfully finding a team by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'issues': [
                {
                    'fields': {
                        'customfield_10803': {
                            'id': 'team-uuid-456',
                            'name': 'Security Team'
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = get_team_id_by_name('Security Team')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['team_id'], 'team-uuid-456')
        self.assertEqual(result['team_name'], 'Security Team')

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.get')
    def test_team_found_case_insensitive(self, mock_get):
        """Test that team name matching is case-insensitive."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'issues': [
                {
                    'fields': {
                        'customfield_10803': {
                            'id': 'team-uuid-789',
                            'name': 'Platform Team'
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Search with different case
        result = get_team_id_by_name('platform team')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['team_id'], 'team-uuid-789')

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.get')
    def test_team_not_found(self, mock_get):
        """Test error when team is not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'issues': [
                {
                    'fields': {
                        'customfield_10803': {
                            'id': 'team-uuid-111',
                            'name': 'Other Team'
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = get_team_id_by_name('Nonexistent Team')

        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'])
        self.assertIn('Available teams', result['message'])

    @patch.dict(os.environ, {'JIRA_SERVER_URL': 'https://jira.test.com'}, clear=True)
    def test_missing_token(self):
        """Test error when JIRA_API_TOKEN is missing."""
        result = get_team_id_by_name('Any Team')
        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_API_TOKEN not found', result['message'])

    @patch.dict(os.environ, {'JIRA_API_TOKEN': 'test-token'}, clear=True)
    def test_missing_url(self):
        """Test error when JIRA_SERVER_URL is missing."""
        result = get_team_id_by_name('Any Team')
        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_SERVER_URL not found', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.get')
    def test_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_team_id_by_name('Any Team')

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA API error', result['message'])


class TestRankJiraIssues(unittest.TestCase):
    """Test suite for the rank_jira_issues MCP tool."""

    def test_empty_issue_keys(self):
        """Test error when issue_keys is empty."""
        result = rank_jira_issues([])
        self.assertEqual(result['status'], 'error')
        self.assertIn('non-empty list', result['message'])

    def test_too_many_issues(self):
        """Test error when more than 50 issues are provided."""
        issue_keys = [f"PROJ-{i}" for i in range(51)]
        result = rank_jira_issues(issue_keys, rank_before="PROJ-100")
        self.assertEqual(result['status'], 'error')
        self.assertIn('Maximum 50', result['message'])

    def test_both_rank_before_and_after(self):
        """Test error when both rank_before and rank_after are provided."""
        result = rank_jira_issues(["PROJ-1"], rank_before="PROJ-2", rank_after="PROJ-3")
        self.assertEqual(result['status'], 'error')
        self.assertIn('only one of', result['message'].lower())

    def test_neither_rank_before_nor_after(self):
        """Test error when neither rank_before nor rank_after is provided."""
        result = rank_jira_issues(["PROJ-1"])
        self.assertEqual(result['status'], 'error')
        self.assertIn('Must specify either', result['message'])

    @patch.dict(os.environ, {'JIRA_SERVER_URL': 'https://jira.test.com'}, clear=True)
    def test_missing_token(self):
        """Test error when JIRA_API_TOKEN is missing."""
        result = rank_jira_issues(["PROJ-1"], rank_before="PROJ-2")
        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_API_TOKEN', result['message'])

    @patch.dict(os.environ, {'JIRA_API_TOKEN': 'test-token'}, clear=True)
    def test_missing_url(self):
        """Test error when JIRA_SERVER_URL is missing."""
        result = rank_jira_issues(["PROJ-1"], rank_before="PROJ-2")
        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_SERVER_URL', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com',
        'JIRA_RANK_FIELD': 'customfield_10000'
    })
    @patch('jira_mcp_server.requests.put')
    def test_success_rank_before(self, mock_put):
        """Test successful ranking before another issue."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_put.return_value = mock_response

        result = rank_jira_issues(["PROJ-1"], rank_before="PROJ-2")

        self.assertEqual(result['status'], 'success')
        self.assertIn('1 issue', result['message'])

        # Verify the request
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        payload = call_args.kwargs['json']
        self.assertEqual(payload['issues'], ["PROJ-1"])
        self.assertEqual(payload['rankBeforeIssue'], "PROJ-2")
        self.assertEqual(payload['rankCustomFieldId'], 10000)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com',
        'JIRA_RANK_FIELD': 'customfield_10000'
    })
    @patch('jira_mcp_server.requests.put')
    def test_success_rank_after(self, mock_put):
        """Test successful ranking after another issue."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_put.return_value = mock_response

        result = rank_jira_issues(["PROJ-1"], rank_after="PROJ-2")

        self.assertEqual(result['status'], 'success')

        # Verify the request uses rankAfterIssue
        call_args = mock_put.call_args
        payload = call_args.kwargs['json']
        self.assertEqual(payload['rankAfterIssue'], "PROJ-2")
        self.assertNotIn('rankBeforeIssue', payload)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com',
        'JIRA_RANK_FIELD': 'customfield_10000'
    })
    @patch('jira_mcp_server.requests.put')
    def test_success_multiple_issues(self, mock_put):
        """Test successful bulk ranking of multiple issues."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_put.return_value = mock_response

        result = rank_jira_issues(["PROJ-1", "PROJ-2", "PROJ-3"], rank_before="PROJ-4")

        self.assertEqual(result['status'], 'success')
        self.assertIn('3 issue', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_404_error(self, mock_put):
        """Test 404 error when issue not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_put.return_value = mock_response

        result = rank_jira_issues(["PROJ-1"], rank_before="PROJ-NONEXISTENT")

        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'].lower())

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_403_permission_denied(self, mock_put):
        """Test 403 error when permission denied."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_put.return_value = mock_response

        result = rank_jira_issues(["PROJ-1"], rank_before="PROJ-2")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Permission denied', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_400_invalid_request(self, mock_put):
        """Test 400 error for invalid request."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid issue key"
        mock_response.json.return_value = {"errorMessages": ["Invalid issue key format"]}
        mock_put.return_value = mock_response

        result = rank_jira_issues(["INVALID"], rank_before="PROJ-2")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_207_partial_success(self, mock_put):
        """Test 207 partial success response."""
        mock_response = Mock()
        mock_response.status_code = 207
        mock_response.json.return_value = {
            "entries": [
                {"issueKey": "PROJ-1", "issueId": 10001, "status": 204},
                {"issueKey": "PROJ-2", "issueId": 10002, "status": 400, "errors": ["Issue not found"]}
            ]
        }
        mock_put.return_value = mock_response

        result = rank_jira_issues(["PROJ-1", "PROJ-2"], rank_before="PROJ-3")

        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(result['successes']), 1)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(result['failures'][0]['issueKey'], 'PROJ-2')


class TestReorderJiraIssues(unittest.TestCase):
    """Test suite for the reorder_jira_issues MCP tool."""

    def test_empty_issue_keys(self):
        """Test error when issue_keys is empty."""
        result = reorder_jira_issues([])
        self.assertEqual(result['status'], 'error')
        self.assertIn('non-empty list', result['message'])

    def test_single_issue_without_after_issue(self):
        """Test error when only one issue provided without after_issue."""
        result = reorder_jira_issues(["PROJ-1"])
        self.assertEqual(result['status'], 'error')
        self.assertIn('at least 2 issues', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com',
        'JIRA_RANK_FIELD': 'customfield_10000'
    })
    @patch('jira_mcp_server.requests.put')
    def test_success_reorder_three_issues(self, mock_put):
        """Test successful reordering of 3 issues."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_put.return_value = mock_response

        result = reorder_jira_issues(["PROJ-1", "PROJ-2", "PROJ-3"])

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operations_completed'], 2)  # 2 rank operations for 3 issues

        # Verify rank_jira_issues was called twice:
        # 1. PROJ-2 after PROJ-1
        # 2. PROJ-3 after PROJ-2
        self.assertEqual(mock_put.call_count, 2)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com',
        'JIRA_RANK_FIELD': 'customfield_10000'
    })
    @patch('jira_mcp_server.requests.put')
    def test_success_with_after_issue(self, mock_put):
        """Test successful reordering with after_issue reference."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_put.return_value = mock_response

        result = reorder_jira_issues(["PROJ-5", "PROJ-6"], after_issue="PROJ-1")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operations_completed'], 2)  # 1 for placing after reference, 1 for chaining

        # Verify:
        # 1. First call: PROJ-5 after PROJ-1
        # 2. Second call: PROJ-6 after PROJ-5
        self.assertEqual(mock_put.call_count, 2)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com',
        'JIRA_RANK_FIELD': 'customfield_10000'
    })
    @patch('jira_mcp_server.requests.put')
    def test_single_issue_with_after_issue(self, mock_put):
        """Test single issue with after_issue is valid."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_put.return_value = mock_response

        result = reorder_jira_issues(["PROJ-5"], after_issue="PROJ-1")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operations_completed'], 1)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_failure_in_chain(self, mock_put):
        """Test handling when a middle operation fails."""
        # First call succeeds, second call fails
        mock_response_success = Mock()
        mock_response_success.status_code = 204

        mock_response_fail = Mock()
        mock_response_fail.status_code = 404

        mock_put.side_effect = [mock_response_success, mock_response_fail]

        result = reorder_jira_issues(["PROJ-1", "PROJ-2", "PROJ-3"])

        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['operations_completed'], 1)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(result['failures'][0]['issue'], 'PROJ-3')

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_first_operation_fails_with_after_issue(self, mock_put):
        """Test error when the first placement after reference fails."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_put.return_value = mock_response

        result = reorder_jira_issues(["PROJ-5", "PROJ-6"], after_issue="PROJ-NONEXISTENT")

        self.assertEqual(result['status'], 'error')
        self.assertIn('Failed to place', result['message'])


class TestEditJiraComment(unittest.TestCase):
    """Test suite for the edit_jira_comment MCP tool."""

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_edit_comment_success(self, mock_put):
        """Test successfully editing a comment."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "7309695",
            "body": "Updated comment text",
            "author": {"displayName": "Test User"},
            "created": "2025-01-15T10:00:00.000+0000",
            "updated": "2025-01-15T12:00:00.000+0000"
        }
        mock_put.return_value = mock_response

        result = edit_jira_comment("PROJECT-123", "7309695", "Updated comment text")

        self.assertEqual(result['status'], 'success')
        self.assertIn('comment', result)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_edit_comment_with_numeric_id(self, mock_put):
        """Test editing a comment with numeric comment_id (the bug fix scenario)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "7309695",
            "body": "Updated comment text",
            "author": {"displayName": "Test User"},
            "created": "2025-01-15T10:00:00.000+0000",
            "updated": "2025-01-15T12:00:00.000+0000"
        }
        mock_put.return_value = mock_response

        # Pass comment_id as int (the bug scenario)
        result = edit_jira_comment("PROJECT-123", 7309695, "Updated comment text")

        self.assertEqual(result['status'], 'success')
        # Verify the URL was called with string ID
        called_url = mock_put.call_args[0][0]
        self.assertIn("/comment/7309695", called_url)

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_edit_comment_with_string_id(self, mock_put):
        """Test editing a comment with string comment_id."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "7309695",
            "body": "Updated comment text"
        }
        mock_put.return_value = mock_response

        result = edit_jira_comment("PROJECT-123", "7309695", "Updated comment text")

        self.assertEqual(result['status'], 'success')
        called_url = mock_put.call_args[0][0]
        self.assertIn("/comment/7309695", called_url)

    def test_edit_comment_missing_token(self):
        """Test error when JIRA_API_TOKEN is not set."""
        with patch.dict(os.environ, {'JIRA_SERVER_URL': 'https://jira.test.com'}, clear=True):
            result = edit_jira_comment("PROJECT-123", "7309695", "New comment")

        self.assertEqual(result['status'], 'error')
        self.assertIn('JIRA_API_TOKEN', result['message'])

    def test_edit_comment_invalid_issue_key(self):
        """Test error with empty issue_key."""
        result = edit_jira_comment("", "7309695", "New comment")

        self.assertEqual(result['status'], 'error')
        self.assertIn('issue key', result['message'].lower())

    def test_edit_comment_invalid_comment_id(self):
        """Test error with empty comment_id."""
        result = edit_jira_comment("PROJECT-123", "", "New comment")

        self.assertEqual(result['status'], 'error')
        self.assertIn('comment ID', result['message'])

    @patch.dict(os.environ, {
        'JIRA_API_TOKEN': 'test-token',
        'JIRA_SERVER_URL': 'https://jira.test.com'
    })
    @patch('jira_mcp_server.requests.put')
    def test_edit_comment_404(self, mock_put):
        """Test error when issue or comment not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_put.return_value = mock_response

        result = edit_jira_comment("PROJECT-999", "7309695", "New comment")

        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'].lower())


if __name__ == '__main__':
    unittest.main()
