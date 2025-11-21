# Contributing to PMLLM

Thank you for your interest in contributing to the PMLLM project!

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/pmllm.git`
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and configure your environment variables

## Code Style Guidelines

- Follow PEP 8 Python style guide
- Use type hints for function parameters and return values
- Add docstrings to all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names

## Security Best Practices

- Never commit secrets, passwords, or API keys
- Use environment variables for sensitive configuration
- Add new secrets to `.env.example` with placeholder values
- Review code for potential security vulnerabilities before committing

## Error Handling

- Use specific exception types instead of bare `except:` clauses
- Provide helpful error messages
- Handle edge cases and invalid input gracefully
- Log errors appropriately

## Testing

- Test your changes before submitting a PR
- Ensure all existing functionality still works
- Add tests for new features when applicable

## Pull Request Process

1. Create a new branch for your feature: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Test thoroughly
4. Commit with clear, descriptive messages
5. Push to your fork
6. Open a Pull Request with a clear description of changes

## Code Review

All submissions require review. We'll provide feedback and work with you to ensure quality and consistency.

## Questions?

Feel free to open an issue for questions or discussions about the project.
