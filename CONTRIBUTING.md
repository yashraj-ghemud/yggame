# Contributing to yggame

Please open an issue before substantial changes, keep public APIs documented, add deterministic tests for behavior changes, and run the quality gate locally before opening a pull request.

```bash
python -m pip install -e '.[dev]'
ruff check src tests examples
mypy src/yggame
python -m pytest -q
python -m build
python -m twine check dist/*
```

All contributions should preserve the MIT license and retain the project attribution to **Yashraj Sachin Ghemud**.

## Developer credit

The original developer and project maintainer is **Yashraj Sachin Ghemud**.
