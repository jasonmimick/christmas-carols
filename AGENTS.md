# Christmas Carols

Songbook site for the three-church Christmas carol sing-alongs. Static HTML,
hosted on Cloudflare Pages (project `christmas-carols`,
https://christmas-carols-cjm.pages.dev).

## Layout
- `build.py` — generates all HTML. **Home page copy lives here**, in `build_sheet()`.
- `songs-abc/*.abc` — sheet-music songs → `songbook.html` (the site).
- `songs/*.cho` — ChordPro text songs → `songbook-text.html`.
- `appendix/*.txt` — plain-text extras shown under "Appendix" in the set list. First line is
  the title, the rest is shown as preformatted text. Not part of the 13 curated carols.
- `_redirects` — maps `/` to `/songbook.html`.
- `dist/` — deploy folder, gitignored.

## Commands
```
python3 build.py
cp songbook.html chords.html _redirects dist/
npx wrangler pages deploy dist --project-name christmas-carols --branch main
```

## Gotchas
- A song is "curated" when its `.abc` has a `%curated: <source>` line under the header. That
  shows a green check in the set list and on the song, and counts toward the home-page total.
  Only add it after the song's notes, lyrics and chords were checked against that source.
- `songbook.html` is generated. Edit `build.py` (or the song files), never the
  HTML by hand, or the next build wipes the change.
- Deploys are direct upload with Wrangler. Pushing to GitHub does not deploy.
  To preview without touching the live site, deploy with `--branch mobile-preview`
  (or any other branch name) and open `https://<branch>.christmas-carols-cjm.pages.dev`.
- Sheet music (abcjs) renders at a fixed 760px staff on desktop and print. Below
  that, `renderTunes()` wraps bars at a 480px staff and scales it to fit. Wider
  than 480 at phone size and the lyrics get too small; narrower and you get one bar per line.
- **Printed music is the P0 requirement; phone layout is not a priority.** Judge layout by the wide
  (desktop/print) render. `m2render.py` engraves with `%%barsperstaff` and picks bars per line so the last
  line is never a lone bar. For songs with short bars (slow 3/4, 2/4) set `%bars-wide: N` under the header
  in the `.abc` (Silent Night 8, Joy to the World 5). Keep lines on phrase boundaries where you can.
