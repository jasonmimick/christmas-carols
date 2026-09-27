#!/usr/bin/env python3
"""Render songs/*.cho into songbook.html and songbook-capo.html.

Song files use ChordPro-style inline chords: [G]Silent night, [D7]holy night.
Directives: {title: ..} {key: ..} {time: ..} {capo: N} {note: ..} {label: ..}

songbook.html       chords as written (open position)
songbook-capo.html  same songs for a guitar with a capo at {capo}, chords
                    shown as the shapes that player fingers
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Dm", "Gm", "Cm", "Fm"}
NOTE = r"[A-G][#b]?"

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

def shift_note(note, steps, flats):
    i = SHARPS.index(note) if note in SHARPS else FLATS.index(note)
    return (FLATS if flats else SHARPS)[(i + steps) % 12]


def shift_chord(chord, steps, flats):
    return re.sub(NOTE, lambda m: shift_note(m.group(), steps, flats), chord)


def shift_key(key, steps):
    """Return (new key name, whether to spell its chords with flats)."""
    root = re.match(NOTE, key).group()
    suffix = key[len(root):]
    flat_name = shift_note(root, steps, True) + suffix
    if flat_name in FLAT_KEYS:
        return flat_name, True
    return shift_note(root, steps, False) + suffix, False


def parse(path):
    song = {"title": path.stem, "key": "C", "time": "", "capo": "0", "note": "", "stanzas": [[]]}
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
    song["capo"] = int(song["capo"])
    return song


def render_line(line, steps, flats):
    parts = re.split(r"\[([^\]]+)\]", line)
    has_chords = len(parts) > 1
    segs = [("", parts[0])] if parts[0] else []
    for chord, text in zip(parts[1::2], parts[2::2]):
        segs.append((shift_chord(chord, steps, flats) if steps else chord, text))
    out = []
    for chord, text in segs:
        c = f'<span class="chord">{html.escape(chord)}</span>' if has_chords else ""
        out.append(f'<span class="seg">{c}<span class="lyric">{html.escape(text)}</span></span>')
    return f'<div class="line">{"".join(out)}</div>'


def describe(song, capo_book):
    """Return (key description, semitone shift, spell with flats)."""
    if capo_book and song["capo"]:
        shapes, flats = shift_key(song["key"], -song["capo"])
        return f'Capo {song["capo"]}, {shapes} shapes (sounds in {song["key"]})', -song["capo"], flats
    return f'Key of {song["key"]}', 0, False


def render_song(number, song, capo_book):
    desc, steps, flats = describe(song, capo_book)
    meta = " · ".join(x for x in (desc, song["time"]) if x)
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
                out.append(render_line(text, steps, flats))
        out.append("</div>")
    out.append("</section>")
    return "\n".join(out)


def build(songs, capo_book):
    title = "Christmas Carols: Guitar Chords" + (" (Capo Part)" if capo_book else "")
    rows = []
    for n, song in enumerate(songs, 1):
        desc, _, _ = describe(song, capo_book)
        rows.append(f"<tr><td>{n}</td><td>{html.escape(song['title'])}</td>"
                    f"<td>{html.escape(desc)}</td><td>{html.escape(song['time'])}</td></tr>")
    body = "\n".join(render_song(n, s, capo_book) for n, s in enumerate(songs, 1))
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
  @media (max-width: 700px) {
    nav { position: static; width: auto; border-right: none; border-bottom: 1px solid #ddd; }
    nav li .pr { visibility: visible; }
    main { margin-left: 0; }
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
    out.append('<nav><div class="navtitle">Christmas Carols</div><ul>'
               '<li id="navhome"><span class="name">Home</span></li></ul>'
               '<hr><div class="label">Set list</div><ul>')
    out.extend(nav)
    out.append('</ul><span class="all" id="printall">Print entire songbook</span></nav>')
    out.append("""<main><div class="sheet"><h1 id="booktitle">Christmas Carols</h1>
<section class="page" id="home" data-slug="home">
  <h1 class="hometitle">Christmas Carols</h1>
  <p>This Christmas season we are getting together to sing carols at each of our
     three churches &mdash; about an hour of the songs everyone knows, with guitars
     to carry the tune, and hot cocoa and cookies the whole time.</p>
  <h2>Where &amp; when</h2>
  <ul>
    <li>Holy Mother &amp; Child Parish &mdash; date &amp; time TBD</li>
    <li>St. Joseph's Church &mdash; date &amp; time TBD</li>
    <li>St. Paul's &mdash; date &amp; time TBD</li>
  </ul>
  <p>Dates and times will be posted here once the schedule is set.</p>
  <h2>The songbook</h2>
  <p>The set list on the left has all thirteen carols &mdash; click one to see its
     sheet music with lyrics and guitar chords. You can print any single song, or
     print the entire songbook and bring it with you.</p>
</section>""")
    out.extend(sections)
    out.append("</div></main>")
    out.append('<script type="application/json" id="tunes">')
    out.append(json.dumps(tunes))
    out.append("""</script>
<script>
  const tunes = JSON.parse(document.getElementById("tunes").textContent);
  tunes.forEach((abc, n) => {
    ABCJS.renderAbc("paper" + n, abc, {
      staffwidth: 760,
      add_classes: true,
      format: { gchordfont: "Helvetica 13 bold", vocalfont: "Georgia 13",
                partsfont: "Helvetica 14 italic" }
    });
  });

  function show(sectionId, navId, updateHash) {
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
    (ROOT / "songbook-text.html").write_text(build(songs, False))
    (ROOT / "songbook-capo.html").write_text(build(songs, True))
    sheets = sorted((ROOT / "songs-abc").glob("*.abc"))
    (ROOT / "songbook.html").write_text(build_sheet(sheets))
    print(f"Wrote {len(songs)} text songs and {len(sheets)} sheet-music songs; "
          f"outputs: songbook.html, songbook-text.html, songbook-capo.html")


if __name__ == "__main__":
    main()
