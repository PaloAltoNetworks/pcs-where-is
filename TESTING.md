# Testing Guide for Python

## Quick Start

```bash
# Install testing dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_simple_example.py -v

# Run specific test
pytest test_simple_example.py::test_basic_assertion -v

# Run tests with coverage report
pytest --cov=. --cov-report=html

# Run tests and stop at first failure
pytest -x
```

## Test Organization

```
your-project/
├── pcs-where-is.py           # Your code
├── test_pcs_where_is.py      # Tests for pcs-where-is.py
├── test_simple_example.py    # Example tests to learn from
├── requirements.txt           # Production dependencies
└── requirements-test.txt      # Testing dependencies
```

## Writing Tests - Basic Patterns

### 1. Simple Assertion Test
```python
def test_addition():
    assert 2 + 2 == 4
```

### 2. Test with Setup/Teardown
```python
import tempfile
import os

def test_file_creation():
    # Setup
    temp_file = os.path.join(tempfile.gettempdir(), 'test.txt')
    
    # Test
    with open(temp_file, 'w') as f:
        f.write('test')
    
    assert os.path.exists(temp_file)
    
    # Teardown
    os.remove(temp_file)
```

### 3. Using Fixtures (Reusable Test Data)
```python
import pytest

@pytest.fixture
def sample_config():
    return {
        'url': 'https://api.example.com',
        'access_key': 'test-key'
    }

def test_config_loading(sample_config):
    assert sample_config['url'].startswith('https')
```

### 4. Testing Exceptions
```python
import pytest

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        result = 1 / 0
```

### 5. Parameterized Tests (Multiple Inputs)
```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

### 6. Mocking API Calls
```python
def test_api_call(requests_mock):
    # Mock the API response
    requests_mock.get(
        'https://api.example.com/data',
        json={'result': 'success'},
        status_code=200
    )
    
    import requests
    response = requests.get('https://api.example.com/data')
    assert response.json() == {'result': 'success'}
```

## Common pytest Commands

```bash
# Show available tests without running
pytest --collect-only

# Run tests matching a keyword
pytest -k "customer"

# Run tests with markers
pytest -m integration

# Show print statements
pytest -s

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate HTML report
pytest --html=report.html

# Watch for file changes and re-run (requires pytest-watch)
ptw
```

## Test Coverage

```bash
# Run with coverage
pytest --cov=. --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=. --cov-report=html
# Then open htmlcov/index.html in browser

# Check coverage threshold
pytest --cov=. --cov-fail-under=80
```

## Best Practices

### 1. Test File Naming
- Name test files `test_*.py` or `*_test.py`
- Name test functions `test_*`
- Name test classes `Test*`

### 2. One Assertion Per Test (Generally)
```python
# Good - focused test
def test_customer_name():
    customer = {'name': 'Example'}
    assert customer['name'] == 'Example'

# Avoid - testing too many things
def test_customer():
    customer = {'name': 'Example', 'id': '123', 'active': True}
    assert customer['name'] == 'Example'
    assert customer['id'] == '123'
    assert customer['active'] is True
```

### 3. Use Descriptive Test Names
```python
# Good
def test_login_returns_token_on_success():
    ...

# Bad
def test_login():
    ...
```

### 4. Arrange-Act-Assert Pattern
```python
def test_customer_search():
    # Arrange - setup test data
    customer_name = "example"
    tenants = [{'name': 'Example Customer'}]
    
    # Act - perform the action
    result = search_customer(customer_name, tenants)
    
    # Assert - verify the outcome
    assert result == 1
```

### 5. Don't Test External APIs Directly
Use mocking to avoid:
- Slow tests
- Flaky tests (network issues)
- Hitting rate limits
- Costs (if API charges per call)

## Testing Your Scripts

For your `pcs-where-is.py` and `pcs-app-stack-version.py`, focus on testing:

1. **Login function**
   - Successful login returns token
   - Failed login handles error
   - Network errors are retried

2. **Execute function**
   - GET/POST requests work
   - Retry logic with exponential backoff
   - 403 errors handled gracefully

3. **Customer search**
   - Finding by name (case-insensitive)
   - Finding by Prisma ID
   - Finding by tenant ID
   - Handling None marketplaceData

4. **Cache logic**
   - Cache hit uses cached data
   - Expired cache is deleted
   - Cache miss fetches fresh data

5. **Edge cases**
   - Empty tenant list
   - Malformed JSON responses
   - Network timeouts

## Running Your Example Tests

```bash
# Try it now!
pytest test_simple_example.py -v

# Output will show:
# ✓ test_basic_assertion PASSED
# ✓ test_string_operations PASSED
# ✓ test_customer_search_logic PASSED
# etc.
```

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **Real Python Testing Guide**: https://realpython.com/pytest-python-testing/
- **pytest-mock**: https://pytest-mock.readthedocs.io/
- **requests-mock**: https://requests-mock.readthedocs.io/
