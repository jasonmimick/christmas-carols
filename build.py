#!/usr/bin/env python3
"""Render songs-abc/*.abc into songbook.html and songs/*.cho into songbook-text.html.

Song files use ChordPro-style inline chords: [G]Silent night, [D7]holy night.
Directives: {title: ..} {key: ..} {time: ..} {note: ..} {label: ..}
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent

CSS = """
body { font-family: Georgia, serif; font-size: 13pt; margin: 0.6in; color: #000; }
h1 { font-size: 22pt; margin: 0 0 0.2em; }
h2 { font-size: 18pt; margin: 0; }
.meta { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; margin: 0.2em 0 1em; }
.note { font-style: italic; font-size: 10.5pt; margin: 0 0 1em; }
.song { page-break-before: always; }
.stanza { margin: 0 0 1em; break-inside: avoid; }
.label { font-style: italic; font-weight: bold; margin-bottom: 0.2em; }
.line { line-height: 1.25; }
.seg { display: inline-block; vertical-align: bottom; white-space: pre; }
.chord { display: block; min-height: 1.2em; padding-right: 0.4em;
         font-family: Helvetica, Arial, sans-serif; font-weight: bold; font-size: 11.5pt; }
.lyric { display: block; min-height: 1.2em; }
table { border-collapse: collapse; font-family: Helvetica, Arial, sans-serif; font-size: 11pt; }
th, td { border-bottom: 1px solid #999; padding: 0.3em 0.9em 0.3em 0; text-align: left; }
.printbar { font-family: Helvetica, Arial, sans-serif; margin: 1em 0; }
.printbar button { font-size: 11pt; padding: 0.4em 1.2em; }
@media print { .printbar { display: none; } }
@page { margin: 0.6in; }
"""

def parse(path):
    song = {"title": path.stem, "key": "C", "time": "", "note": "", "stanzas": [[]]}
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        m = re.fullmatch(r"\{(\w+):\s*(.*)\}", line)
        if m and m.group(1) == "label":
            song["stanzas"][-1].append(("label", m.group(2)))
        elif m:
            song[m.group(1)] = m.group(2)
        elif not line:
            song["stanzas"].append([])
        else:
            song["stanzas"][-1].append(("lyric", line))
    song["stanzas"] = [s for s in song["stanzas"] if s]
    return song


def render_line(line):
    parts = re.split(r"\[([^\]]+)\]", line)
    has_chords = len(parts) > 1
    segs = [("", parts[0])] if parts[0] else []
    for chord, text in zip(parts[1::2], parts[2::2]):
        segs.append((chord, text))
    out = []
    for chord, text in segs:
        c = f'<span class="chord">{html.escape(chord)}</span>' if has_chords else ""
        out.append(f'<span class="seg">{c}<span class="lyric">{html.escape(text)}</span></span>')
    return f'<div class="line">{"".join(out)}</div>'


def render_song(number, song):
    meta = " · ".join(x for x in (f'Key of {song["key"]}', song["time"]) if x)
    out = [f'<section class="song"><h2>{number}. {html.escape(song["title"])}</h2>',
           f'<div class="meta">{html.escape(meta)}</div>']
    if song["note"]:
        out.append(f'<div class="note">{html.escape(song["note"])}</div>')
    for stanza in song["stanzas"]:
        out.append('<div class="stanza">')
        for kind, text in stanza:
            if kind == "label":
                out.append(f'<div class="label">{html.escape(text)}</div>')
            else:
                out.append(render_line(text))
        out.append("</div>")
    out.append("</section>")
    return "\n".join(out)


def build(songs):
    title = "Christmas Carols: Guitar Chords"
    rows = []
    for n, song in enumerate(songs, 1):
        rows.append(f"<tr><td>{n}</td><td>{html.escape(song['title'])}</td>"
                    f"<td>Key of {html.escape(song['key'])}</td><td>{html.escape(song['time'])}</td></tr>")
    body = "\n".join(render_song(n, s) for n, s in enumerate(songs, 1))
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{CSS}</style></head><body><h1>{title}</h1>"
            f'<div class="printbar"><button onclick="window.print()">Print / Save as PDF</button></div>'
            f"<table><tr><th>#</th><th>Carol</th><th>Key</th><th>Time</th></tr>"
            f"{''.join(rows)}</table>\n{body}</body></html>")


SHEET_HEAD = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Christmas Carols Songbook</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&display=swap">
<style>
  body { background: #fff; color: #000; margin: 0; font-family: Helvetica, Arial, sans-serif; }
  nav { position: fixed; top: 0; left: 0; bottom: 0; width: 250px; overflow-y: auto;
        border-right: 1px solid #ddd; padding: 1rem 0; box-sizing: border-box; }
  nav .navtitle { font-family: "IM Fell English", Georgia, serif; font-size: 1.3rem;
                  padding: 0.3rem 1rem 0.8rem; }
  nav ul { list-style: none; margin: 0; padding: 0; }
  nav .label { font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
               color: #777; padding: 0 1rem 0.4rem; }
  nav hr { border: none; border-top: 1px solid #ddd; margin: 0.9rem 1rem 0.9rem 0; }
  nav li { display: flex; align-items: center; font-size: 0.9rem; cursor: pointer;
           border-radius: 0 16px 16px 0; margin-right: 8px; }
  nav li .name { flex: 1; padding: 0.45rem 0.4rem 0.45rem 1rem; }
  nav li:hover { background: #f1f1f1; }
  nav li.active { background: #e9e9e9; font-weight: bold; }
  nav li .pr { visibility: hidden; padding: 0.45rem 0.7rem; color: #555; font-size: 0.8rem; }
  nav li:hover .pr { visibility: visible; }
  nav li .pr:hover { color: #000; text-decoration: underline; }
  nav .all { display: block; margin: 1rem 1rem 0; padding-top: 1rem; border-top: 1px solid #ddd;
             font-size: 0.9rem; color: #000; cursor: pointer; text-decoration: underline; }
  main { margin-left: 250px; padding: 2rem 20px 3rem; }
  .sheet { max-width: 820px; margin: 0 auto; }
  section.page { display: none; }
  section.page.current { display: block; }
  #home { max-width: 620px; }
  #home .hometitle { font-family: "IM Fell English", Georgia, serif; font-weight: 400;
                     font-size: 2.4rem; margin: 0 0 1rem; }
  #home .ornaments { display: flex; flex-wrap: wrap; align-items: center; gap: 1.4rem;
                     margin: 0 0 1.4rem; }
  #home .ornaments svg { height: 64px; width: auto; }
  #home h2 { font-size: 1.15rem; margin: 2rem 0 0.5rem; }
  #home p { line-height: 1.55; margin: 0 0 1em; }
  #home ul { margin: 0 0 1em; padding-left: 1.4rem; }
  #home li { padding: 0.15rem 0; }
  h2.songtitle { font-family: "IM Fell English", Georgia, serif; font-weight: 400;
                 font-size: 2rem; text-align: center; margin: 0 0 0.1em; }
  .composer { font-family: "IM Fell English", Georgia, serif; font-style: italic;
              text-align: center; margin: 0 0 0.8em; font-size: 1rem; }
  .verses { font-family: Georgia, serif; font-size: 1rem; margin: 1em auto 0;
            max-width: 34em; line-height: 1.5; }
  #booktitle { display: none; }
  nav .toggle { display: none; }
  @media (max-width: 700px) {
    nav { position: static; width: auto; border-right: none; border-bottom: 1px solid #ddd;
          padding: 0.6rem 0; }
    nav .navtitle { display: flex; justify-content: space-between; align-items: center;
                    padding: 0.2rem 1rem; cursor: pointer; }
    nav .toggle { display: inline; font-family: Helvetica, Arial, sans-serif; font-size: 0.9rem; }
    nav:not(.open) ul, nav:not(.open) hr, nav:not(.open) .label, nav:not(.open) .all { display: none; }
    nav.open .navtitle { padding-bottom: 0.8rem; }
    nav li .pr { visibility: visible; }
    main { margin-left: 0; padding: 1.2rem 12px 2rem; }
    #home .hometitle { font-size: 2rem; }
    #home .ornaments { gap: 1rem; }
    #home .ornaments svg { height: 48px; }
    h2.songtitle { font-size: 1.6rem; }
  }
  @media print {
    nav { display: none; }
    main { margin-left: 0; padding: 0; }
    body.print-all #booktitle { display: block; font-family: "IM Fell English", Georgia, serif;
      font-weight: 400; font-size: 2.6rem; text-align: center; padding-top: 3in;
      page-break-after: always; }
    body.print-all section.song { display: block; page-break-after: always; }
    body.print-all #home { display: none; }
  }
  @page { margin: 0.6in; }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/abcjs/6.4.4/abcjs-basic-min.js"></script>
</head><body>
"""


def parse_abc(path):
    """Split an .abc file into (title, composer, abc-for-render, extra verse lines)."""
    title, composer, abc, extra = "", "", [], []
    for line in path.read_text().splitlines():
        if line.startswith("T:"):
            title = line[2:].strip()
        elif line.startswith("C:"):
            composer = line[2:].strip()
        elif line.startswith("W:"):
            extra.append(line[2:].strip())
        else:
            abc.append(line)
    return title, composer, "\n".join(abc), extra


def build_sheet(paths):
    out = [SHEET_HEAD]
    tunes, nav = [], []
    sections = []
    for n, path in enumerate(paths):
        title, composer, abc, extra = parse_abc(path)
        slug = path.stem
        nav.append(f'<li id="nav{n}" data-n="{n}"><span class="name">{html.escape(title)}</span>'
                   f'<span class="pr" title="Print this song">print</span></li>')
        sec = [f'<section class="page song" id="song{n}" data-slug="{html.escape(slug)}">',
               f'<h2 class="songtitle">{html.escape(title)}</h2>',
               f'<div class="composer">{html.escape(composer)}</div>',
               f'<div id="paper{n}"></div>']
        if extra:
            verses = "<br>\n".join(html.escape(v) for v in extra)
            sec.append(f'<div class="verses">{verses}</div>')
        sec.append("</section>")
        sections.append("\n".join(sec))
        tunes.append(abc)
    out.append('<nav><div class="navtitle">Christmas Carols<span class="toggle">Songs &#9662;</span></div><ul>'
               '<li id="navhome"><span class="name">Home</span></li></ul>'
               '<hr><div class="label">Set list</div><ul>')
    out.extend(nav)
    out.append('</ul><span class="all" id="printall">Print entire songbook</span></nav>')
    out.append("""<main><div class="sheet"><h1 id="booktitle">Christmas Carols</h1>
<section class="page" id="home" data-slug="home">
  <h1 class="hometitle">Christmas Carols</h1>
  <div class="ornaments" aria-hidden="true">
<svg viewBox="0 0 120 90" stroke="#1d1d1b" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">
  <path fill="none" stroke="#5a4127" d="M6,62 C28,40 44,72 64,48 S100,28 114,38"/>
  <g fill="#3f7a3a">
    <path transform="translate(24,40) rotate(-20)" d="M0,-15 Q3,-8 6,-7 Q12,-11 14,-7 Q11,-1 12,2 Q16,6 13,9 Q6,8 4,9 Q2,14 0,15 Q-2,14 -4,9 Q-6,8 -13,9 Q-16,6 -12,2 Q-11,-1 -14,-7 Q-12,-11 -6,-7 Q-3,-8 0,-15 Z"/>
    <path transform="translate(56,72) rotate(160) scale(.9)" d="M0,-15 Q3,-8 6,-7 Q12,-11 14,-7 Q11,-1 12,2 Q16,6 13,9 Q6,8 4,9 Q2,14 0,15 Q-2,14 -4,9 Q-6,8 -13,9 Q-16,6 -12,2 Q-11,-1 -14,-7 Q-12,-11 -6,-7 Q-3,-8 0,-15 Z"/>
    <path transform="translate(84,24) rotate(15)" d="M0,-15 Q3,-8 6,-7 Q12,-11 14,-7 Q11,-1 12,2 Q16,6 13,9 Q6,8 4,9 Q2,14 0,15 Q-2,14 -4,9 Q-6,8 -13,9 Q-16,6 -12,2 Q-11,-1 -14,-7 Q-12,-11 -6,-7 Q-3,-8 0,-15 Z"/>
    <path transform="translate(108,58) rotate(170) scale(.75)" d="M0,-15 Q3,-8 6,-7 Q12,-11 14,-7 Q11,-1 12,2 Q16,6 13,9 Q6,8 4,9 Q2,14 0,15 Q-2,14 -4,9 Q-6,8 -13,9 Q-16,6 -12,2 Q-11,-1 -14,-7 Q-12,-11 -6,-7 Q-3,-8 0,-15 Z"/>
  </g>
</svg>
<svg viewBox="0 0 80 92" stroke="#1d1d1b" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">
  <path fill="#f4b93a" d="M40,4 C48,14 47,24 40,28 C33,24 32,14 40,4 Z"/>
  <path fill="#fff3c4" stroke-width="1.5" d="M40,13 C44,18 43,23 40,25 C37,23 36,18 40,13 Z"/>
  <path fill="none" d="M40,28 V33"/>
  <rect x="31" y="33" width="18" height="44" rx="2" fill="#f6ecd6"/>
  <path fill="#f6ecd6" stroke-width="2" d="M35,33 V42 Q37,45 39,42 V35"/>
  <path fill="#b88a3a" d="M18,78 H62 Q60,86 40,86 Q20,86 18,78 Z"/>
  <path fill="none" d="M62,80 Q74,80 72,72"/>
  <path fill="#2f6b34" stroke-width="2.5" d="M22,77 L16,72 L18,68 L12,66 L20,62 L26,70 Z"/>
  <path fill="#2f6b34" stroke-width="2.5" d="M58,77 L64,72 L62,68 L68,66 L60,62 L54,70 Z"/>
  <circle cx="30" cy="77" r="4" fill="#c8312a" stroke-width="2"/>
  <circle cx="50" cy="77" r="4" fill="#c8312a" stroke-width="2"/>
</svg>
<svg viewBox="0 10 120 80" stroke="#1d1d1b" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">
  <g transform="rotate(8 60 46)">
    <path fill="#2f6b34" d="M60,44 L52,34 L46,40 L38,29 L32,38 L22,31 L20,42 L6,44 L18,52 L15,63 L28,56 L32,67 L40,56 L48,62 L52,52 Z"/>
    <path fill="none" stroke-width="2" d="M57,46 Q35,45 12,45"/>
  </g>
  <g transform="translate(120,0) scale(-1,1) rotate(30 60 46)">
    <path fill="#2f6b34" d="M60,44 L52,34 L46,40 L38,29 L32,38 L22,31 L20,42 L6,44 L18,52 L15,63 L28,56 L32,67 L40,56 L48,62 L52,52 Z"/>
    <path fill="none" stroke-width="2" d="M57,46 Q35,45 12,45"/>
  </g>
  <circle cx="55" cy="50" r="8" fill="#c8312a"/>
  <circle cx="67" cy="48" r="8" fill="#c8312a"/>
  <circle cx="61" cy="60" r="8" fill="#c8312a"/>
  <g stroke="none" fill="#fff" opacity=".8">
    <ellipse cx="52" cy="47" rx="2.2" ry="1.4"/><ellipse cx="64" cy="45" rx="2.2" ry="1.4"/><ellipse cx="58" cy="57" rx="2.2" ry="1.4"/>
  </g>
</svg>
<svg viewBox="0 0 80 84" stroke="#1d1d1b" stroke-width="3" stroke-linejoin="round">
  <path stroke="#d9a520" stroke-width="2" stroke-linecap="round" d="M40,18 V4 M40,66 V80 M16,42 H2 M64,42 H78"/>
  <polygon fill="#f2c230" points="40.0,6.0 44.6,30.9 54.8,27.2 51.1,37.4 76.0,42.0 51.1,46.6 54.8,56.8 44.6,53.1 40.0,78.0 35.4,53.1 25.2,56.8 28.9,46.6 4.0,42.0 28.9,37.4 25.2,27.2 35.4,30.9"/>
  <circle cx="40" cy="42" r="5" fill="#fff6d0" stroke-width="2"/>
  <g fill="#f2c230" stroke-width="1.5">
    <circle cx="14" cy="14" r="2.5"/><circle cx="68" cy="70" r="2.5"/><circle cx="70" cy="16" r="2"/>
  </g>
</svg>
  </div>
  <p>This Christmas season we are getting together to sing carols at each of our
     three churches.</p>
  <h2>Where &amp; when</h2>
  <p>Practice: October &mdash; time &amp; date TBD</p>
  <ul>
    <li>St. Paul's &mdash; Sunday, December 6, 6 pm</li>
    <li>St. Joseph's Church &mdash; Sunday, December 13, 6 pm</li>
    <li>Holy Mother &amp; Child Parish &mdash; Sunday, December 20, 6 pm</li>
  </ul>
  <h2>The songbook</h2>
  <p>The set list on the left has all thirteen carols &mdash; click one to see its
     sheet music with lyrics and guitar chords. You can print any single song, or
     print the entire songbook and bring it with you.</p>
  <p>We're still checking the music. Here are the
     <a href="https://github.com/jasonmimick/christmas-carols/issues">issues with the music</a>
     we're working through. If anyone wants to work on an issue, feel free.</p>
</section>""")
    out.extend(sections)
    out.append("</div></main>")
    out.append('<script type="application/json" id="tunes">')
    out.append(json.dumps(tunes))
    out.append("""</script>
<script>
  const tunes = JSON.parse(document.getElementById("tunes").textContent);
  function renderTunes() {
    const available = document.querySelector(".sheet").clientWidth - 30;
    tunes.forEach((abc, n) => {
      const opts = {
        staffwidth: 760,
        add_classes: true,
        format: { gchordfont: "Helvetica 13 bold", vocalfont: "Georgia 13",
                  partsfont: "Helvetica 14 italic" }
      };
      if (available < 760) {
        opts.staffwidth = Math.max(available, 480);
        opts.wrap = { minSpacing: 1, maxSpacing: 2.7, preferredMeasuresPerLine: 3 };
        if (available < 480) opts.responsive = "resize";
      }
      ABCJS.renderAbc("paper" + n, abc, opts);
    });
  }
  renderTunes();
  let lastWidth = window.innerWidth, resizeTimer;
  window.addEventListener("resize", () => {
    if (window.innerWidth === lastWidth) return;
    lastWidth = window.innerWidth;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(renderTunes, 200);
  });

  const nav = document.querySelector("nav");
  document.querySelector("nav .navtitle").addEventListener("click", () => nav.classList.toggle("open"));

  function show(sectionId, navId, updateHash) {
    nav.classList.remove("open");
    document.querySelectorAll("section.page").forEach(s => s.classList.remove("current"));
    document.querySelectorAll("nav li").forEach(li => li.classList.remove("active"));
    const sec = document.getElementById(sectionId);
    sec.classList.add("current");
    document.getElementById(navId).classList.add("active");
    if (updateHash) history.replaceState(null, "", "#" + sec.dataset.slug);
    window.scrollTo(0, 0);
  }

  document.getElementById("navhome").addEventListener("click", () => show("home", "navhome", true));
  document.querySelectorAll("nav li[data-n]").forEach(li => {
    const n = +li.dataset.n;
    li.querySelector(".name").addEventListener("click", () => show("song" + n, "nav" + n, true));
    li.querySelector(".pr").addEventListener("click", e => {
      e.stopPropagation();
      show("song" + n, "nav" + n, true);
      window.print();
    });
  });

  document.getElementById("printall").addEventListener("click", () => {
    document.body.classList.add("print-all");
    window.print();
  });
  window.addEventListener("afterprint", () => document.body.classList.remove("print-all"));

  const bySlug = {};
  document.querySelectorAll("section.page").forEach(s => bySlug[s.dataset.slug] = s.id);
  const target = bySlug[location.hash.slice(1)] || "home";
  show(target, target === "home" ? "navhome" : "nav" + target.slice(4), false);
</script>
</body></html>""")
    return "\n".join(out)


def main():
    songs = [parse(p) for p in sorted((ROOT / "songs").glob("*.cho"))]
    (ROOT / "songbook-text.html").write_text(build(songs))
    sheets = sorted((ROOT / "songs-abc").glob("*.abc"))
    (ROOT / "songbook.html").write_text(build_sheet(sheets))
    print(f"Wrote {len(songs)} text songs and {len(sheets)} sheet-music songs; "
          f"outputs: songbook.html, songbook-text.html")


if __name__ == "__main__":
    main()
