# Fyn-Runner Testing Strategy

## Overview

This document outlines the testing approach for the Fyn-Runner project. It provides guidelines for writing consistent, maintainable, and effective tests across the codebase.

## Testing Philosophy

- **Comprehensive Coverage**: Test both success paths and error conditions
- **Isolation**: Each test should focus on a specific functionality
- **Independence**: Tests should not depend on other tests
- **Clarity**: Tests should clearly communicate what is being tested and why

## Test Organization

### File Structure

- Tests should be placed in a directory structure that mirrors the source code
- Test files should be named `test_*.py` to match the module being tested
- Each test file should include the standard copyright header

### Class Structure

- Group tests for a specific class in a `Test{ClassName}` class
- Include a docstring explaining what is being tested
- Organize test methods to flow from basic to more complex scenarios

```python
# e.g.
class TestServerProxy:
    """Test suite for ServerProxy utility."""

    # Tests will go here
```

## Fixtures

- Use `pytest` fixtures for test setup and resource management
- Name fixtures to clearly indicate what they provide
- Use docstrings to explain what the fixture does
- Use `yield` pattern for cleanup when working with resources

```python
@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)
```

## Mocking

- Use `unittest.mock` for mocking dependencies
- Prefer `patch` and `patch.object` over other mocking methods
- Use context managers for patching when possible
- Be specific about what is being mocked to avoid overly brittle tests

```python
# Mocking a method on an instance
with patch.object(server_proxy, '_report_status') as mock_report_status:
    # Test code here

# Mocking a module function
with patch('requests.patch', side_effect=requests.exceptions.ConnectionError("Error")):
    # Test code here
```

## Test Method Naming and Structure

### Naming

- Use descriptive method names in the format `test_{method}_{scenario}`
- Names should clearly indicate what is being tested and under what conditions
- Examples: `test_report_status_success`, `test_report_status_timeout`

### Structure

Each test should follow this general structure:

1. **Arrange**: Set up test conditions, including mocks and inputs
2. **Act**: Call the method or function being tested
3. **Assert**: Verify the expected outcomes

```python
def test_report_status_success(self, server_proxy):
    """Test _report_status when the request is successful."""
    # Arrange
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "success"}

    with patch('requests.patch', return_value=mock_response):
        # Act
        result = server_proxy._report_status('idle')

        # Assert
        assert result == {"status": "success"}
        server_proxy.logger.debug.assert_called_once()
```

## Assertions

- Use simple `assert` statements rather than PyTest's `assert_*` methods
- When verifying mock calls, use methods like `assert_called_once()` and `assert_called_with()`
- Include descriptive error messages in complex assertions
- Verify all relevant side effects (logging, calls to dependencies)

## Special Considerations

### Global State and Side Effects

- Be careful with tests that affect global state (e.g., `atexit` handlers)
- Mock out or disable side effects that would cause issues in test environment
- When necessary, save and restore original state

```python
# Example of managing global state
original_register = atexit.register
atexit.register = MagicMock()
# Test code here
atexit.register = original_register
```

### Error Handling

- Use `pytest.raises` to test for expected exceptions
- Verify both the exception type and message when possible
- Test both normal error paths and edge cases

```python
with pytest.raises(ConnectionError) as exc_info:
    server_proxy._report_status('idle')
assert "Failed to report status" in str(exc_info.value)
```

### Resource Cleanup

- Always clean up resources (files, connections, etc.) after tests
- Use fixtures with `yield` to ensure cleanup happens even if tests fail
- Be aware of potential resource leaks in tests

## Continuous Integration

- All tests should pass in the CI environment
- Tests should not rely on specific environment configurations
- Use mock objects and fixtures to isolate tests from external dependencies

## Example Test

```python
def test_create_logger_dev_mode(self, temp_log_dir):
    """Test logger in dev mode with console output."""
    logger = create_logger(temp_log_dir, dev_mode=True)

    assert len(logger.handlers) == 2
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
```
