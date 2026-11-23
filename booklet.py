"""Engrave the 13 carols (plus the appendix/*.txt charts, e.g. Jingle Bell Rock) into a spiral-bound print booklet PDF (sheet music with chords).

    python3 booklet.py            -> booklet/booklet-letter.pdf (the chosen size)
    python3 booklet.py all        -> one PDF per size in SIZES, for comparing trim sizes

booklet-letter.pdf is served on the site as /songbook.pdf.

Each song starts on a new page. A song that runs to two pages starts on a left-hand (even) page,
with a blank page inserted before it if needed, so the whole song shows when the book lies open.
The inside margin is wider for the spiral. Extra verses (W: lines) print under the music.
Needs abcm2ps and ps2pdf (brew install abcm2ps ghostscript).
"""
import re
import sys
import subprocess
from pathlib import Path

from chart import parse_chart, segments

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


FRONT = 2   # title page and contents come before the carols, which start on page 3


def build(name, w, h, scale):
    setup = page_setup(w, h, scale)
    ps = OUT / f"booklet-{name}.ps"
    pdf = OUT / f"booklet-{name}.pdf"
    # Two placeholder pages stand in for the front matter so abcm2ps numbers the carols from 3;
    # they are dropped and replaced with the real title and contents pages at the end.
    body, page = setup + "%%text  \n%%newpage\n%%text  \n\n", FRONT + 1
    contents = []
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
        contents.append((re.search(r"^T:\s*(.*)$", p.read_text(), re.M).group(1), page))
        body += song
        page += n
    total = engrave(body, ps)
    if total != page - 1:
        print(f"  warning: expected {page - 1} pages, got {total}")
    # Appendix A: a divider page, then the chord charts (appendix/*.txt), drawn as PostScript.
    pages = [divider_page("Appendix A", "Additional Songs", w, h)]
    appendix_start = total + 1
    for t in sorted((ROOT / "appendix").glob("*.txt")):
        parts = chart_pages(parse_chart(t))
        contents.append(("A:" + parts[0]["title"], total + len(pages) + 1))
        for c in parts:
            pages.append(chart_page(c, w, h, total + len(pages) + 1))
    extra = OUT / "appendix.ps"
    extra.write_text("%!PS\n" + CHART_PS + "".join(pages))
    front = OUT / "front.ps"
    front.write_text("%!PS\n" + contents_page(contents, appendix_start, w, h))
    cover = cover_pdf()
    music = OUT / f"music-{name}.pdf"
    subprocess.run(["gs", "-q", "-sDEVICE=pdfwrite", f"-dFirstPage={FRONT + 1}", "-o", str(music), str(ps)], check=True)
    subprocess.run(["gs", "-q", "-sDEVICE=pdfwrite", f"-dDEVICEWIDTHPOINTS={w*72:.0f}",
                    f"-dDEVICEHEIGHTPOINTS={h*72:.0f}", "-dFIXEDMEDIA", "-o", str(pdf),
                    str(cover), str(front), str(music), str(extra)], check=True)
    for f in (ps, extra, front, music):
        f.unlink()
    return pdf


def centered(text, font, size, x, y):
    return (f"/{font} findfont {size} scalefont setfont {x:.1f} {y:.1f} moveto "
            f"{ps_str(text)} dup stringwidth pop 2 div neg 0 rmoveto show\n")


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def cover_pdf():
    """Page 1: cover.html (title, the three churches on a map, Christmas icons) printed by headless
    Chrome. Chrome fetches the IM Fell English font, so this needs the network."""
    out = OUT / "cover.pdf"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=5000",
                    f"--print-to-pdf={out}", (ROOT / "cover.html").as_uri()], check=True, capture_output=True)
    return out


def title_page(w, h):   # plain fallback title page, not used since cover.html
    W, H = w * 72, h * 72
    return ("%%Page: 1 1\n" + centered("Christmas Carols", "Times-Roman", 46, W / 2, H * 0.62) +
            f"0.6 setlinewidth {W/2 - 72:.1f} {H*0.62 - 28:.1f} moveto 144 0 rlineto stroke\n" +
            centered("Sheet music with chords", "Times-Italic", 16, W / 2, H * 0.62 - 56) +
            centered("13 carols  \267  Appendix A: additional songs", "Times-Roman", 11, W / 2, H * 0.62 - 80) +
            "showpage\n")


