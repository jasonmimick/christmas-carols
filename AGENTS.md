# Christmas Carols

Songbook site for the three-church Christmas carol sing-alongs. Static HTML,
hosted on Cloudflare Pages (project `christmas-carols`,
https://christmas-carols-cjm.pages.dev).

## Layout
- `build.py` — generates all HTML. **Home page copy lives here**, in `build_sheet()`.
- `songs-abc/*.abc` — sheet-music songs → `songbook.html` (the site).
- `songs/*.cho` — ChordPro text songs → `songbook-text.html`, `songbook-capo.html`.
- `_redirects` — maps `/` to `/songbook.html`.
- `dist/` — deploy folder, gitignored.

## Commands
```
python3 build.py
cp songbook.html _redirects dist/
npx wrangler pages deploy dist --project-name christmas-carols --branch main
```

## Gotchas
- `songbook.html` is generated. Edit `build.py` (or the song files), never the
  HTML by hand, or the next build wipes the change.
- Deploys are direct upload with Wrangler. Pushing to GitHub does not deploy.
  To preview without touching the live site, deploy with `--branch mobile-preview`
  (or any other branch name) and open `https://<branch>.christmas-carols-cjm.pages.dev`.
- Sheet music (abcjs) renders at a fixed 760px staff on desktop and print. Below
  that, `renderTunes()` wraps bars at a 480px staff and scales it to fit. Wider
  than 480 at phone size and the lyrics get too small; narrower and you get one bar per line.
