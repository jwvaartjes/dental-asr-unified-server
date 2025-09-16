# Development Commands

## Starting the Server
```bash
# Navigate to project directory
cd /Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace/pairing_server

# Start unified server (handles ALL functionality)
python3 -m app.main
```

## Testing Commands
```bash
# Run all tests with pytest
pytest

# Run specific test categories
pytest -m normalization  # Normalization tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Exclude slow tests

# Run specific test files
pytest unittests/test_*.py

# Run normalization pipeline tests
python3 run_all_normalization_tests.py

# Debug specific normalization issues
python3 debug/test_debug_steps.py
python3 debug/test_time_unit_protection.py
python3 debug/test_hyphen_fix.py
```

## Development URLs (when server is running)
- **Main Server**: http://localhost:8089
- **API Documentation**: http://localhost:8089/docs
- **Complete Test Suite**: http://localhost:8089/api-test
- **Desktop Pairing Test**: http://localhost:8089/test-desktop.html
- **Mobile Pairing Test**: http://localhost:8089/test-mobile-local.html
- **Rate Limiter Test**: http://localhost:8089/test-rate-limiter
- **Health Check**: http://localhost:8089/health

## Utility Commands (macOS/Darwin)
```bash
# File operations
ls -la              # List files with details
find . -name "*.py" # Find Python files
grep -r "pattern"   # Search for pattern (use with care, prefer search tools)

# Git operations
git status          # Check git status
git log --oneline   # View commit history
git diff            # View changes

# Process management
ps aux | grep python    # Find Python processes
lsof -i :8089          # Check what's using port 8089
kill -9 <PID>          # Kill process by PID
```

## Testing Workflow
1. Start server: `python3 -m app.main`
2. Open test suite: http://localhost:8089/api-test
3. Test specific functionality with provided HTML test pages
4. Run pytest for unit/integration tests
5. Use debug scripts in `/debug/` folder for specific issues

## Important Note
- **Never use the old server** (`server_windows_spsc.py`) - it's deprecated
- All functionality is now on the unified server (port 8089)
- Test scripts should be placed in `/debug/` directory, not main directory