def contents_page(contents, appendix_start, w, h):
    """Song titles with dot leaders to right-aligned page numbers; Appendix A as its own heading."""
    W, H = w * 72, h * 72
    left, right = (BINDING + 0.5) * 72, W - (OUTSIDE + 0.5) * 72
    out = ["%%Page: 2 2\n", centered("Contents", "Times-Roman", 26, W / 2, H - 1.3 * 72)]
    y = H - 2.0 * 72
    pitch = 19

    def entry(title, page, font="Times-Roman", size=12.5):
        return (f"/{font} findfont {size} scalefont setfont {left:.1f} {y:.1f} moveto {ps_str(title)} show "
                f"currentpoint pop 6 add /dx exch def "
                f"/Times-Roman findfont {size} scalefont setfont ({page}) stringwidth pop {right:.1f} exch sub /px exch def "
                f"px {right:.1f} sub 0 rmoveto "
                f"dx 5 px 10 sub {{ {y:.1f} moveto (.) show }} for "
                f"px {y:.1f} moveto ({page}) show\n")

    in_appendix = False
    for title, page in contents:
        if title.startswith("A:") and not in_appendix:
            in_appendix = True
            y -= pitch * 0.9
            out.append(entry("Appendix A: Additional Songs", appendix_start, "Times-Bold", 12.5))
            y -= pitch
        if title.startswith("A:"):
            title = title[2:]
            out.append(f"/LM {left + 18:.1f} def\n")
            out.append(entry(title, page).replace(f"{left:.1f} {y:.1f} moveto {ps_str(title)}", f"{left + 18:.1f} {y:.1f} moveto {ps_str(title)}"))
        else:
            out.append(entry(title, page))
        y -= pitch
    out.append("showpage\n")
    return "".join(out)


def divider_page(label, title, w, h):
    W, H = w * 72, h * 72
    return ("%%Page: 0 0\n" + centered(label.upper(), "Times-Roman", 14, W / 2, H * 0.58 + 40) +
            centered(title, "Times-Roman", 34, W / 2, H * 0.58) +
            f"0.6 setlinewidth {W/2 - 54:.1f} {H*0.58 - 24:.1f} moveto 108 0 rlineto stroke\nshowpage\n")


def ps_str(text):
    return "(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def measure(lines):
    """Exact widths at 1pt of every words segment (Times-Roman) and chord (Times-Bold), via ghostscript."""
    keys = sorted({("R", t) for l in lines for ch, t in segments(l)} | {("B", ch) for l in lines for ch, t in segments(l)})
    ps = "".join(f"/{'Times-Roman' if f == 'R' else 'Times-Bold'} findfont 1 scalefont setfont {ps_str(t)} stringwidth pop =\n"
                 for f, t in keys)
    r = subprocess.run(["gs", "-q", "-dNODISPLAY", "-dNOSAFER", "-"], input=ps + "quit\n", capture_output=True, text=True)
    return dict(zip(keys, map(float, r.stdout.split())))


def chart_pages(c):
    """Split a chart at its '---' lines into one chart per printed page."""
    pages = [[]]
    for sec in c["sections"]:
        if sec[0][0] == "page":
            pages.append([])
        else:
            pages[-1].append(sec)
    return [dict(c, sections=secs, title=c["title"] + (" (continued)" if i else ""), meta=c["meta"] if not i else [])
            for i, secs in enumerate(pages)]


CHART_PS = """/chordline { % [chord lyric ...] y -> draws chords above words from the left margin
  /y exch def /segs exch def /x LEFT def
  0 2 segs length 1 sub { /i exch def
    /c segs i get def /l segs i 1 add get def
    /Times-Roman findfont SZ scalefont setfont l stringwidth pop /lw exch def
    /Times-Bold findfont CSZ scalefont setfont c stringwidth pop /cw exch def
    c length 0 gt { x y SZ 1.0 mul add moveto c show } if
    /Times-Roman findfont SZ scalefont setfont x y moveto l show
    /x x lw c length 0 gt { cw SZ 0.6 mul add } { 0 } ifelse 2 copy lt { exch } if pop add def
  } for } def
"""


# Typesetting for the appendix charts: one fixed size for every chart, matched to the engraved
# carols (lyrics about 12pt Times, chords Times-Bold), rather than scaled to fill each page.
LYRIC_PT = 12      # words
CHORD_PT = 11.5    # chords, Times-Bold, set 0.95 * LYRIC_PT above the words
LINE_PITCH = 2.35  # chord+words line, in LYRIC_PT units
LABEL_PT = 10      # section headings, bold, letterspaced capitals
NOTE_PT = 8.5      # composer line, key line and footnotes
MIN_PT = 9         # a chart that will not fit even in two columns is shrunk, down to this


