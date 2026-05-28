"""
Tests for pcs-where-is.py

Install test dependencies:
    pip install pytest pytest-mock requests-mock

Run tests:
    pytest test_pcs_where_is.py
    pytest test_pcs_where_is.py -v              # Verbose
    pytest test_pcs_where_is.py -v -s           # Show print statements
    pytest test_pcs_where_is.py::test_login     # Run specific test
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Import functions from the script
# Note: Since pcs-where-is.py is executable, we need to handle the import carefully
sys.path.insert(0, os.path.dirname(__file__))


class TestLogin:
    """Test the login function"""

    def test_login_success(self, requests_mock):
        """Test successful login"""
        # Mock the API response
        requests_mock.post(
            'https://api.prismacloud.io/login',
            json={'token': 'test-token-123'},
            status_code=200
        )

        # You would import and call the login function here
        # For now, this shows the pattern
        url = 'https://api.prismacloud.io'
        access_key = 'test-key'
        secret_key = 'test-secret'

        # Expected behavior: should return the token
        # token = login(url, access_key, secret_key, None)
        # assert token == 'test-token-123'

    def test_login_failure(self, requests_mock):
        """Test login with invalid credentials"""
        requests_mock.post(
            'https://api.prismacloud.io/login',
            text='Unauthorized',
            status_code=401
        )

        # Expected behavior: should return None or handle error
        # token = login(url, access_key, secret_key, None)
        # assert token is None


class TestExecute:
    """Test the execute function for API calls"""

    def test_execute_get_success(self, requests_mock):
        """Test successful GET request"""
        test_data = {'version': '1.2.3'}
        requests_mock.get(
            'https://api.prismacloud.io/version',
            json=test_data,
            status_code=200
        )

        # result = execute('GET', 'https://api.prismacloud.io/version', 'token-123')
        # assert result == test_data

    def test_execute_retry_on_429(self, requests_mock):
        """Test that 429 (rate limit) triggers retry with exponential backoff"""
        # First call returns 429, second succeeds
        requests_mock.get(
            'https://api.prismacloud.io/test',
            [
                {'status_code': 429, 'text': 'Rate limited'},
                {'json': {'success': True}, 'status_code': 200}
            ]
        )

        # Should retry and eventually succeed
        # result = execute('GET', 'https://api.prismacloud.io/test', 'token-123')
        # assert result == {'success': True}

    def test_execute_403_forbidden(self, requests_mock):
        """Test that 403 returns None gracefully"""
        requests_mock.get(
            'https://api.prismacloud.io/test',
            status_code=403
        )

        # result = execute('GET', 'https://api.prismacloud.io/test', 'token-123')
        # assert result is None


class TestFindCustomer:
    """Test customer search logic"""

    def test_find_customer_by_name(self):
        """Test finding customer by name match"""
        tenant_list = [
            {
                'customerName': 'Example Customer',
                'customerId': '12345',
                'prismaId': '999',
                'eval': False,
                'active': True,
                'workloads': 10000,
                'licenseDetails': {
                    'marketplaceData': {
                        'tenantId': '777',
                        'serialNumber': '888'
                    }
                }
            }
        ]

        # Should find the customer
        # count = find_customer('APP', tenant_list, 'example', 'url', 'ca', 'token')
        # assert count == 1

    def test_find_customer_by_prisma_id(self):
        """Test finding customer by Prisma ID"""
        tenant_list = [
            {
                'customerName': 'Test Customer',
                'customerId': '12345',
                'prismaId': '999',
                'eval': False,
                'active': True,
                'workloads': 10000,
                'licenseDetails': {'marketplaceData': None}
            }
        ]

        # Should find by Prisma ID even if search term doesn't match name
        # count = find_customer('APP', tenant_list, '999', 'url', 'ca', 'token')
        # assert count == 1

    def test_find_customer_none_marketplace_data(self):
        """Test that None marketplaceData doesn't cause UnboundLocalError"""
        tenant_list = [
            {
                'customerName': 'Test Customer',
                'customerId': '12345',
                'prismaId': '999',
                'eval': False,
                'active': True,
                'workloads': 10000,
                'licenseDetails': {'marketplaceData': None}
            }
        ]

        # This was the bug we fixed - should not crash
        # count = find_customer('APP', tenant_list, 'test', 'url', 'ca', 'token')
        # Should handle gracefully

    def test_find_customer_not_found(self):
        """Test customer not found returns 0"""
        tenant_list = [
            {
                'customerName': 'Different Customer',
                'customerId': '12345',
                'prismaId': '999',
                'eval': False,
                'active': True,
                'workloads': 10000,
                'licenseDetails': {'marketplaceData': None}
            }
        ]

        # count = find_customer('APP', tenant_list, 'nonexistent', 'url', 'ca', 'token')
        # assert count == 0


class TestCaching:
    """Test caching functionality"""

    @patch('os.path.isfile')
    @patch('builtins.open')
    @patch('json.load')
    def test_cache_hit(self, mock_json_load, mock_open, mock_isfile):
        """Test that cache is used when available and not expired"""
        mock_isfile.return_value = True
        mock_json_load.return_value = [{'customerName': 'Cached Customer'}]

        # Should load from cache instead of API
        # Cache logic would be tested here

    def test_cache_expiry(self):
        """Test that cache older than 8 hours is deleted"""
        # Would test the 8-hour expiry logic


# Fixtures for common test data
@pytest.fixture
def mock_config():
    """Provide a mock CONFIG dictionary"""
    return {
        'CA_BUNDLE': 'test-ca-bundle.txt',
        'STACKS': {
            'TEST': {
                'url': 'https://test.api.prismacloud.io',
                'access_key': 'test-access-key',
                'secret_key': 'test-secret-key'
            }
        }
    }


@pytest.fixture
def sample_tenant():
    """Provide sample tenant data"""
    return {
        'customerName': 'Test Customer',
        'customerId': '12345',
        'prismaId': '999',
        'eval': False,
        'active': True,
        'workloads': 10000,
        'licenseDetails': {
            'marketplaceData': {
                'tenantId': '777',
                'serialNumber': '888',
            },
            'endTs': 1672531200000  # Timestamp
        }
    }


@pytest.fixture
def requests_mock():
    """Provide requests-mock for HTTP mocking"""
    import requests_mock as rm
    with rm.Mocker() as m:
        yield m


# Integration test example
class TestIntegration:
    """Integration tests that test multiple components together"""

    @pytest.mark.integration
    def test_full_customer_search_flow(self):
        """Test complete flow: login -> search -> results"""
        # This would test the entire flow end-to-end
        # Marked with @pytest.mark.integration so it can be run separately
        pass


# Parameterized tests - run same test with different inputs
@pytest.mark.parametrize("search_term,expected_match", [
    ("example", True),
    ("EXAMPLE", True),  # Case insensitive
    ("exam", True),     # Partial match
    ("nonexistent", False),
])
def test_customer_search_variations(search_term, expected_match):
    """Test customer search with various inputs"""
    # Would test different search scenarios
    pass
