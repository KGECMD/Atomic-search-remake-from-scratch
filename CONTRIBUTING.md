# Contributing to Atomic Search

Thank you for your interest in contributing to Atomic Search!

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment.

## Getting Started

### Prerequisites

- Python 3.11+
- Redis (optional, for caching)
- Docker (optional)

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/atomic-search/atomic-search.git
cd atomic-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Start development server
python -m atomic_search.main
```

## Development Workflow

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and write tests
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to your branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

## Code Style

- Follow PEP 8
- Use type hints where possible
- Write docstrings for public functions
- Keep functions focused and small

```python
def search(query: str, limit: int = 10) -> List[SearchResult]:
    """
    Search for query and return results.
    
    Args:
        query: The search query string
        limit: Maximum number of results to return
        
    Returns:
        List of SearchResult objects
    """
    ...
```

## Testing

Write tests for all new features:

```python
def test_search_returns_results():
    results = search("python")
    assert len(results) > 0
    assert all(hasattr(r, 'title') for r in results)
```

Run tests with:
```bash
pytest tests/ -v
```

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Keep the first line under 72 characters

```
Add search result caching

- Implement LRU cache for search results
- Add cache invalidation on new results
- Update tests for cache functionality
```

## Pull Request Guidelines

- Fill out the PR template completely
- Reference any related issues
- Include screenshots for UI changes
- Ensure all tests pass
- Update documentation if needed

## Reporting Issues

- Use the GitHub issue tracker
- Include your environment details
- Provide steps to reproduce
- Include expected vs actual behavior

## Security

- Never commit secrets or API keys
- Report security vulnerabilities privately
- Follow secure coding practices

## Questions?

- Open a discussion on GitHub
- Join our community chat

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
