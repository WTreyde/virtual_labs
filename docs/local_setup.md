# Local setup

Use Python 3.11 or newer. From the repository root:

```bash
uv venv --python 3.11
uv pip install --python .venv/bin/python -e './backend[dev]'
.venv/bin/python validate_examples.py
```

For Claude credentials, the standalone agent workbench, example prompts, troubleshooting,
and CLI sessions, follow [Agent setup](../backend/labforge/agent/LIVE_RUN.md).

The backend and main frontend also have Makefile targets documented in the README.
The standalone workbench requires neither Node.js nor the main frontend.
