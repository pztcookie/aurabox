# AuraBox

AuraBox has 3 parts:
- Emotion text
- Selfie aura scanner + music
- Character Lab (FLUX image generation)

Character Lab needs a SKY API key. Without a SKY API key, users can still use Emotion + Selfie + Music (stage 1 and stage 2).

---

## Quick links for users

- Full app (if API is configured):  
  [https://pztcookie.github.io/aurabox/](https://pztcookie.github.io/aurabox/)
- If users do **not** need image generation, they can still use the same link and just stay on page 1 and page 2 (emotion + selfie + music).

---

## If you want Character Lab (FLUX)

You need a backend endpoint that AuraBox can call:
- `POST https://YOUR_HOST/api/flux-generate`
- Request body JSON: `prompt`, `width`, `height`
- Response JSON should include `image_base64` (AuraBox `server.py` already does this)

### SKY API setup

Get SKY API access here:
- [https://www.zsky.ai/](https://www.zsky.ai/)
- [https://www.zsky.ai/api](https://www.zsky.ai/api) (if available for your account/region)

If the API page is not public in your region, use the contact/support form on the main site and request API access.

Use these environment variables on the machine running `server.py`:

```bash
export AURABOX_FLUX_BACKEND=zsky
export ZSKY_API_KEY="YOUR_SKY_API_KEY"
# optional (only set if SKY gives you a custom endpoint)
# export ZSKY_API_URL="YOUR_SKY_API_ENDPOINT"
```

`ZSKY_API_URL` is optional in this project. If you do not set it, AuraBox uses the default endpoint from `zsky_api.py`.

### Point GitHub Pages to your API

Option A (recommended): edit `site-config.js`

```js
window.AURABOX_DEFAULT_REMOTE_API = "https://YOUR_HOST/api/flux-generate";
```

Option B: use query string once:

`https://pztcookie.github.io/aurabox/?api=https%3A%2F%2FYOUR_HOST%2Fapi%2Fflux-generate`

---

## Run locally on your laptop (step-by-step)

1. Open terminal:

```bash
cd /path/to/aurabox
```

2. Quick install without venv (simplest):

```bash
pip install -r requirements.txt
pip install -r requirements-zsky.txt
```

If you prefer venv, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-zsky.txt
```

3. Export SKY API env vars:

```bash
# SKY API
export AURABOX_FLUX_BACKEND=zsky
export ZSKY_API_KEY="YOUR_KEY"
# optional (only if SKY gave you a custom endpoint)
# export ZSKY_API_URL="YOUR_ENDPOINT"
```

4. Start server:

```bash
python3 server.py
```

5. Open in browser:

`http://127.0.0.1:8000/`

(You can also open `http://127.0.0.1:8000/index.html` directly.)

Stop server with `Ctrl+C`.

---

## No SKY API key? (stage 1 + stage 2 only)

If a user just clones/pulls this repo and runs it without setting `ZSKY_API_KEY`:
- Stage 1 (emotion text) works
- Stage 2 (selfie aura + music) works
- Character Lab generation is locked with an on-screen message

To unlock Character Lab, the user must:
1. Get a SKY API key from [https://www.zsky.ai/](https://www.zsky.ai/) (or [https://www.zsky.ai/api](https://www.zsky.ai/api))
2. Export `ZSKY_API_KEY`
3. Run `python3 server.py` again

---

## Common errors

- `Failed to fetch`:
  - API URL is wrong or unreachable
  - API is `http://` while page is `https://` (mixed content blocked)
  - CORS / TLS issue on API host
- `405 Method Not Allowed`:
  - You passed the wrong URL in `api=...`
  - Must be your backend endpoint, not a token/id and not GitHub Pages URL

---

## Notes

- Camera access works best on `https://` or `http://localhost`.
- Free/shared image APIs have rate limits and daily limits.
