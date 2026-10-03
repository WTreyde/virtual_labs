"""Credential-safe diagnostics shared by local and SSE interfaces."""
import os


def safe_error(exc):
    if isinstance(exc, ModuleNotFoundError):
        return f'Missing dependency: {exc.name}. Install the backend dependencies, then retry.'
    body = getattr(exc, 'body', None)
    if isinstance(body, dict):
        error = body.get('error', body)
        if isinstance(error, dict) and isinstance(error.get('message'), str):
            detail = error['message']
            for name in ['ANTHROPIC_API_KEY', 'AMASS_API_KEY', 'MODAL_TOKEN_SECRET']:
                value = os.getenv(name)
                if value:
                    detail = detail.replace(value, '[redacted]')
            return f'{type(exc).__name__} (HTTP {getattr(exc, "status_code", "unknown")}): {detail[:2000]}'
    return f'{type(exc).__name__}: the run failed. Check API access, credentials and model configuration.'



def redacted_json(value):
    import json
    data = json.dumps(value)
    for name in ["ANTHROPIC_API_KEY", "AMASS_API_KEY", "MODAL_TOKEN_SECRET"]:
        secret = os.getenv(name)
        if secret:
            data = data.replace(secret, "[redacted]")
    return data
