# AuraBox

AuraBox is a small web app with three steps: **emotion check-in**, **aura selfie** (webcam + playful face effects), and **Character Lab** — a kawaii, Cookie Run–inspired **rubber hose food creature** generator driven by your emotion, captured aura, and a food vibe.

Image generation runs through a tiny **Python server** so your API keys (if any) stay on your machine and so the browser can call image APIs safely.

---

## Play without running Python (you host the API)

If **you** run `server.py` on a host you control (Railway, Render, Fly.io, your VPS, etc.), visitors can use AuraBox **without** installing Python or typing terminal commands.

1. Deploy **`server.py`** (same `PORT` / `AURABOX_FLUX_BACKEND` / keys as locally). The server already sends **`Access-Control-Allow-Origin: *`** on `POST /api/flux-generate`, so browsers on other sites can call it.
2. Share the **static files** (`index.html`, `play.html`, `page1_user_emotion_layer/`, `page3_character_generation_layer/`, `aura_songs/` if used, etc.) on **HTTPS** — for example **GitHub Pages** or any static host.
3. Point the UI at your API (pick one):
   - **`site-config.js` (recommended):** set `window.AURABOX_DEFAULT_REMOTE_API = "https://YOUR-HOST/api/flux-generate"` and push to GitHub. Then players can use the short link below with **no** query string.
   - **`play.html`:** opens `index.html?api=...` using the same `site-config.js` value (or shows help if empty).
   - **`index.html?api=`** — one-off testing, URL-encoded, e.g.  
     `index.html?api=https%3A%2F%2Fyour-host%2Fapi%2Fflux-generate`

### Public link (GitHub Pages)

After the API is deployed and `site-config.js` contains your **`https://.../api/flux-generate`** URL, share:

**[https://pztcookie.github.io/aurabox/](https://pztcookie.github.io/aurabox/)**

(Replace `pztcookie` with your GitHub username if the repo lives under a different account.)

---

### Deploy the API on Railway (you run this once)

A hosted assistant **cannot** log into your Railway account for you. These steps take a few minutes:

1. Sign in at [railway.app](https://railway.app/) and click **New project** → **Deploy from GitHub repo** → select **`aurabox`** (or push this repo first so it appears).
2. Railway should detect **Python** and use the **`Procfile`** (`web: python3 server.py`). The server reads **`PORT`** from the environment (Railway sets this automatically).
3. Open your service → **Settings** → **Networking** → **Generate domain** (public HTTPS URL), e.g. `https://aurabox-production-xxxx.up.railway.app`.
4. Confirm the API responds: `POST https://YOUR-URL/api/flux-generate` with JSON `{"prompt":"a red apple","width":512,"height":512}` (or open the root URL in a browser — you should get static files from the same `server.py`).
5. In this repo, edit **`site-config.js`** and set:
   ```js
   window.AURABOX_DEFAULT_REMOTE_API = "https://YOUR-URL/api/flux-generate";
   ```
   Commit and push to GitHub. Wait for GitHub Pages to rebuild (~1 minute).
6. Open the **Public link** above — Character Lab should generate images without `?api=` in the URL.

Default image backend is **Pollinations** (no API key). Optional env vars on Railway match `server.py` (e.g. `AURABOX_FLUX_BACKEND`, `POLLINATIONS_MODEL`).

---

### Deploy the API on your own server (no Railway)

If you do not want Railway, run `server.py` on any Linux VPS (DigitalOcean, Hetzner, Linode, AWS EC2, etc.) and expose it over HTTPS.

1. SSH into your server and install Python 3.10+.
2. Clone this repo and enter the folder:
   ```bash
   git clone https://github.com/pztcookie/aurabox.git
   cd aurabox
   ```
3. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Start the API:
   ```bash
   PORT=8000 python3 server.py
   ```
5. Test from your local machine:
   ```bash
   curl -i -X POST "http://YOUR_SERVER_IP:8000/api/flux-generate" \
     -H "Content-Type: application/json" \
     -d '{"prompt":"cute mochi monster","width":512,"height":512}'
   ```
   You should get JSON with `image_base64`.
6. Put Nginx/Caddy in front with HTTPS, then use:
   `https://YOUR_DOMAIN/api/flux-generate`
7. Set this in `site-config.js`:
   ```js
   window.AURABOX_DEFAULT_REMOTE_API = "https://YOUR_DOMAIN/api/flux-generate";
   ```
8. Commit + push, then users can open your GitHub Pages link normally.

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
| `play.html` | Redirect using `site-config.js` / `?api=` → `index.html?api=...` |
| `site-config.js` | Default remote API URL for GitHub Pages (paste Railway URL here) |
| `Procfile` / `requirements.txt` | Railway / PaaS: run `python3 server.py` |

---

## Troubleshooting

- **Failed to fetch:** This is a browser-level network error (request never got a valid response). Most common causes:
  - API URL is unreachable from the browser (server down, bad domain, DNS, timeout).
  - Mixed content (`https://pztcookie.github.io/...` trying to call `http://...` API). Use HTTPS API URL.
  - CORS/preflight blocked (API does not allow `OPTIONS` + `POST` from browser).
  - TLS/certificate issue on the API host.
  Quick check with curl:
  ```bash
  curl -i -X OPTIONS "https://YOUR_API_HOST/api/flux-generate" \
    -H "Origin: https://pztcookie.github.io" \
    -H "Access-Control-Request-Method: POST"
  ```
  Then:
  ```bash
  curl -i -X POST "https://YOUR_API_HOST/api/flux-generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"test","width":512,"height":512}'
  ```
- **405 Method Not Allowed:** The browser sent **POST** to a URL that does not accept it — almost always the **wrong link**. Use your deployed **`server.py`** URL including the path **`/api/flux-generate`** (e.g. `https://xxx.up.railway.app/api/flux-generate`). Do **not** use your **GitHub Pages** URL (`…github.io/aurabox/…`) as `?api=` — Pages is static-only and often returns **405** for POST. If you only pasted the deploy **root** (no path), the app now appends `/api/flux-generate` when the path is empty.
- **502 / 404 on Character Lab (GitHub Pages):** Pages only serves static files — there is **no** `server.py` and no `/api/flux-generate` on `github.io`. The browser was calling the wrong URL, which often returns **502** or **404**. Deploy `server.py` to Railway, Render, Fly.io, etc., then share AuraBox as:  
  `https://YOUR_USER.github.io/aurabox/index.html?api=https%3A%2F%2FYOUR_API_HOST%2Fapi%2Fflux-generate`  
  (replace with your real HTTPS API URL). The app shows a red help box on Character Lab when this is missing.
- **“Failed to fetch” / image errors (local):** Use `http://127.0.0.1:8000/index.html` with `server.py` running, or use `index.html?api=` pointing at your deployed API (HTTPS, CORS enabled).
- **Camera not working:** Use HTTPS or localhost; grant camera permission in the browser.
- **SSL errors with ZSky:** Prefer `pollinations` unless you have a confirmed ZSky URL and key.

---

## License

Use and modify for your own projects. Third-party APIs (Pollinations, Hugging Face, ZSky, etc.) remain subject to their respective terms.
