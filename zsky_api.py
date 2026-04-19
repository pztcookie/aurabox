"""
ZSky AI — optional remote backend (only if you have a working enterprise URL + key).

Note: ZSky's public site states there is no self-serve API; https://api.zsky.ai often fails TLS
(SSL EOF) because it may not expose a normal public HTTPS API. Use AURABOX_FLUX_BACKEND=pollinations
for a free, keyless fallback, or get the exact base URL from ZSky for your account.

Environment:
  ZSKY_API_KEY       — required
  ZSKY_API_URL       — optional, default https://api.zsky.ai/v1/generate (often unreliable)
  ZSKY_MODEL         — optional, default "flux"
  ZSKY_HTTP_RETRIES  — optional, default 4

pip install -r requirements-zsky.txt for `requests` (better TLS than urllib alone).
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_ZSKY_URL = "https://api.zsky.ai/v1/generate"
ZSKY_HTTP_RETRIES = int(os.environ.get("ZSKY_HTTP_RETRIES", "4"))


def _retryable_net_err(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(
        x in s
        for x in (
            "ssl",
            "eof",
            "connection",
            "reset",
            "timed out",
            "timeout",
            "broken pipe",
            "temporarily",
        )
    )


def _fetch_url_bytes(url: str, timeout: int = 120) -> bytes:
    headers = {"User-Agent": "AuraBox/1.0"}
    try:
        import requests

        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.content
    except ImportError:
        pass

    ctx = ssl.create_default_context()
    last: BaseException | None = None
    for attempt in range(ZSKY_HTTP_RETRIES):
        try:
            req = Request(url, method="GET", headers=headers)
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except (URLError, OSError) as e:
            last = e
            if attempt < ZSKY_HTTP_RETRIES - 1 and _retryable_net_err(e):
                time.sleep(1.0 * (attempt + 1))
                continue
            raise RuntimeError(f"ZSky image download failed: {e}") from e
    raise RuntimeError(f"ZSky image download failed: {last}")


def _post_zsky(
    url: str,
    headers: dict[str, str],
    body: bytes,
    timeout: int = 180,
) -> tuple[bytes, str]:
    """POST JSON; return (raw_body, content_type). Retries on transient SSL/connection errors."""
    try:
        import requests

        h = dict(headers)
        r = requests.post(url, data=body, headers=h, timeout=timeout)
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if r.status_code >= 400:
            detail = r.text[:2000]
            try:
                j = r.json()
                detail = str(j.get("error", j.get("message", detail)))
            except Exception:
                pass
            raise RuntimeError(f"ZSky HTTP {r.status_code}: {detail}")
        return r.content, ctype
    except ImportError:
        pass

    req = Request(url, data=body, method="POST", headers=headers)
    ctx = ssl.create_default_context()
    last: BaseException | None = None
    for attempt in range(ZSKY_HTTP_RETRIES):
        try:
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                return raw, ctype
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace") if e.fp else ""
            try:
                j = json.loads(detail)
                detail = str(j.get("error", j.get("message", detail)))
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"ZSky HTTP {e.code}: {detail[:1200]}") from e
        except (URLError, OSError) as e:
            last = e
            if attempt < ZSKY_HTTP_RETRIES - 1 and _retryable_net_err(e):
                time.sleep(1.2 * (attempt + 1))
                continue
            raise RuntimeError(
                f"ZSky network error (after {attempt + 1} tries): {e}. "
                "Try: pip install requests  (better TLS). Or check VPN/firewall and ZSKY_API_URL."
            ) from e
    raise RuntimeError(f"ZSky network error: {last}")


def _extract_image_from_json(obj: Any) -> bytes | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        for key in ("image_base64", "b64_json", "base64", "image"):
            val = obj.get(key)
            if isinstance(val, str) and val and not val.startswith("http"):
                try:
                    return base64.b64decode(val)
                except Exception:
                    pass

        for key in ("image_url", "url", "href"):
            val = obj.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return _fetch_url_bytes(val)

        for nest in ("data", "images", "results", "output"):
            if nest in obj:
                got = _extract_image_from_json(obj[nest])
                if got:
                    return got

        if "image" in obj and isinstance(obj["image"], dict):
            return _extract_image_from_json(obj["image"])

    if isinstance(obj, list) and obj:
        return _extract_image_from_json(obj[0])

    return None


def _raise_if_api_error(data: dict) -> None:
    err = data.get("error") or data.get("message")
    if not err:
        return
    if isinstance(err, dict):
        err = err.get("message", str(err))
    raise RuntimeError(f"ZSky API error: {err}")


def generate_zsky_png(prompt: str, width: int, height: int) -> bytes:
    api_key = (os.environ.get("ZSKY_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "Set ZSKY_API_KEY to your ZSky AI API key (free tier ~100 calls/day). "
            "Get it from the ZSky AI developer / dashboard."
        )

    url = (os.environ.get("ZSKY_API_URL") or DEFAULT_ZSKY_URL).strip()
    model = (os.environ.get("ZSKY_MODEL") or "flux").strip()

    payload = {
        "prompt": prompt,
        "model": model,
        "width": width,
        "height": height,
        "num_images": 1,
    }

    body = json.dumps(payload).encode("utf-8")
    hdrs = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json, image/png, image/jpeg, image/webp, */*",
        "User-Agent": "AuraBox/1.0",
        "Connection": "close",
    }

    raw, ctype = _post_zsky(url, hdrs, body, timeout=180)

    if ctype.startswith("image/"):
        return raw
    if raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:2] == b"\xff\xd8":
        return raw

    if "application/json" in ctype or raw.strip().startswith(b"{"):
        data = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            out = _extract_image_from_json(data)
            if out:
                return out
            _raise_if_api_error(data)
        else:
            out = _extract_image_from_json(data)
            if out:
                return out
        raise RuntimeError(
            f"ZSky returned JSON but no image field recognized. First 500 chars: {str(data)[:500]}"
        )

    raise RuntimeError(f"Unexpected ZSky response Content-Type: {ctype or 'unknown'}")
