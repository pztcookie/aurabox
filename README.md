# AuraBox

AuraBox is a small web app with three steps: **emotion check-in**, **aura selfie** (webcam + playful face effects), and **Character Lab** — a kawaii, Cookie Run–inspired **rubber hose food creature** generator driven by your emotion, captured aura, and a food vibe.

Image generation runs through a tiny **Python server** so your API keys (if any) stay on your machine and so the browser can call image APIs safely.

---

## Play without running Python (you host the API)

If **you** run `server.py` on a host you control (Railway, Render, Fly.io, your VPS, etc.), visitors can use AuraBox **without** installing Python or typing terminal commands.

1. Deploy **`server.py`** (same `PORT` / `AURABOX_FLUX_BACKEND` / keys as locally). The server already sends **`Access-Control-Allow-Origin: *`** on `POST /api/flux-generate`, so browsers on other sites can call it.
2. Share the **static files** (`index.html`, `play.html`, `page1_user_emotion_layer/`, `page3_character_generation_layer/`, `aura_songs/` if used, etc.) on **HTTPS** — for example **GitHub Pages** or any static host.
3. Point the UI at your API using either:
   - **`play.html`:** edit the line `var AURABOX_REMOTE_API = "https://YOUR-HOST/api/flux-generate";` then tell people to open `play.html` (it redirects to `index.html?api=...`), or
   - **`index.html?api=`** — pass your endpoint URL-encoded, e.g.  
     `index.html?api=https%3A%2F%2Fyour-host%2Fapi%2Fflux-generate`

**Camera / selfie (page 2):** Browsers usually require a **secure context** (HTTPS, or `http://localhost`). Opening files with **`file://`** often **blocks the webcam**, even if Character Lab can still call your API. So for the full three-page flow, **host the HTML on HTTPS**, not only a local double-click.

**Character Lab only:** If users only need generation and skip the camera, `file://` + `?api=` may work in some browsers, but HTTPS hosting is still recommended.

---

## Requirements

- **Python 3.10+** (3.11+ recommended)
- A **modern browser** (Chrome, Firefox, Safari, Edge) with camera permission for the selfie step
- **Network access** for the default image backend (see below)

Optional:

- `pip install requests` — more reliable HTTPS for some backends (`requirements-zsky.txt` / Pollinations helper)

---

## Quick start

1. Open a terminal and go to this folder:

   ```bash
   cd /path/to/aurabox
   ```

2. (Optional) Use a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. (Optional) Install helpers:

   ```bash
   pip install -r requirements-zsky.txt
   ```

4. Start the app server:

   ```bash
   python3 server.py
   ```

5. In your browser, open:

   **`http://127.0.0.1:8000/index.html`**

   You can also open **`http://127.0.0.1:8000/START_HERE.html`** for a short onboarding page with the same link.

6. Stop the server with `Ctrl+C` in the terminal.

> **Local dev:** Without a hosted API, use `python3 server.py` and open `http://127.0.0.1:8000/index.html` so `POST /api/flux-generate` is same-origin.
>
> **Hosted API:** You can open `index.html?api=https://your-server/api/flux-generate` (or use `play.html` after you set `AURABOX_REMOTE_API`). The webcam step still needs **HTTPS** (or localhost) in most browsers — see **Play without running Python** above.

---

## Image generation backends (`AURABOX_FLUX_BACKEND`)

| Value | What it does |
|--------|----------------|
| `pollinations` (default) | Uses [Pollinations](https://pollinations.ai/) image API — no API key. Good for demos and student projects. |
| `zsky` | ZSky AI — requires `ZSKY_API_KEY` and a working `ZSKY_API_URL` from your account. Public `api.zsky.ai` often fails TLS; use only if you have a supported endpoint. |
| `local` | Runs FLUX locally with Diffusers — needs GPU, `requirements-flux.txt`, and `HF_TOKEN`. |
| `hf_hub` | Hugging Face `InferenceClient` — needs `HF_TOKEN`; quotas and model availability vary. |
| `hf` | Legacy raw HTTP to Hugging Face router — mostly for debugging. |

Examples:

```bash
# Default (Pollinations, no key)
python3 server.py

# Optional: choose Pollinations model name (if supported by the service)
export POLLINATIONS_MODEL=flux
python3 server.py
```

---

## Fair use and API limits

Free and shared image APIs apply **rate limits**, **daily caps**, and may change without notice. AuraBox does not control those limits.

- **Pollinations (default):** Shared public service — treat it as **limited**; avoid hammering the service with rapid repeated clicks. Perfect for **demos, coursework, and MVPs**, not high-volume production traffic.
- **Other providers:** Each has its own pricing and quotas; check their official docs.

Please use AuraBox **respectfully**: batch your experiments, cache results you need, and move to a paid or self-hosted backend for production workloads.

---

## Project layout (short)

| File | Role |
|------|------|
| `index.html` | Main AuraBox UI (emotion → selfie → Character Lab) |
| `server.py` | Static file server + `POST /api/flux-generate` proxy |
| `pollinations_api.py` | Default remote image fetch (Pollinations) |
| `zsky_api.py` | Optional ZSky integration |
| `flux_local.py` | Optional local FLUX (Diffusers) |
| `START_HERE.html` | Simple landing page + link to the app + limit notice |
| `play.html` | Optional redirect: set `AURABOX_REMOTE_API` → opens `index.html?api=...` |

---

## Troubleshooting

- **“Failed to fetch” / image errors (local):** Use `http://127.0.0.1:8000/index.html` with `server.py` running, or use `index.html?api=` pointing at your deployed API (HTTPS, CORS enabled).
- **Camera not working:** Use HTTPS or localhost; grant camera permission in the browser.
- **SSL errors with ZSky:** Prefer `pollinations` unless you have a confirmed ZSky URL and key.

---

## License

Use and modify for your own projects. Third-party APIs (Pollinations, Hugging Face, ZSky, etc.) remain subject to their respective terms.