def chart_page(c, w, h, number):
    """One PostScript page for an appendix chart: title, composer and key under it, then each
    section with a small bold heading and chords above the words. Bar grids and chord diagrams stay
    fixed-width. Notes (source, chord key) go at the foot of the page. Type is a fixed size; a
    chart that is too long goes to two columns, and only then shrinks."""
    W, H = w * 72, h * 72
    left, top, bottom = BINDING * 72, H - 0.6 * 72, 0.75 * 72
    width = W - left - OUTSIDE * 72
    gutter = 0.4 * 72
    secs = [sec for sec in c["sections"] if any(k != "note" for k, t in sec)]
    notes = [t for sec in c["sections"] if all(k == "note" for k, t in sec) for k, t in sec]
    notes = c["meta"][2:] + notes
    head = 20 + 16 + (13 if len(c["meta"]) > 1 else 0) + 18
    avail = top - head - (bottom + len(notes) * NOTE_PT * 1.3 + 6)
    widths = measure([t for sec in secs for k, t in sec if k == "chords"])

    def one_w(ch, t, size):   # same spacing rule as chordline in CHART_PS
        return max(widths[("R", t)], widths[("B", ch)] / 0.95 * (CHORD_PT / LYRIC_PT) + 0.6 if ch else 0) * size

    def line_w(t, size):
        return sum(one_w(ch, x, size) for ch, x in segments(t))

    def mono_size(colw):
        longest = max([len(t) for sec in secs for k, t in sec if k == "mono"] or [1])
        return min(10.5, colw / (longest * 0.6))

    def sec_h(sec, size, colw):
        return size * 1.1 + sum({"label": LABEL_PT * 1.6, "note": NOTE_PT * 1.4,
                                 "mono": mono_size(colw) * 1.2, "chords": size * LINE_PITCH}[k] for k, t in sec)

    def fits(cols, colw, size):
        return (max(sum(sec_h(x, size, colw) for x in col) for col in cols) <= avail and
                all(line_w(t, size) <= colw for sec in secs for k, t in sec if k == "chords"))

    def split(colw):
        total = sum(sec_h(x, LYRIC_PT, colw) for x in secs)
        best = min(range(1, len(secs)), key=lambda n: abs(sum(sec_h(x, LYRIC_PT, colw) for x in secs[:n]) - total / 2))
        return [secs[:best], secs[best:]]

    two = (width - gutter) / 2
    options = [([secs], width)] + ([(split(two), two)] if len(secs) > 1 else [])
    size, cols, colw = MIN_PT, *options[0]
    for pt in [x / 4 for x in range(int(LYRIC_PT * 4), int(MIN_PT * 4) - 1, -1)]:
        ok = [o for o in options if fits(*o, pt)]
        if ok:
            size, (cols, colw) = pt, ok[0]
            break
    ms = mono_size(colw)
    out = [f"%%Page: {number} {number}\n/SZ {size:.2f} def /CSZ {size * CHORD_PT / LYRIC_PT:.2f} def\n",
           f"/Times-Roman findfont 20 scalefont setfont {W/2:.1f} {top - 14:.1f} moveto "
           f"{ps_str(c['title'])} dup stringwidth pop 2 div neg 0 rmoveto show\n"]
    y = top - 14 - 16
    for i, m in enumerate(c["meta"][:2]):
        font = "Times-Italic" if i == 0 else "Times-Roman"
        out.append(f"/{font} findfont {NOTE_PT + 1.5 if i == 0 else NOTE_PT + 0.5} scalefont setfont {W/2:.1f} {y:.1f} moveto "
                   f"{ps_str(m)} dup stringwidth pop 2 div neg 0 rmoveto show\n")
        y -= 13
    y0 = top - head
    for ci, col in enumerate(cols):
        x, y = left + ci * (colw + gutter), y0
        out.append(f"/LEFT {x:.1f} def\n")
        for si, sec in enumerate(col):
            y -= size * 1.1 if si else 0
            for k, t in sec:
                if k == "label":
                    y -= LABEL_PT * 1.6
                    name, _, rest = t.partition("(")
                    name, _, cue = name.partition('"')
                    out.append(f"/Times-Bold findfont {LABEL_PT} scalefont setfont {x:.1f} {y + LABEL_PT * 0.4:.1f} moveto "
                               f"0.6 0 {ps_str(name.strip().upper())} ashow\n")
                    extra = ("(" + rest) if rest else ('"' + cue) if cue else ""
                    if extra:
                        out.append(f"/Times-Italic findfont {LABEL_PT} scalefont setfont 6 0 rmoveto {ps_str(extra)} show\n")
                elif k == "chords":
                    y -= size * LINE_PITCH
                    arr = " ".join(ps_str(ch) + " " + ps_str(tx) for ch, tx in segments(t))
                    out.append(f"[{arr}] {y + size * 0.6:.1f} chordline\n")
                elif k == "note":
                    y -= NOTE_PT * 1.4
                    out.append(f"/Times-Italic findfont {NOTE_PT + 1} scalefont setfont {x:.1f} {y:.1f} moveto {ps_str(t)} show\n")
                else:
                    y -= ms * 1.2
                    out.append(f"/Courier-Bold findfont {ms:.2f} scalefont setfont {x:.1f} {y:.1f} moveto {ps_str(t)} show\n")
    # footnotes above the page number, with a short rule
    y = bottom + (len(notes) - 1) * NOTE_PT * 1.3
    if notes:
        out.append(f"0.5 setlinewidth {left:.1f} {y + NOTE_PT * 1.4:.1f} moveto 1.2 72 mul 0 rlineto stroke\n")
    for t in notes:
        out.append(f"/Times-Italic findfont {NOTE_PT} scalefont setfont {ps_str(t)} stringwidth pop "
                   f"{width:.1f} exch div dup 1 lt {{ currentfont exch scalefont setfont }} {{ pop }} ifelse "
                   f"{left:.1f} {y:.1f} moveto {ps_str(t)} show\n")
        y -= NOTE_PT * 1.3
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
