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
    search_jira_issues
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


if __name__ == '__main__':
    unittest.main()
