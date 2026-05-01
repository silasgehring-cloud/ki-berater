# Landing Page — ki-berater.de

Astro 5 + Tailwind 4, statisch deploybar (Cloudflare Pages, Netlify, Vercel,
Hetzner Storage Box).

## Lokal

```bash
cd landing
npm install
npm run dev          # http://localhost:4321
npm run build        # → dist/
npm run preview
```

## Deploy (Cloudflare Pages)

1. Repo nach GitHub pushen.
2. In Cloudflare Pages: "Connect to Git" → repo wählen.
3. Build-Command: `cd landing && npm install && npm run build`
4. Build-Output: `landing/dist`
5. Custom-Domain: `ki-berater.de` (DNS A → Cloudflare).

## Deploy (Hetzner Storage Box + Caddy)

```bash
npm run build
rsync -avz --delete dist/ deploy@server:/srv/landing/
```

Caddy serviert `/srv/landing` auf `ki-berater.de`.

## Was fehlt

- Datenschutz-, AGB-, Impressum-Pages — anwaltlich generieren lassen, dann
  als Astro-Pages unter `/src/pages/{datenschutz,agb,impressum}.astro`.
- Demo-Video oder GIF (Sektion zwischen Features und Pricing).
- Open-Graph-Image (`og.png`) für Social-Share-Previews.
