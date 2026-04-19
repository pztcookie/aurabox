"""
Pollinations image API — free, no API key, stable HTTPS (good fallback when ZSky/HF fail).

GET https://image.pollinations.ai/prompt/{urlencoded_prompt}?width=&height=&model=&nologo=true

Set POLLINATIONS_MODEL (default flux) if you want another model name their service supports.
"""

from __future__ import annotations

import os
import ssl
import time
import urllib.parse
from urllib.error import URLError
from urllib.request import Request, urlopen

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"
ZSKY_HTTP_RETRIES = int(os.environ.get("POLLINATIONS_HTTP_RETRIES", os.environ.get("ZSKY_HTTP_RETRIES", "4")))


def _retryable(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(x in s for x in ("ssl", "eof", "connection", "reset", "timeout", "timed out"))


def generate_pollinations_image(prompt: str, width: int, height: int) -> bytes:
    encoded = urllib.parse.quote(prompt, safe="")
    model = (os.environ.get("POLLINATIONS_MODEL") or "flux").strip()
    w = max(64, min(width, 2048))
    h = max(64, min(height, 2048))
    url = (
        f"{POLLINATIONS_BASE}{encoded}"
        f"?width={w}&height={h}&model={urllib.parse.quote(model)}&nologo=true"
    )

    try:
        import requests

        r = requests.get(
            url,
            timeout=180,
            headers={"User-Agent": "AuraBox/1.0"},
        )
        r.raise_for_status()
        return r.content
    except ImportError:
        pass

    req = Request(url, method="GET", headers={"User-Agent": "AuraBox/1.0"})
    ctx = ssl.create_default_context()
    last: BaseException | None = None
    for attempt in range(ZSKY_HTTP_RETRIES):
        try:
            with urlopen(req, timeout=180, context=ctx) as resp:
                return resp.read()
        except (URLError, OSError) as e:
            last = e
            if attempt < ZSKY_HTTP_RETRIES - 1 and _retryable(e):
                time.sleep(1.0 * (attempt + 1))
                continue
            raise RuntimeError(f"Pollinations fetch failed: {e}") from e
    raise RuntimeError(f"Pollinations fetch failed: {last}")
