# Open Swarm bee mark

Project-owned brand mark derived from the README hero
(`assets/images/openswarm-project-image.jpg` — honeybee over hand-lettered
OPEN SWARM). That JPG stays the hero; this folder is the **simplified mark**
for favicon, PWA, and later installable / desktop / Pinokio icons.

No third-party stock bee. No illustrator credit is recorded on the JPG.

## Masters

| File | Use |
|---|---|
| `bee-mark.svg` | Colour (honey `#F4C400` / black `#1A140C`). Silhouette-first; no wing veins. |
| `bee-mark-mono.svg` | Single colour via `currentColor` (defaults to black). Light UI, masks. |
| `bee-mark-mono-on-dark.svg` | Opaque white. Dark chrome / DaisyUI rail `#111111`. |

Regenerate rasters (optional tools, not runtime deps):

```bash
uv run --with pillow --with cairosvg python scripts/export_brand_icons.py
```

That also copies the serving set into `webui/frontend/public/` and replaces
`assets/images/favicon.ico` with the colour multi-size ICO.

## Raster set (checked in)

**Colour (wired in the tab / Apple / PWA):**

| File | Size | Notes |
|---|---|---|
| `favicon.ico` | 16 / 32 / 48 | Colour, transparent. Root `/favicon.ico`. |
| `favicon-16.png` | 16 | Colour, transparent. |
| `favicon-32.png` | 32 | Colour, transparent. |
| `favicon-48.png` | 48 | Colour, transparent; baked into the ICO. |
| `apple-touch-icon.png` | 180 | Colour on cream `#FFF8EC` (iOS fills transparency with black). |
| `apple-touch-icon-120.png` | 120 | Colour on cream. Not linked in HTML; easy extra. |
| `apple-touch-icon-152.png` | 152 | Colour on cream. Not linked in HTML; easy extra. |
| `icon-192.png` | 192 | Colour on cream. PWA `any`. |
| `icon-512.png` | 512 | Colour on cream. PWA `any`. |

**Mono (not every size is wired in `<head>`):**

| File | Size | Notes |
|---|---|---|
| `bee-mark-mono-16.png` / `32` / `192` / `512` | those sizes | Black silhouette, transparent. Masks / light UI. |
| `bee-mark-mono-on-dark-16.png` / `32` / `192` / `512` | those sizes | White bee on `#111111`. Dark rail / dark chrome. |

Tab favicon, `apple-touch-icon`, and the web manifest use **colour only**.
Mono rasters are the kit for dark-UI embeds and a future native shell.

## Wiring

- SPA `webui/frontend/index.html` → `/favicon.ico`, `/favicon-16.png`,
  `/favicon-32.png`, `/apple-touch-icon.png`, `/manifest.json`
- Django `base.html` + login → `{% static 'brand/…' %}` (`STATICFILES_DIRS`
  prefix `brand` → this directory)
- Django also serves the same files at the root URLs above so the SPA and
  default browser `/favicon.ico` requests are not the SPA `index.html`
- Pinokio launcher `icon` points at `bee-mark.svg` (asset kit; no native
  app shell in this change)
