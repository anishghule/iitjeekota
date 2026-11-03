"""The only way dsapkit reaches the network.

HTTPS only, an explicit host allowlist per caller, a size cap and retries with
backoff. Callers verify what they receive (file signatures, SHA-256 locks).
"""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request

from .errors import BuildError

DEFAULT_MAX_BYTES = 4 * 1024 * 1024


def https_get(url: str, *, allow: frozenset[str], user_agent: str,
              max_bytes: int = DEFAULT_MAX_BYTES, attempts: int = 3) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allow:
        raise BuildError(f"refusing to download {url}: only https from {sorted(allow)}")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})  # noqa: S310 (https and an allowed host, checked above)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310
                data = response.read(max_bytes + 1)
            break
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt == attempts:
                raise BuildError(f"download failed after {attempts} attempts: {url}: {err}") from err
            time.sleep(1.5 * attempt)
    if len(data) > max_bytes:
        raise BuildError(f"{url} is larger than {max_bytes} bytes")
    return data
