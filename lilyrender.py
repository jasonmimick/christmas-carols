"""Engrave songs-abc/*.abc to SVG with LilyPond (abc2ly -> lilypond), cached by content hash.

render(path) returns (wide_svg, narrow_svg): the same song set to two line widths, so the page
can show the wide one on desktop/print and the narrow one on phones without shrinking the text.
Needs `lilypond` and `abc2ly` on PATH (brew install lilypond).
"""
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

CACHE = Path(__file__).parent / ".lycache"
VERSION = "3"  # bump when the post-processing below changes
WIDTHS = {"wide": 190, "narrow": 108}  # line width in mm
LABELS = {"Chorus", "Refrain", "Verse"}


def _fix_ly(ly, width_mm):
    ly = re.sub(r'tagline = "[^"]*"', "tagline = ##f", ly)
    ly = re.sub(r'^\s*(title|composer) = .*\n', "", ly, flags=re.M)
    ly = re.sub(r'\\midi\s*\{\s*\}', "", ly)
    ly = ly.replace('\\#', "#")

    def chord(m):
        t = m.group(1)
        return f'^\\markup \\italic "{t}"' if t in LABELS else f'^\\markup \\sans \\bold "{t}"'

    ly = re.sub(r'\^"([^"]*)"', chord, ly)
    ly += f"""
\\paper {{
  paper-width = {width_mm + 4}\\mm
  line-width = {width_mm}\\mm
  left-margin = 2\\mm
  right-margin = 2\\mm
  top-margin = 1\\mm
  bottom-margin = 1\\mm
  indent = 0\\mm
  ragged-bottom = ##t
  page-breaking = #ly:one-page-breaking
}}
\\layout {{
  \\context {{ \\Score \\override BarNumber.stencil = ##f }}
  \\context {{ \\Lyrics \\override LyricText.font-size = #-1 }}
}}
"""
    return ly


def _engrave(abc_path, width_mm, work):
    ly_path = work / "song.ly"
    # W: lines (extra verses) become a text block in abc2ly's output; the page prints them itself.
    src = work / "song.abc"
    src.write_text("".join(l for l in abc_path.read_text().splitlines(True) if not l.startswith("W:")))
    subprocess.run(["abc2ly", "-o", str(ly_path), str(src)], check=True,
                   capture_output=True, text=True)
    ly_path.write_text(_fix_ly(ly_path.read_text(), width_mm))
    r = subprocess.run(["lilypond", "-dcrop", "-dbackend=svg", "-o", str(work / "song"), str(ly_path)],
                       capture_output=True, text=True)
    out = work / "song.cropped.svg"
    if not out.exists():
        raise RuntimeError(f"lilypond failed for {abc_path.name}:\n{r.stderr[-800:]}")
    svg = out.read_text()
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    svg = re.sub(r'(<svg[^>]*?) width="[^"]*" height="[^"]*"', r"\1", svg, count=1)
    return svg


def render(abc_path):
    abc_path = Path(abc_path)
    key = hashlib.sha1((VERSION + abc_path.read_text()).encode()).hexdigest()[:16]
    CACHE.mkdir(exist_ok=True)
    result = []
    for name, width in WIDTHS.items():
        cached = CACHE / f"{abc_path.stem}-{name}-{key}.svg"
        if not cached.exists():
            with tempfile.TemporaryDirectory() as tmp:
                cached.write_text(_engrave(abc_path, width, Path(tmp)))
            for old in CACHE.glob(f"{abc_path.stem}-{name}-*.svg"):
                if old != cached:
                    old.unlink()
        result.append(cached.read_text())
    return tuple(result)
