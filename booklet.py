"""Engrave the 13 carols (plus the appendix/*.txt charts, e.g. Jingle Bell Rock) into a spiral-bound print booklet PDF (sheet music with chords).

    python3 booklet.py            -> booklet/booklet-letter.pdf (the chosen size)
    python3 booklet.py all        -> one PDF per size in SIZES, for comparing trim sizes

Each song starts on a new page. A song that runs to two pages starts on a left-hand (even) page,
with a blank page inserted before it if needed, so the whole song shows when the book lies open.
The inside margin is wider for the spiral. Extra verses (W: lines) print under the music.
Needs abcm2ps and ps2pdf (brew install abcm2ps ghostscript).
"""
import re
import sys
import textwrap
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "booklet"

# Same music size on every page size, so only the trim size changes. 0.77 puts lyrics and
# chords at about 10pt; smaller pages just use more pages.
SCALE = 0.77

# name: (width in, height in, music scale, label)
SIZES = {
    "letter": (8.5, 11, 0.9, "Letter 8.5x11"),  # music 17% bigger, fills the page
    "7x10": (7, 10, SCALE, "7x10"),
    "6x9": (6, 9, SCALE, "6x9"),
    "half-letter": (5.5, 8.5, SCALE, "Half letter 5.5x8.5"),
}
MIN_FIT = 0.84   # smallest per-song shrink allowed to keep a song on one page
BINDING = 0.6    # both side margins match so double-sided pages line up; 0.6in clears spiral holes
OUTSIDE = 0.6

HEADER = """%%titlefont Times-Roman 22
%%composerfont Times-Italic 10
%%vocalfont Times-Roman 13
%%gchordfont Times-Bold 14
%%wordsfont Times-Roman 12
%%textfont Times-Roman 12
%%musicspace 0.4cm
%%vocalspace 4pt
%%titlespace 0.2cm
%%composerspace 0.3cm
%%wordsspace 0.6cm
%%maxshrink 0.8
%%footer "\t$P\t"
%%footerfont Times-Roman 10
"""


def song_source(path, i):
    """The .abc minus our private %comments, renumbered, with a fixed bars-per-line
    (the song's %bars-wide, else 4) so lines break on phrases like the site."""
    text = path.read_text()
    m = re.search(r"^%bars-wide:\s*(\d+)", text, re.M)
    bars = int(m.group(1)) if m else 4
    lines = [l for l in text.splitlines(True)
             if not (l.startswith("%curated") or l.startswith("%bars-wide"))]
    out = "".join(lines).replace("X:1", f"X:{i}", 1)
    return re.sub(r"^(K:.*)$", rf"\1\n%%barsperstaff {bars}", out, count=1, flags=re.M)


def page_setup(w, h, scale):
    return HEADER + (f"%%pagewidth {w}in\n%%pageheight {h}in\n%%scale {scale}\n"
                     f"%%leftmargin {BINDING}in\n%%rightmargin {OUTSIDE}in\n"
                     f"%%topmargin 0.45in\n%%botmargin 0.45in\n\n")


def engrave(abc_text, ps):
    """abcm2ps -1 (each tune on a new page); returns the page count."""
    src = ps.with_suffix(".abc")
    src.write_text(abc_text)
    r = subprocess.run(["abcm2ps", "-1", "-O", str(ps), str(src)], capture_output=True, text=True)
    src.unlink()
    if not ps.exists():
        raise RuntimeError(r.stdout + r.stderr)
    return ps.read_text(errors="ignore").count("%%Page:")


