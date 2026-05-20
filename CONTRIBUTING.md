# Contributing to Sophra Client OSS

Thank you for your interest in contributing to the Sophra Client! This document provides guidelines to help you get started.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/sophra-client-oss.git`
3. Create a feature branch: `git checkout -b feat/your-feature-name`
4. Make your changes
5. Test your changes locally
6. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `git commit -m "feat: add new health metric"`
7. Push and open a Pull Request

## Development Setup

```bash
cd sophra-client-oss
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Code Style

- **Python 3.10+** required
- **2-space indentation** in all files
- **camelCase** for variables and functions
- **PascalCase** for class names
- Run your code through a linter before submitting

## What We're Looking For

- New agent health metrics (beyond entropy, hallucination rate, etc.)
- Improved rehabilitation strategies
- Better CLI UX and documentation
- Bug fixes and security improvements
- Performance optimizations

## Reporting Issues

Please use GitHub Issues and include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
