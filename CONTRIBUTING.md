# Contributing to Banger Link

First off, thank you for considering contributing to Banger Link! We appreciate your time and effort in making this project better.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- Ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/yourusername/banger-link/issues).
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/yourusername/banger-link/issues/new). Be sure to include a title and clear description, as much relevant information as possible, and a code sample or an executable test case demonstrating the expected behavior.

### Suggesting Enhancements

- Open a new issue with a clear title and description explaining the enhancement and why it would be useful.
- Include any relevant code, screenshots, or other resources that might help explain the enhancement.

### Your First Code Contribution

1. Fork the repository on GitHub.
2. Clone the forked repository to your local machine:
   ```bash
   git clone https://github.com/yourusername/banger-link.git
   cd banger-link
   ```
3. Create a new branch for your changes:
   ```bash
   git checkout -b your-feature-branch
   ```
4. Make your changes and commit them with a clear and descriptive commit message.
5. Push your changes to your fork:
   ```bash
   git push origin your-feature-branch
   ```
6. Open a pull request against the main branch of the original repository.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/banger-link.git
   cd banger-link
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

### Running Tests

```bash
pytest
```

### Code Style

We use `black` for code formatting and `isort` for import sorting. Please ensure your code adheres to these standards before submitting a pull request.

```bash
black .
isort .
```

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2. Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations, and container parameters.
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

## Questions?

If you have any questions, feel free to open an issue or contact the maintainers.
