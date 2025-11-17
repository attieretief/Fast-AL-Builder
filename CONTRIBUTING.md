# Contributing to Fast AL Builder

Thank you for your interest in contributing to Fast AL Builder! This document provides guidelines and information for contributors.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use the issue template and provide:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (runner OS, AL version, etc.)
   - Relevant logs or error messages

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes with clear commit messages
4. Test your changes thoroughly
5. Update documentation if needed
6. Submit a pull request with description of changes

### Development Guidelines

#### Code Style
- Use descriptive variable and function names
- Add comments for complex logic
- Follow shell scripting best practices
- Use proper error handling with `set -e`

#### Testing
- Test on both Ubuntu and macOS runners when possible
- Include test cases for new features
- Ensure backward compatibility
- Test with multiple BC versions if applicable

#### Documentation
- Update README.md for new features
- Add examples for new functionality
- Update parameter documentation
- Include troubleshooting information

### Development Setup

1. Clone the repository
2. Make changes to scripts in the `scripts/` directory
3. Update `action.yml` if adding new parameters
4. Test locally using act or GitHub Actions

### Script Development

#### Shell Scripts (`scripts/`)
- Use `#!/bin/bash` shebang
- Include `set -e` for error handling
- Use proper quoting for variables
- Add descriptive comments
- Output progress using echo with emojis
- Set GitHub outputs using `>> $GITHUB_OUTPUT`

#### Testing Scripts
- Validate input parameters
- Handle edge cases gracefully
- Provide clear error messages
- Test with various AL project structures

### Release Process

1. Update version in `action.yml`
2. Update `CHANGELOG.md`
3. Create a new release with semantic versioning
4. Tag the release appropriately

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow GitHub's community guidelines

## Questions?

Feel free to open an issue for:
- Feature requests
- Technical questions
- Documentation improvements
- General feedback

Thank you for contributing to Fast AL Builder!