# Christmas Carols

Songbook site for the three-church Christmas carol sing-alongs. Static HTML,
hosted on Cloudflare Pages (project `christmas-carols`,
https://christmas-carols-cjm.pages.dev).

## Layout
- `build.py` — generates all HTML. **Home page copy lives here**, in `build_sheet()`.
- `songs-abc/*.abc` — sheet-music songs → `songbook.html` (the site).
- `songs/*.cho` — ChordPro text songs → `songbook-text.html`.
- `appendix/*.txt` — chord charts shown under "Appendix A: Additional Songs" on the site and in the booklet.
  Format is in `chart.py`: title, notes, then sections; `[Chord]word` lines render chords over the
  words (same layout as the chords page), indented lines stay fixed-width (bar grids, diagrams),
  `---` starts a new printed page. These songs are under copyright. Claude does not type their lyrics from
  memory; the words come from sheets Jason supplies (PDFs in ~/Downloads), and Jason chose to publish
  them on the site and repo.
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

## Print booklet
- `python3 booklet.py` → `booklet/booklet-letter.pdf` (gitignored): all 13 carols, sheet music with
  chords, for the musicians' booklets (5 copies). Letter at scale 0.9 won over 7x10 / 6x9 / half letter
  (`python3 booklet.py all` rebuilds those for comparison; half letter forces 2 bars per line).
- Engraved straight to PostScript by abcm2ps (`-1`, one song per page), not from the site SVGs.
  Chords are Times-Bold to match the Times lyrics (Jason's pick over the site's Helvetica-Bold).
- Two-page songs must start on a left (even) page; `build()` inserts a blank page if not.
  Side margins are equal so double-sided printing works with the spiral.
- A song slightly over one page is shrunk per song (down to `MIN_FIT`) so it stays on one page;
  Jingle Bells and We Three Kings need this. O Holy Night stays two pages (a left/right spread).
- Cover (page 1) is `cover.html` (title, the three churches on a line map, tree/candle/wreath icons),
  printed to PDF by headless Chrome in `cover_pdf()`; needs the network for the IM Fell English font.
- Booklet order: cover, contents (generated with page numbers), the 13 carols from page 3
  (abcm2ps numbers them; two placeholder pages are engraved first and swapped for the front matter),
  then an "Appendix A: Additional Songs" divider page and the charts. No blank pages.
- The appendix charts are drawn as PostScript by `chart_page()` (Times-Bold chords over Times words)
  at one fixed size for every chart (`LYRIC_PT` etc.), top-aligned, notes as footnotes. A long chart
  goes to two columns, and only then shrinks (to `MIN_PT`). Don't scale charts to fill the page:
  Jason rejected that as unprofessional (different, oversized type on every page). `dist/songbook.pdf` is a copy of `booklet/booklet-letter.pdf`;
  copy it before each deploy. One booklet only — Jason doesn't want a second print version.
- Jingle Bells has verse 2 under the music (with verse 1) and verses 3–4 as text below, so it fits one page.
