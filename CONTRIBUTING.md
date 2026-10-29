# Contributing

Thanks for helping out! Bug reports, fixes and new integrations are all welcome.

## Development setup

```bash
git clone https://github.com/kuttim/smartposti-tracker.git
cd smartposti-tracker
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

```bash
ruff check .          # lint
pytest                # unit tests (offline, API is mocked)
pytest -m live        # optional: smoke test against the real API
```

`pytest -m live` uses a real tracking code from the `SMARTPOSTI_TEST_CODE`
environment variable and is skipped if it is not set.

## Guidelines

- Keep the core dependency-free apart from `requests`. Integrations with extra
  dependencies (Telegram, email, databases, ...) belong in `examples/` or behind
  an optional extra.
- Add or update tests for behaviour changes.
- Add a line under **Unreleased** in `CHANGELOG.md`.
- The API is undocumented. If it changes, describe what you observed (request,
  response shape) in the issue or PR. A HAR export from the browser's dev tools
  on the smartposti.ee tracking page is the easiest way to show it.
