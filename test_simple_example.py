"""
Simple working test examples you can run right now

Install: pip install pytest
Run: pytest test_simple_example.py -v
"""

import pytest
import json
import tempfile
import os
import sys
from datetime import datetime, timedelta


# ===== SIMPLE UNIT TESTS =====

def test_basic_assertion():
    """Most basic test - just assert something is true"""
    assert 2 + 2 == 4


def test_string_operations():
    """Test string operations"""
    customer_name = "Example Customer"
    assert customer_name.lower() == "example customer"
    assert "example" in customer_name.lower()


def test_list_operations():
    """Test working with lists"""
    tenants = [
        {'name': 'Customer A', 'id': '1'},
        {'name': 'Customer B', 'id': '2'},
    ]
    assert len(tenants) == 2
    assert tenants[0]['name'] == 'Customer A'


# ===== TESTING EXCEPTIONS =====

def test_exception_handling():
    """Test that code raises expected exceptions"""
    with pytest.raises(ValueError):
        int("not a number")

    with pytest.raises(KeyError):
        test_dict = {'a': 1}
        _ = test_dict['b']


# ===== TESTING WITH FIXTURES =====

@pytest.fixture
def sample_tenant_data():
    """Fixture provides reusable test data"""
    return {
        'customerName': 'Test Customer',
        'customerId': '12345',
        'prismaId': '999',
        'licenseDetails': {
            'marketplaceData': {
                'tenantId': '777',
                'serialNumber': '888'
            }
        }
    }


def test_using_fixture(sample_tenant_data):
    """Test that uses the fixture"""
    assert sample_tenant_data['customerName'] == 'Test Customer'
    assert sample_tenant_data['customerId'] == '12345'


# ===== PARAMETERIZED TESTS =====

@pytest.mark.parametrize("input,expected", [
    ("example", "example"),
    ("EXAMPLE", "example"),
    ("Example", "example"),
    ("  example  ", "  example  "),  # Doesn't strip whitespace
])
def test_lowercase_conversion(input, expected):
    """Run same test with different inputs"""
    assert input.lower() == expected


# ===== TESTING FILE OPERATIONS =====

def test_temp_file_operations():
    """Test file operations using temp directory"""
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test-cache.json")

    # Write test data
    test_data = {'test': 'data'}
    with open(test_file, 'w') as f:
        json.dump(test_data, f)

    # Read and verify
    assert os.path.exists(test_file)
    with open(test_file, 'r') as f:
        loaded_data = json.load(f)
    assert loaded_data == test_data

    # Cleanup
    os.remove(test_file)


# ===== TESTING DATETIME LOGIC =====

def test_cache_expiry_logic():
    """Test the 8-hour cache expiry logic from your script"""
    now = datetime.now()
    hours_ago = now - timedelta(hours=8)

    # Cache from 9 hours ago should be expired
    old_cache = now - timedelta(hours=9)
    assert old_cache < hours_ago  # Should delete

    # Cache from 7 hours ago should still be valid
    fresh_cache = now - timedelta(hours=7)
    assert fresh_cache > hours_ago  # Should keep


# ===== TESTING SEARCH LOGIC =====

def test_customer_search_logic():
    """Test the customer search logic from your script"""
    customer_name_lower = "example"

    # Test different match scenarios
    assert customer_name_lower in "example customer".lower()  # Match
    assert customer_name_lower in "999".lower() or customer_name_lower in "example customer".lower()  # OR logic
    assert not (customer_name_lower in "different".lower())  # No match


def test_marketplace_data_handling():
    """Test handling of None marketplaceData (the bug we fixed)"""
    tenant = {
        'licenseDetails': {
            'marketplaceData': None
        }
    }

    # Initialize variables like we do in the fixed code
    tenant_id = ''
    serial_num = ''

    if tenant['licenseDetails']['marketplaceData'] is not None:
        tenant_id = str(tenant['licenseDetails']['marketplaceData']['tenantId'])
        serial_num = str(tenant['licenseDetails']['marketplaceData']['serialNumber'])

    # Should not crash, variables should be empty strings
    assert tenant_id == ''
    assert serial_num == ''


# ===== TESTING API RETRY LOGIC =====

def test_exponential_backoff_calculation():
    """Test the exponential backoff delays we implemented"""
    delays = []
    for retry in range(1, 4):
        delay = 2 ** retry
        delays.append(delay)

    assert delays == [2, 4, 8]  # Our new backoff pattern
    assert sum(delays) == 14  # Total wait time


# ===== MOCKING EXAMPLE =====

def test_with_mock():
    """Example of mocking (requires pytest-mock)"""
    from unittest.mock import Mock

    # Create a mock object
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.content = json.dumps({'token': 'test-123'}).encode()

    # Test the mock
    assert mock_response.ok is True
    assert mock_response.status_code == 200
    data = json.loads(mock_response.content)
    assert data['token'] == 'test-123'


# ===== CONDITIONAL TESTS =====

@pytest.mark.skip(reason="Example of skipping a test")
def test_this_will_be_skipped():
    """This test won't run"""
    assert False


@pytest.mark.skipif(sys.platform == "win32", reason="Unix only test")
def test_unix_only():
    """This test only runs on Unix systems"""
    assert True


# ===== GROUPING TESTS =====

class TestGroupExample:
    """Group related tests in a class"""

    def test_one(self):
        assert True

    def test_two(self):
        assert True


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, '-v'])
