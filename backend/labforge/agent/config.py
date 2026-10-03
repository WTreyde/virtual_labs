"""Load the project's simple KEY=value .env without overriding shell settings.

Supports blank values and quoted values. No shell execution or interpolation.
"""
import os
import shlex
from pathlib import Path
from labforge.contracts import REPO_ROOT

ENV_KEYS = {"ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_WORKSPACE_ID", "AMASS_API_KEY", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"}


def load_env(path: Path | None = None) -> None:
    path = path or Path(os.getenv('LABFORGE_ENV_FILE', str(REPO_ROOT / '.env')))
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, raw = line.partition('=')
        key = key.strip()
        if not sep or key not in ENV_KEYS or key in os.environ:
            continue
        parts = shlex.split(raw, comments=True, posix=True)
        if len(parts) > 1:
            raise ValueError(f"Invalid .env format for {key}: quote values containing spaces")
        os.environ[key] = parts[0] if parts else ''
