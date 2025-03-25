# Contributing to Syclops

Thank you for your interest in contributing to Syclops! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Development Environment](#development-environment)
- [Development Workflow](#development-workflow)
- [Contributing Code](#contributing-code)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Development Tools](#development-tools)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors. Any form of harassment or discriminatory behavior will not be tolerated.

## Development Environment

Before starting development:

1. Read the [installation instructions](README.md#⚡️getting-started) in the README.
2. Fork and clone the repository
3. Set up your development environment according to the README instructions

For detailed development environment requirements and troubleshooting, refer to the [documentation](https://dfki-ni.github.io/syclops/).

## Development Workflow

1. Create a new branch for your work:
```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch prefixes:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation changes
- `refactor/` for code refactoring

2. Make your changes, following our code style guidelines
3. Write/update tests
4. Commit your changes with clear commit messages
5. Push to your fork and submit a pull request

### Code Style Guidelines

- Follow PEP 8 standards for Python code
- Use meaningful variable and function names
- Document functions and classes using docstrings
- Keep functions focused and concise
- Add comments for complex logic

## Contributing Code

### Plugin Development

For adding new functionality through plugins, refer to our comprehensive documentation:

- [Creating Scene Plugins](https://dfki-ni.github.io/syclops/developement/add_functionality/create_plugin/)
- [Creating Sensor and Output Plugins](https://dfki-ni.github.io/syclops/developement/add_functionality/create_sensor/)
- [Architecture Overview](https://dfki-ni.github.io/syclops/developement/architecture/)

These guides provide detailed examples, schema file creation instructions, and best practices for plugin development.

### Documentation Requirements

- Add docstrings to all new functions and classes
- Update relevant documentation files
- Include examples for new features
- Document any new configuration options
- Add a schema file for new configuration options ([Schema Docs](https://dfki-ni.github.io/syclops/developement/add_functionality/create_plugin/?h=schema#schema))

## Pull Request Process

1. Ensure your code passes all tests
2. Update documentation for any changed functionality
3. Request review from project maintainers
4. Address review feedback

PR template:
```markdown
## Description
[Describe your changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Added/updated unit tests
- [ ] Tested manually

## Documentation
- [ ] Updated relevant documentation
```

## Issue Reporting

### Bug Reports

When reporting bugs, include:

1. Syclops version
2. Python version
3. Operating system
4. Steps to reproduce
5. Expected vs actual behavior
6. Error messages and stack traces

### Feature Requests

When requesting features:

1. Describe the problem you're trying to solve
2. Explain your proposed solution
3. Discuss alternatives you've considered
4. Provide example use cases

## Development Tools

### Testing and Debugging

#### Testing
Your contribution must pass all integration tests before it can be merged. We use GitHub Actions for continuous integration. Check our [integration test workflow](.github/workflows/integration_test.yaml) to understand the testing requirements.

The integration tests verify:
- Pipeline functionality
- Output file generation
- Format compliance
- Documentation builds

#### Debugging
For detailed debugging instructions, including:
- Visual debugging in Blender
- IDE integration
- Pipeline debugging
- Breakpoint usage

Refer to our [Debugging Guide](https://dfki-ni.github.io/syclops/developement/debugging/).

## Community

### Getting Help

- Search the [documentation](https://dfki-ni.github.io/syclops/)
- Check existing issues on GitHub
- Join discussions in pull requests

### Contact

For bug reports and feature requests, please use GitHub issues. For security concerns, please email the maintainers directly.

## License

By contributing to Syclops, you agree that your contributions will be licensed under the project's license.
