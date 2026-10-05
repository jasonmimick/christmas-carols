"""Engrave songs-abc/*.abc to SVG with abcm2ps, a fixed number of bars per line, cached by content hash.

render(path) returns (wide_svg, narrow_svg): wide is 4 bars per line for desktop and print, narrow is
2 bars per line for phones, so the notes and lyrics keep a readable size. Needs `abcm2ps` on PATH
(brew install abcm2ps).
"""
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

CACHE = Path(__file__).parent / ".m2cache"
VERSION = "1"  # bump when the settings below change

COMMON = """%%writefields TCOPR 0
%%vocalfont Times-Roman 13
%%gchordfont Helvetica-Bold 12
%%partsfont Times-Italic 12
%%annotationfont Helvetica-Oblique 11
%%musicspace 0.6cm
%%vocalspace 4pt
%%topspace 0
%%titlespace 0
%%leftmargin 0.2cm
%%rightmargin 0.2cm
%%maxshrink 0.7
"""
LAYOUTS = {
    "wide": "%%pagewidth 20.6cm\n%%staffwidth 20.2cm\n%%barsperstaff 4\n",
    "narrow": "%%pagewidth 11cm\n%%staffwidth 10.6cm\n%%barsperstaff 2\n",
}


def _engrave(abc_path, layout, work):
    # W: lines (extra verses) are printed by the page, so they are dropped here.
    body = "".join(l for l in abc_path.read_text().splitlines(True) if not l.startswith("W:"))
    src = work / "song.abc"
    src.write_text(COMMON + LAYOUTS[layout] + "\n" + body)
    r = subprocess.run(["abcm2ps", "-g", "-O", str(work / "out.svg"), str(src)],
                       capture_output=True, text=True)
    out = work / "out001.svg"
    if not out.exists():
        raise RuntimeError(f"abcm2ps failed for {abc_path.name}:\n{r.stdout[-600:]}{r.stderr[-600:]}")
    svg = out.read_text()
    svg = re.sub(r"<\?xml[^>]*\?>\s*|<!DOCTYPE[^>]*>\s*", "", svg)
    m = re.search(r'width="([\d.]+)px" height="([\d.]+)px"', svg)
    svg = svg.replace(m.group(0), f'viewBox="0 0 {m.group(1)} {m.group(2)}"', 1)
    return svg


def render(abc_path):
    abc_path = Path(abc_path)
    key = hashlib.sha1((VERSION + abc_path.read_text()).encode()).hexdigest()[:16]
    CACHE.mkdir(exist_ok=True)
    result = []
    for layout in LAYOUTS:
        cached = CACHE / f"{abc_path.stem}-{layout}-{key}.svg"
        if not cached.exists():
            with tempfile.TemporaryDirectory() as tmp:
                cached.write_text(_engrave(abc_path, layout, Path(tmp)))
            for old in CACHE.glob(f"{abc_path.stem}-{layout}-*.svg"):
                if old != cached:
                    old.unlink()
        result.append(cached.read_text())
    return tuple(result)
