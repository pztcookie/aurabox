"""
Local FLUX image generation — same approach as the official HF notebook / Colab for FLUX.1-dev:
  FluxPipeline.from_pretrained(...) then pipe(prompt, ...).images[0]

Requires: torch, diffusers (see requirements-flux.txt), a GPU with enough VRAM (or CPU offload — slow).
You must accept the model license on Hugging Face and set HF_TOKEN for gated downloads.

https://huggingface.co/black-forest-labs/FLUX.1-dev
"""

from __future__ import annotations

import io
import os
import threading

import torch
from diffusers import FluxPipeline

_lock = threading.Lock()
_pipe: FluxPipeline | None = None


def _token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")


def _want_cpu() -> bool:
    return os.environ.get("AURABOX_FLUX_FORCE_CPU", "").lower() in ("1", "true", "yes")


def _get_torch_device() -> str:
    if _want_cpu():
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _dtype_for_device(device: str):
    if device == "cuda":
        try:
            if getattr(torch.cuda, "is_bf16_supported", lambda: False)():
                return torch.bfloat16
        except Exception:
            pass
        return torch.float16
    if device == "mps":
        return torch.float16
    return torch.float32


def get_pipeline() -> FluxPipeline:
    global _pipe
    with _lock:
        if _pipe is not None:
            return _pipe

        tok = _token()
        if not tok:
            raise RuntimeError(
                "Local FLUX needs HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) to download gated weights. "
                "Export your token and accept the FLUX.1-dev license on Hugging Face."
            )

        model_id = os.environ.get("HF_FLUX_MODEL_ID", "black-forest-labs/FLUX.1-dev")
        device = _get_torch_device()
        dtype = _dtype_for_device(device)

        print(f"[aurabox] Loading FluxPipeline: {model_id} (device={device}, dtype={dtype}) ...", flush=True)
        _pipe = FluxPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            token=tok,
        )

        # Same idea as the official notebook / Colab: offload unless you have plenty of CUDA VRAM.
        low_vram = os.environ.get("AURABOX_FLUX_LOW_VRAM", "").lower() in ("1", "true", "yes")
        if device == "cuda" and not low_vram:
            _pipe = _pipe.to("cuda")
        elif device == "mps":
            print(
                "[aurabox] MPS: FLUX is large; using CPU offload (slow). For speed, use a CUDA machine or Google Colab.",
                flush=True,
            )
            _pipe.enable_model_cpu_offload()
        else:
            _pipe.enable_model_cpu_offload()

        print("[aurabox] FluxPipeline ready.", flush=True)
        return _pipe


def generate_flux_png(prompt: str, width: int, height: int) -> bytes:
    """
    Run text-to-image and return PNG bytes (Colab-style single forward).
    """
    pipe = get_pipeline()

    guidance = float(os.environ.get("HF_FLUX_GUIDANCE", "3.5"))
    steps = int(os.environ.get("HF_FLUX_STEPS", "28"))
    max_seq = int(os.environ.get("HF_FLUX_MAX_SEQ_LEN", "512"))
    seed_raw = os.environ.get("AURABOX_FLUX_SEED", "")
    seed = int(seed_raw) if seed_raw.strip().lstrip("-").isdigit() else -1

    g = torch.Generator(device="cpu")
    if seed >= 0:
        g.manual_seed(seed)

    kwargs = dict(
        prompt=prompt,
        width=width,
        height=height,
        guidance_scale=guidance,
        num_inference_steps=steps,
        max_sequence_length=max_seq,
        generator=g,
    )

    with _lock:
        out = pipe(**kwargs)

    image = out.images[0]
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
