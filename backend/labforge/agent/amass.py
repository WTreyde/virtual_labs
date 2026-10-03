"""Read-only BiomedCore retrieval. API contract: https://api.amass.tech/api/doc.

Retrieved papers are candidates, not proof of a processing time or yield.
"""
import hashlib
import json
import os
import time
from pathlib import Path

import httpx

API_URL = 'https://api.amass.tech/api/v1/cores/biomedcore/records'
TTL_S = 86400


def retrieve_literature(query: str, limit: int = 5, *, cache_dir: Path | None = None) -> dict:
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise ValueError('Use a nonempty literature query of at most 1000 characters')
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError('limit must be an integer between 1 and 10')
    key = os.getenv('AMASS_API_KEY', '').strip()
    if not key:
        return {'status': 'unconfigured', 'items': [], 'note': 'AMASS_API_KEY is missing; use explicit estimates, not invented evidence.'}
    query = query.strip()
    # Key-scoped caches avoid sharing licensed results between credentials; never store a key.
    digest = hashlib.sha256(json.dumps([key, query, limit]).encode()).hexdigest()
    cache_dir = cache_dir or Path(os.getenv('LABFORGE_EVIDENCE_CACHE', str(Path.home() / '.cache/labforge/evidence')))
    cache = cache_dir / f'{digest}.json'
    cached = None
    try:
        cached = json.loads(cache.read_text())
        if time.time() - cached['fetched_at'] < TTL_S:
            return {'status': 'cached', 'items': cached['items'], 'fetched_at': cached['fetched_at'], 'note': 'Literature candidates; check relevance before citing numerical assumptions.'}
    except (OSError, ValueError, KeyError, TypeError):
        cached = None
    try:
        response = httpx.get(API_URL, headers={'Authorization': f'Bearer {key}'},
                             params={'query': query, 'limit': limit, 'isRetracted': 'false'}, timeout=20)
        response.raise_for_status()
        data = response.json()['data']
        records = data.get('records') if isinstance(data, dict) else data
        if not isinstance(records, list):
            raise ValueError('Unexpected Amass response envelope')
        items = []
        for record in records[:limit]:
            if not isinstance(record, dict) or record.get('isRetracted') or not record.get('amassId'):
                continue
            source = ('https://doi.org/' + record['doi']) if record.get('doi') else (
                'https://pubmed.ncbi.nlm.nih.gov/' + str(record['pmid']) + '/' if record.get('pmid') else record['amassId'])
            title = str(record.get('title') or 'Untitled record')
            items.append({'amass_id': record['amassId'], 'title': title,
                          'abstract': str(record.get('abstract') or '')[:4000],
                          'publication_date': record.get('publicationDate'),
                          'evidence': {'claim': 'Literature candidate: ' + title, 'source': source, 'provider': 'amass'}})
        fetched_at = time.time()
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Atomic replacement: concurrent local requests never read half-written JSON.
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', dir=cache_dir, delete=False) as temp:
                json.dump({'fetched_at': fetched_at, 'items': items}, temp)
                temporary = Path(temp.name)
            temporary.replace(cache)
        except OSError:
            pass  # Read-only cache locations must not fail a successful retrieval.
        return {'status': 'retrieved', 'items': items, 'fetched_at': fetched_at,
                'note': 'Literature candidates; check relevance before citing numerical assumptions.'}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        # Do not return exception text, which may contain headers or credentials.
        return {'status': 'unavailable', 'items': [],
                'note': 'Amass retrieval failed (access, network, rate limit or response format). No evidence returned; disclose estimates and retry later.'}


def search_literature(query: str, limit: int = 5) -> list[dict]:
    """Backward-compatible list of evidence candidates."""
    return [item['evidence'] for item in retrieve_literature(query, limit)['items']]