def build(name, w, h, scale):
    setup = page_setup(w, h, scale)
    ps = OUT / f"booklet-{name}.ps"
    pdf = OUT / f"booklet-{name}.pdf"
    body, page = setup, 1
    for i, p in enumerate(sorted((ROOT / "songs-abc").glob("*.abc")), 1):
        song = song_source(p, i).rstrip() + "\n\n"
        # A song just over one page is shrunk a little (down to MIN_FIT of the page scale) to fit.
        for fit in [x / 100 for x in range(100, int(MIN_FIT * 100) - 1, -2)] + [1.0]:
            sized = f"%%scale {scale * fit:.3f}\n" + song
            n = engrave(setup + sized, ps)
            if n == 1:
                break
        if n == 1 and fit < 1.0:   # one more notch so the last line clears the page number
            sized = f"%%scale {scale * (fit - 0.02):.3f}\n" + song
        song = sized
        if n > 1 and page % 2 == 1:   # multi-page song would start on a right page
            body += "%%newpage\n%%text  \n\n"
            page += 1
        body += song
        page += n
    total = engrave(body, ps)
    if total != page - 1:
        print(f"  warning: expected {page - 1} pages, got {total}")
    # Other tunes (appendix/*.txt) go at the end, one page each, as fixed-width text so the
    # ASCII chord diagrams line up. abcm2ps can't keep spacing in text, so these pages are
    # written as plain PostScript and appended to the music before converting to PDF.
    pages = [text_page(t, w, h, total + k) for k, t in enumerate(sorted((ROOT / "appendix").glob("*.txt")), 1)]
    extra = OUT / "appendix.ps"
    extra.write_text("%!PS\n" + "".join(pages))
    subprocess.run(["gs", "-q", "-sDEVICE=pdfwrite", f"-dDEVICEWIDTHPOINTS={w*72:.0f}",
                    f"-dDEVICEHEIGHTPOINTS={h*72:.0f}", "-dFIXEDMEDIA", "-o", str(pdf), str(ps), str(extra)],
                   check=True)
    ps.unlink()
    extra.unlink()
    return pdf


def ps_str(text):
    return "(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def text_page(path, w, h, number):
    """One PostScript page: centered title, then the file's lines in Courier, sized so the
    longest line fits the width and all lines fit the height."""
    title, *raw = path.read_text().rstrip().splitlines()
    # Wrap long prose lines (not indented); indented lines are chord rows and diagrams, kept as is.
    lines = []
    for l in raw:
        if len(l) > 80 and not l.startswith(" "):
            lines += textwrap.wrap(l, 80, subsequent_indent="    ")
        else:
            lines.append(l)
    W, H = w * 72, h * 72
    left, top, bottom = BINDING * 72, H - 0.6 * 72, 0.6 * 72
    longest = max(len(l) for l in lines) or 1
    size = min(11.0, (W - 2 * left) / (longest * 0.6), (top - 50 - bottom) / (len(lines) * 1.2))
    out = [f"%%Page: {number} {number}\n",
           f"/Times-Roman findfont 22 scalefont setfont {W/2:.1f} {top - 16:.1f} moveto "
           f"{ps_str(title)} dup stringwidth pop 2 div neg 0 rmoveto show\n",
           f"/Courier findfont {size:.2f} scalefont setfont\n"]
    y = top - 50
    for l in lines:
        out.append(f"{left:.1f} {y:.1f} moveto {ps_str(l)} show\n")
        y -= size * 1.2
    out.append(f"/Times-Roman findfont 10 scalefont setfont {W/2:.1f} {0.3*72:.1f} moveto "
               f"({number}) dup stringwidth pop 2 div neg 0 rmoveto show\nshowpage\n")
    return "".join(out)


def page_count(pdf):
    r = subprocess.run(["gs", "-q", "-dNODISPLAY", "-dNOSAFER", "-c",
                        f"({pdf}) (r) file runpdfbegin pdfpagecount = quit"],
                       capture_output=True, text=True)
    return r.stdout.strip()


def main():
    OUT.mkdir(exist_ok=True)
    names = SIZES if sys.argv[1:] == ["all"] else ["letter"]
    for name in names:
        w, h, scale, label = SIZES[name]
        pdf = build(name, w, h, scale)
        print(f"{label:22} {page_count(pdf):>3} pages  {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
