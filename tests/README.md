# Proxtract Test Suite

This directory contains comprehensive unit tests for the Proxtract project, covering all major components with extensive edge case and error handling scenarios.

## Test Structure

The test suite is organized into the following files:

- `conftest.py` - Shared fixtures and test configuration
- `test_core.py` - Tests for the core extraction logic (FileExtractor class)
- `test_state.py` - Tests for application state management (AppState class)
- `test_config.py` - Tests for configuration persistence functionality
- `test_main.py` - Tests for CLI interface and argument parsing
- `test_tui.py` - Tests for Textual UI components
- `test_widgets.py` - Tests for custom TUI widgets

## Test Coverage

### Core Functionality (`test_core.py`)
- **ExtractionStats**: Data class properties, serialization, and backward compatibility
- **FileExtractor**: 
  - Initialization with various configurations
  - File filtering and exclusion logic
  - Binary file detection and handling
  - Encoding detection and fallback mechanisms
  - Progress callback functionality
  - Error handling for various failure scenarios
  - Gitignore integration
  - Token counting capabilities
  - Include/exclude pattern matching
  - File size limits and empty file handling

### State Management (`test_state.py`)
- **AppState**:
  - Default and custom initialization
  - FileExtractor creation with current state
  - Path handling and expansion
  - Pattern list management
  - Field independence and data isolation
  - Type compatibility and serialization

### Configuration (`test_config.py`)
- Configuration file path management
- TOML loading and parsing with error handling
- Configuration application to AppState
- Save/load roundtrip testing
- Missing dependency handling
- File system error scenarios
- Escape sequence handling in saved config

### CLI Interface (`test_main.py`)
- Argument parsing for all CLI options
- State management through CLI arguments
- Progress reporting and error display
- Clipboard integration
- Configuration persistence
- Mutual exclusivity of options
- TUI launch functionality
- Error handling in extraction workflow

### TUI Components (`test_tui.py`)
- **ProxtractApp**: Application lifecycle, key bindings, config persistence
- **ExtractScreen**: Modal workflow, input validation, progress tracking
- **MainScreen**: Settings management, action handling, value editing
- **EditSettingScreen**: Value input and validation
- Screen navigation and state synchronization
- Error handling and user feedback

### Widget Components (`test_widgets.py`)
- **ActionItem**: Action display and selection
- **SettingItem**: Setting display, editing, and value formatting
- **SettingMetadata**: Configuration and type handling
- **SummaryDisplay**: Statistics rendering and updates

## Running Tests

### Install Test Dependencies

```bash
pip install -e ".[dev]"
```

Or install manually:
```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=src/proxtract --cov-report=term-missing --cov-report=html
```

### Run Specific Test Categories

```bash
# Only unit tests
pytest -m unit

# Only core functionality
pytest -m core

# Only TUI tests
pytest -m tui

# Only CLI tests
pytest -m cli

# Only config tests
pytest -m config
```

### Run Specific Test File

```bash
pytest tests/test_core.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Stop on First Failure

```bash
pytest -x
```

## Test Configuration

The test suite is configured in `pyproject.toml` under `[tool.pytest.ini_options]`:

- **Minimum pytest version**: 6.0
- **Test paths**: `tests/`
- **Coverage threshold**: 80%
- **Output formats**: Terminal, HTML, XML
- **Warning filters**: Suppress known warnings from dependencies
- **Markers**: Custom markers for test categorization

## Test Fixtures

The `conftest.py` file provides the following fixtures:

- `temp_dir`: Temporary directory for test file operations
- `sample_project_dir`: Pre-configured project structure with various file types
- `binary_files_dir`: Directory with binary files for testing detection
- `extractor`: Configured FileExtractor instance
- `app_state`: Configured AppState instance
- `mock_pathspec`: Mocked pathspec module for gitignore testing
- `mock_tiktoken`: Mocked tiktoken module for token counting tests
- `mock_console`: Mocked Rich Console for CLI output testing

## Test Patterns and Best Practices

### Mocking Strategy
- **External dependencies**: `pathspec`, `tiktoken`, `pyperclip`, `rich.console`
- **File system operations**: Temporary directories and file mocking
- **UI components**: Widget and screen interaction mocking
- **Network and clipboard**: Platform-specific functionality

### Error Handling Tests
- Invalid file paths and permissions
- Corrupted configuration files
- Missing dependencies
- Network failures (clipboard, etc.)
- Malformed user input
- Resource exhaustion scenarios

### Edge Case Testing
- Empty files and directories
- Very large files
- Files with unusual encodings
- Special characters in paths
- Concurrent access scenarios
- Platform-specific differences

### Performance Considerations
- Tests are designed to run quickly
- Long-running tests are marked with `@pytest.mark.slow`
- Parallel execution friendly
- Minimal resource usage

## Continuous Integration

The test suite is designed to work with CI systems:

- **Exit codes**: Proper exit codes for success/failure
- **Coverage reporting**: HTML and XML reports for integration
- **JUnit XML**: Compatible with most CI systems
- **Parallel execution**: Support for pytest-xdist

## Test Data Management

- **Temporary files**: All test files created in temporary directories
- **Cleanup**: Automatic cleanup after test completion
- **Isolation**: Tests are independent and can run in any order
- **Reproducibility**: Deterministic test data and behavior

## Adding New Tests

When adding new tests:

1. **Follow naming conventions**: `test_*` functions, `Test*` classes
2. **Use appropriate fixtures**: Leverage existing fixtures when possible
3. **Mark slow tests**: Use `@pytest.mark.slow` for long-running tests
4. **Test error conditions**: Include failure scenarios
5. **Document complex test logic**: Add clear docstrings
6. **Maintain coverage**: Ensure new features are well-covered

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure the source directory is in Python path
2. **Missing dependencies**: Install all optional dependencies
3. **Permission errors**: Check temporary directory permissions
4. **Platform-specific failures**: Some tests may behave differently on Windows/Linux/macOS

### Debug Mode

Run tests in debug mode for more detailed output:

```bash
pytest --tb=long -v
```

### Specific Test Debugging

To run a single test with full output:

```bash
pytest -xvs tests/test_core.py::TestFileExtractor::test_specific_method
```

## Coverage Goals

The test suite aims for:
- **Overall coverage**: 80%+ (configurable in pyproject.toml)
- **Critical paths**: 100% coverage for core extraction logic
- **Error handling**: All error paths tested
- **Edge cases**: Comprehensive boundary condition testing
- **Integration**: Cross-component interaction testing

## Maintenance

- **Regular updates**: Update tests when adding new features
- **Dependency tracking**: Keep mock dependencies in sync
- **Performance monitoring**: Watch for slow tests over time
- **Coverage analysis**: Regularly review coverage reports
- **Documentation**: Keep test documentation current

## Contributing

When contributing new tests:

1. Ensure all new tests pass
2. Maintain or improve coverage percentages
3. Follow existing test patterns and naming conventions
4. Update this README if adding new test categories
5. Test on multiple platforms if possible

## License

The test suite follows the same license as the main Proxtract project.