# AuraBox

AuraBox has 3 stages:
- Stage 1: Emotion text
- Stage 2: Selfie aura scanner + music
- Stage 3: Character Lab (image generation)

This repo is configured to work with the Pollinations backend for Character Lab image generation.
You do not need any ZSKY API key to run Stage 3 with the current scripts (`server.py` + `pollinations_api.py`).

---

## After Git Pull: quick start

```bash
cd /path/to/aurabox
pip install -r requirements.txt
export AURABOX_FLUX_BACKEND=pollinations
python3 server.py
```

Open:

`http://127.0.0.1:8000/`

---

## Recommended free setup: Pollinations (no SKY key)

Use this for all users (no API key needed):

```bash
export AURABOX_FLUX_BACKEND=pollinations
python3 server.py
```

Then open:

`http://127.0.0.1:8000/`

Now Stage 1, Stage 2, and Stage 3 should all work (subject to Pollinations rate limits).

---

## Backend used by this repo

- `server.py` exposes `POST /api/flux-generate`
- `pollinations_api.py` calls Pollinations image API
- Default intended free setup: `AURABOX_FLUX_BACKEND=pollinations`
- No ZSKY key is required for this flow

---

## Shareable website link

Public site:

[https://pztcookie.github.io/aurabox/](https://pztcookie.github.io/aurabox/)

Users can always play Stage 1 and Stage 2 from this link.  
For Stage 3, the app must reach a running backend endpoint.

### Free temporary public link (Cloudflare Tunnel)

If you want others to use Stage 3 without deploying a paid server:

1. Run backend locally:
   ```bash
   cd /path/to/aurabox
   export AURABOX_FLUX_BACKEND=pollinations
   python3 server.py
   ```
2. In another terminal:
   ```bash
   cloudflared tunnel --url http://127.0.0.1:8000
   ```
3. Copy the `https://...trycloudflare.com` URL and share:
   `https://pztcookie.github.io/aurabox/?api=https%3A%2F%2FYOUR_TUNNEL_HOST%2Fapi%2Fflux-generate`

Keep both terminals running; the link stops when either process stops.

---

## Notes

- Camera works best on `https://` or `http://localhost`.
- Pollinations is a shared free service and may have daily/rate limits.
