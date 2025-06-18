# Contributing to SynthScribe

Thank you for your interest in contributing to SynthScribe! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use issue templates when available
3. Provide clear descriptions and steps to reproduce
4. Include system information (OS, Python version, etc.)

### Suggesting Enhancements

1. Open an issue with the "enhancement" label
2. Clearly describe the enhancement and its benefits
3. Provide examples or mockups if applicable
4. Be open to discussion and feedback

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding standards** (see below)
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass** before submitting
6. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Local Development

```bash
# Clone your fork
git clone https://github.com/yourusername/synthscribe.git
cd synthscribe

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=synthscribe --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

### Code Quality Checks

```bash
# Format code with black
black .

# Check linting
flake8

# Type checking
mypy synthscribe

# Run all checks
make lint  # If Makefile is available
```

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:
- Line length: 88 characters (Black default)
- Use type hints for all functions
- Docstrings for all public functions and classes

### Example Code Style

```python
from typing import List, Optional

def get_recommendations(
    mood: str,
    user_id: Optional[str] = None,
    count: int = 4
) -> List[MusicSuggestion]:
    """
    Generate music recommendations based on mood.
    
    Args:
        mood: Description of user's current mood or activity
        user_id: Optional user identifier for personalization
        count: Number of recommendations to return
        
    Returns:
        List of MusicSuggestion objects
        
    Raises:
        ValueError: If mood is empty or count is invalid
    """
    if not mood.strip():
        raise ValueError("Mood cannot be empty")
    
    # Implementation here
    pass
```

### Commit Messages

Follow the Conventional Commits specification:

```
feat: add Spotify integration
fix: resolve parsing error for multi-genre suggestions
docs: update API documentation
test: add tests for recommendation engine
refactor: simplify prompt template logic
perf: optimize LLM response caching
chore: update dependencies
```

### Branch Naming

- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test additions/updates
- `refactor/description` - Code refactoring

## Testing Guidelines

### Test Structure

```python
import pytest
from synthscribe.recommendation import RecommendationEngine

class TestRecommendationEngine:
    """Test cases for RecommendationEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create test instance"""
        return RecommendationEngine()
    
    def test_basic_recommendation(self, engine):
        """Test basic recommendation generation"""
        # Arrange
        mood = "coding late at night"
        
        # Act
        results = engine.get_recommendations(mood)
        
        # Assert
        assert len(results) == 4
        assert all(r.genre for r in results)
```

### Test Coverage

- Aim for 80%+ code coverage
- Test edge cases and error conditions
- Include integration tests for external services
- Mock external API calls in unit tests

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def complex_function(param1: str, param2: int) -> dict:
    """
    Brief description of function.
    
    Longer description if needed, explaining the purpose
    and any important details about the implementation.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When and why this is raised
        
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result["status"])
        success
    """
    pass
```

### README Updates

When adding new features:
1. Update feature list
2. Add usage examples
3. Update installation instructions if needed
4. Add to relevant sections

## Review Process

### What We Look For

1. **Code Quality**: Clean, readable, maintainable code
2. **Tests**: Comprehensive test coverage
3. **Documentation**: Clear comments and docstrings
4. **Performance**: No significant performance regressions
5. **Security**: No security vulnerabilities introduced

### Review Timeline

- Initial review: Within 48 hours
- Follow-up responses: Within 24 hours
- Merge decision: Within 1 week

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in relevant documentation

## Questions?

- Open an issue with the "question" label
- Join our Discord community (coming soon)
- Email: synthscribe@example.com

Thank you for contributing to SynthScribe!