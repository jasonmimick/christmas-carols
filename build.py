#!/usr/bin/env python3
"""Render songs/*.cho into songbook.html and songbook-capo.html.

Song files use ChordPro-style inline chords: [G]Silent night, [D7]holy night.
Directives: {title: ..} {key: ..} {time: ..} {capo: N} {note: ..} {label: ..}

songbook.html       chords as written (open position)
songbook-capo.html  same songs for a guitar with a capo at {capo}, chords
                    shown as the shapes that player fingers
"""
import html
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

INDEX_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Christmas Carols</title>
<style>
  body { background: #fff; color: #000; margin: 0; font-family: Helvetica, Arial, sans-serif;
         font-size: 17px; line-height: 1.55; }
  .wrap { max-width: 560px; padding: 2rem 20px 3rem; }
  h1 { font-size: 1.9rem; margin: 0 0 1.5rem; font-weight: 700; }
  h2 { font-size: 1.15rem; margin: 2rem 0 0.5rem; font-weight: 700; }
  ul, ol { margin: 0; padding-left: 1.4rem; }
  li { padding: 0.15rem 0; }
  a { color: #000; }
</style></head><body>
<div class="wrap">
  <h1>Christmas Carols</h1>

  <h2>Churches</h2>
  <ul>
    <li>Holy Mother &amp; Child Parish &mdash; date &amp; time TBD</li>
    <li>St. Joseph's Church &mdash; date &amp; time TBD</li>
    <li>St. Paul's &mdash; date &amp; time TBD</li>
  </ul>

  <h2>Songbook</h2>
  <ul>
    <li><a href="songbook.html">Print the songbook (PDF)</a></li>
  </ul>

  <h2>Songs</h2>
  <ol>
{song_items}
  </ol>
</div>
</body></html>
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


def main():
    songs = [parse(p) for p in sorted((ROOT / "songs").glob("*.cho"))]
    (ROOT / "songbook.html").write_text(build(songs, False))
    (ROOT / "songbook-capo.html").write_text(build(songs, True))
    items = "\n".join(f"    <li>{html.escape(s['title'])}</li>" for s in songs)
    (ROOT / "index.html").write_text(INDEX_HTML.replace("{song_items}", items))
    print(f"Wrote {len(songs)} songs to index.html, songbook.html and songbook-capo.html")


if __name__ == "__main__":
    main()
