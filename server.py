#!/usr/bin/env python3
"""
AuraBox dev server: static files + POST /api/flux-generate for character images.

Backends (env AURABOX_FLUX_BACKEND):

  pollinations (default) — Free image API, no key, reliable HTTPS (image.pollinations.ai).
      Optional: POLLINATIONS_MODEL (default flux).

  zsky — ZSky REST API. Official site: no self-serve public API; api.zsky.ai often fails TLS.
      Only if you have a working URL + key from ZSky: ZSKY_API_KEY, ZSKY_API_URL.

  local — Diffusers FLUX on GPU (requirements-flux.txt + HF_TOKEN).

  hf_hub / hf — Hugging Face (see server source).

Run (simplest, no GPU, no keys):
  python3 server.py

Open http://127.0.0.1:8000/index.html
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Remote InferenceClient default: open SD1.5 (CreativeML Open RAIL-M). Avoids paid fal-ai FLUX routes.
# Override: HF_IMAGE_MODEL_ID or HF_FLUX_MODEL_ID (legacy name).
DEFAULT_HF_HUB_MODEL_ID = "runwayml/stable-diffusion-v1-5"
# Legacy api-inference.huggingface.co/models/... often returns 404 now; use the router instead.
# Docs: https://huggingface.co/docs/api-inference/tasks/text-to-image
INFERENCE_URL_TEMPLATE = os.environ.get(
    "HF_INFERENCE_URL_TEMPLATE",
    "https://router.huggingface.co/hf-inference/models/{model_id}",
)


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")


def _get_remote_model_id() -> str:
    return (
        os.environ.get("HF_IMAGE_MODEL_ID")
        or os.environ.get("HF_FLUX_MODEL_ID")
        or DEFAULT_HF_HUB_MODEL_ID
    )


_hub_resolve_cache: tuple[str, str] | None = None


def _resolve_provider_and_model_for_hub() -> tuple[str, str]:
    """
    Avoid 402 from fal-ai: never use provider=auto (it picks fal for FLUX).
    Unless AURABOX_USE_FLUX_VIA_FAL=1, replace FLUX.* Hub ids with SD1.5 (free-tier friendly).
    Cached per process so startup + first request do not duplicate stderr.
    """
    global _hub_resolve_cache
    if _hub_resolve_cache is not None:
        return _hub_resolve_cache

    raw = (os.environ.get("HF_INFERENCE_PROVIDER") or "hf-inference").strip().lower()
    if raw in ("auto", ""):
        print(
            "[aurabox] HF_INFERENCE_PROVIDER was 'auto' or empty — forcing 'hf-inference' "
            "(provider=auto routes FLUX to fal-ai and triggers 402 when credits run out).",
            file=sys.stderr,
        )
        raw = "hf-inference"

    model_id = _get_remote_model_id()
    allow_paid_flux = os.environ.get("AURABOX_USE_FLUX_VIA_FAL", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if "flux" in model_id.lower() and not allow_paid_flux:
        print(
            f"[aurabox] Remote FLUX models go through paid fal-ai → 402 without credits. "
            f"Using open model {DEFAULT_HF_HUB_MODEL_ID!r} instead. "
            f"To force FLUX via fal (paid): export AURABOX_USE_FLUX_VIA_FAL=1 "
            f"and HF_INFERENCE_PROVIDER=fal-ai",
            file=sys.stderr,
        )
        model_id = DEFAULT_HF_HUB_MODEL_ID

    _hub_resolve_cache = (model_id, raw)
    return _hub_resolve_cache


def _inference_url() -> str:
    model_id = _get_remote_model_id()
    return INFERENCE_URL_TEMPLATE.format(model_id=model_id)


def _parse_hf_error_body(err_body: str) -> str:
    if not err_body:
        return ""
    try:
        j = json.loads(err_body)
    except json.JSONDecodeError:
        return err_body[:800]
    if isinstance(j, list) and j and isinstance(j[0], dict) and "error" in j[0]:
        return str(j[0].get("error", j))
    if isinstance(j, dict):
        return str(j.get("error", j.get("message", json.dumps(j)[:800])))
    return err_body[:800]


def _call_hf_text_to_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    max_retries: int = 3,
) -> bytes:
    token = _hf_token()
    if not token:
        raise RuntimeError(
            "Missing HF_TOKEN (or HUGGINGFACE_HUB_TOKEN). "
            "Export it before starting server.py, e.g. export HF_TOKEN=hf_..."
        )

    url = _inference_url()
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
            "guidance_scale": float(os.environ.get("HF_FLUX_GUIDANCE", "3.5")),
            "num_inference_steps": int(os.environ.get("HF_FLUX_STEPS", "28")),
        },
    }
    body = json.dumps(payload).encode("utf-8")

    last_error: str | None = None
    for attempt in range(max_retries):
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "image/png, image/jpeg, image/webp, application/json, */*",
            },
        )
        try:
            with urlopen(req, timeout=300) as resp:
                raw = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()

            if ctype == "application/json":
                data = json.loads(raw.decode("utf-8", errors="replace"))
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    if "error" in data[0]:
                        raise RuntimeError(str(data[0].get("error")))
                if isinstance(data, dict) and "error" in data:
                    raise RuntimeError(str(data.get("error", data)))
                # Some deployments return JSON-wrapped image; try common keys
                if isinstance(data, dict):
                    for key in ("image", "generated_image", "data"):
                        v = data.get(key)
                        if isinstance(v, str) and v.startswith("data:image"):
                            # data URL
                            if "," in v:
                                b64 = v.split(",", 1)[1]
                                return base64.b64decode(b64)
                raise RuntimeError(f"Unexpected JSON from HF (first 300 chars): {str(data)[:300]}")

            if ctype.startswith("image/"):
                return raw

            # Binary image without image/* (some proxies)
            if raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:2] == b"\xff\xd8":
                return raw

            raise RuntimeError(f"Unexpected Content-Type from HF: {ctype or 'unknown'}")

        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            msg = _parse_hf_error_body(err_body) or str(e)
            print(f"[aurabox] HF HTTP {e.code} from {url}: {msg[:500]}", file=sys.stderr)

            # Model warming / overloaded
            if e.code in (503, 429) and attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                time.sleep(wait)
                last_error = msg
                continue

            hint = ""
            if e.code == 403:
                hint = (
                    " Open the model page, click Access / agree to terms, and ensure your token can "
                    "call Inference Providers (fine-grained: 'Make calls to Inference Providers')."
                )
            elif e.code == 401:
                hint = " Check that HF_TOKEN is correct and not expired."

            raise RuntimeError(f"Hugging Face error ({e.code}): {msg}{hint}") from e

        except URLError as e:
            raise RuntimeError(f"Network error calling HF: {e}") from e

    raise RuntimeError(last_error or "Hugging Face request failed after retries")


def _call_hf_inference_client(prompt: str, width: int, height: int) -> tuple[bytes, str]:
    """
    Remote inference via huggingface_hub.InferenceClient.
    See _resolve_provider_and_model_for_hub(): we avoid provider=auto and remote FLUX → fal-ai (402).
    Paid FLUX: AURABOX_USE_FLUX_VIA_FAL=1 and HF_INFERENCE_PROVIDER=fal-ai.
    """
    token = _hf_token()
    if not token:
        raise RuntimeError(
            "Missing HF_TOKEN (or HUGGINGFACE_HUB_TOKEN). "
            "Same as Colab: export HF_TOKEN=hf_... before python3 server.py"
        )
    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise RuntimeError(
            "Install remote inference deps: pip install -r requirements-inference.txt "
            f"({e})"
        ) from e

    model_id, provider = _resolve_provider_and_model_for_hub()

    # SD v1.5 is 512-native; HF inference often rejects 1024×1024 for this checkpoint.
    w, h = width, height
    if "stable-diffusion-v1-5" in model_id:
        w = min(w, 512)
        h = min(h, 512)

    # Colab often uses api_key=; huggingface_hub accepts token= (same HF access token).
    client = InferenceClient(provider=provider, token=token)

    # Match optional tuning from env (passed if the installed hub supports these kwargs)
    extra: dict = {}
    gs = os.environ.get("HF_FLUX_GUIDANCE")
    st = os.environ.get("HF_FLUX_STEPS")
    if gs is not None and gs.strip():
        try:
            extra["guidance_scale"] = float(gs)
        except ValueError:
            pass
    if st is not None and st.strip():
        try:
            extra["num_inference_steps"] = int(st)
        except ValueError:
            pass

    def _run(**kwargs: object):
        return client.text_to_image(prompt, **kwargs)

    try:
        # Preferred: explicit size + model (newer huggingface_hub)
        image = _run(
            model=model_id,
            width=w,
            height=h,
            **extra,
        )
    except TypeError:
        # Older signatures: prompt + model only
        try:
            image = _run(model=model_id, **extra)
        except TypeError:
            image = _run(model=model_id)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue(), model_id


def _guess_image_mime(image_bytes: bytes) -> str:
    b = image_bytes
    if len(b) >= 3 and b[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(b) >= 8 and b[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(b) >= 12 and b[0:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _call_pollinations(prompt: str, width: int, height: int) -> tuple[bytes, str]:
    from pollinations_api import generate_pollinations_image

    data = generate_pollinations_image(prompt, width=width, height=height)
    model = (os.environ.get("POLLINATIONS_MODEL") or "flux").strip()
    return data, f"pollinations:{model}"


def _call_zsky_api(prompt: str, width: int, height: int) -> tuple[bytes, str]:
    from zsky_api import generate_zsky_png

    data = generate_zsky_png(prompt, width=width, height=height)
    model_label = (os.environ.get("ZSKY_MODEL") or "zsky").strip()
    return data, f"zsky:{model_label}"


def _call_local_flux(prompt: str, width: int, height: int) -> bytes:
    """Colab-style: Diffusers FluxPipeline on this machine (see flux_local.py)."""
    try:
        from flux_local import generate_flux_png
    except ImportError as e:
        raise RuntimeError(
            "Local FLUX dependencies missing. Install with: pip install -r requirements-flux.txt "
            f"(ImportError: {e})"
        ) from e
    return generate_flux_png(prompt, width=width, height=height)


def _generate_image(prompt: str, width: int, height: int) -> tuple[bytes, str]:
    backend = (os.environ.get("AURABOX_FLUX_BACKEND") or "pollinations").strip().lower()
    if backend in ("pollinations", "pollination", "image_pollinations"):
        return _call_pollinations(prompt, width, height)
    if backend in ("zsky", "zsky_ai"):
        return _call_zsky_api(prompt, width, height)
    if backend in ("hf_hub", "inference_client", "hub", "remote_hub"):
        return _call_hf_inference_client(prompt, width, height)
    if backend in ("local", "diffusers", "colab"):
        data = _call_local_flux(prompt, width, height)
        mid = os.environ.get("HF_FLUX_MODEL_ID", "black-forest-labs/FLUX.1-dev")
        return data, mid
    if backend in ("hf", "remote", "api"):
        data = _call_hf_text_to_image(prompt, width=width, height=height)
        return data, _get_remote_model_id()
    raise RuntimeError(
        f"Unknown AURABOX_FLUX_BACKEND={backend!r}. "
        "Use 'pollinations' (default), 'zsky', 'local', 'hf_hub', or 'hf'."
    )


class AuraBoxHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("directory", str(ROOT))
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:
        # Quieter logs
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path != "/api/flux-generate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"

        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"})
            return

        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "Missing prompt"})
            return

        width = int(body.get("width") or 1024)
        height = int(body.get("height") or 1024)

        try:
            image_bytes, model_used = _generate_image(prompt, width, height)
        except Exception as e:
            self._json_response(
                HTTPStatus.BAD_GATEWAY,
                {"error": str(e)},
            )
            return

        b64 = base64.b64encode(image_bytes).decode("ascii")
        backend = (os.environ.get("AURABOX_FLUX_BACKEND") or "pollinations").strip().lower()
        self._json_response(
            HTTPStatus.OK,
            {
                "image_base64": b64,
                "image_mime": _guess_image_mime(image_bytes),
                "model": model_used,
                "backend": backend,
            },
        )

    def _json_response(self, status: HTTPStatus, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path == "/api/flux-generate":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
        else:
            super().do_OPTIONS()


ROOT = Path(__file__).resolve().parent


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    addr = ("", port)
    httpd = ThreadingHTTPServer(addr, AuraBoxHandler)
    print(f"Serving {ROOT} at http://127.0.0.1:{port}/")
    backend = (os.environ.get("AURABOX_FLUX_BACKEND") or "pollinations").strip().lower()
    print(f"Image backend: AURABOX_FLUX_BACKEND={backend}")
    if backend in ("pollinations", "pollination", "image_pollinations"):
        print("  Pollinations (pollinations_api.py): no API key; optional POLLINATIONS_MODEL=flux")
    elif backend in ("zsky", "zsky_ai"):
        print("  ZSky (zsky_api.py): ZSKY_API_KEY + ZSKY_API_URL from your contract (public api.zsky.ai often breaks TLS).")
        if not (os.environ.get("ZSKY_API_KEY") or "").strip():
            print("WARNING: ZSKY_API_KEY is not set — generation will fail for zsky backend.")
    elif backend in ("hf_hub", "inference_client", "hub", "remote_hub"):
        mid, prov = _resolve_provider_and_model_for_hub()
        print(f"  InferenceClient: provider={prov!r}, model={mid!r} (HF_IMAGE_MODEL_ID / HF_FLUX_MODEL_ID)")
    elif backend in ("hf", "remote", "api"):
        print(f"  Raw HF Inference URL: {_inference_url()}")
    else:
        print(
            "  Local Diffusers FluxPipeline — flux_local.py, pip install -r requirements-flux.txt, HF_TOKEN"
        )
    if backend not in ("zsky", "zsky_ai") and not _hf_token():
        print("WARNING: HF_TOKEN not set — needed for Hugging Face backends / local FLUX download.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
