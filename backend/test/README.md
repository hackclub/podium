**PLEASE NOTE:** These tests were more of an experiment to see if stress-testing could be automated with AI agents. It's slower than would be ideal, but they do seem to work. Even if they are less deterministic and reproducible compared to traditional tests, they mimic how users would interact with the application.

## Running Tests

```bash
# Run all tests
uv run pytest -s

# Run specific test file
uv run pytest -s test_admin.py

# Run specific test
uv run pytest -s -k "test_admin_event_management"
```

## Test Structure

- `conftest.py` - Test configuration and fixtures
- `test_admin.py` - Admin router tests (this works reasonably well)
- `test_events.py` - Event management tests  
- `test_user.py` - User management tests
- `browser.py` - Browser automation utilities
- `utils.py` - Test utilities and helpers

## Environment Variables

- `STEEL_API_KEY` - Required for browser automation
- `NGROK_AUTH_TOKEN` - Required for ngrok tunneling
- `BROWSER_USE_LOGGING_LEVEL` - Set to `result` to make the browser agent less verbose

## Debugging Tips

1. **Backend logs are now visible** during test execution
2. **Check Steel viewer URLs** in test output for visual debugging
3. **Use `-s` flag** to see print statements and logs
4. **Use `-v` flag** for verbose test output
5. **Use `-k` flag** to run specific tests by name pattern