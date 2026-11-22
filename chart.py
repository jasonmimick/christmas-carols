"""Read an appendix/*.txt chord chart ("Other tunes...").

Format: line 1 is the title; the lines up to the first blank line are notes (composer, key, source).
After that, blank lines separate sections. A section's first line is its heading when it starts
with a capitalized word (VERSE, CHORUS ...). Lines with [Chord] marks are chords over words, as in
ChordPro. Indented lines (bar grids, chord diagrams) are fixed-width text. Other lines are notes.
A line '---' starts a new page in the print booklet (ignored on the site).
"""
import re


def parse_chart(path):
    title, *rest = path.read_text().rstrip().splitlines()
    meta, i = [], 0
    while i < len(rest) and rest[i].strip():
        meta.append(rest[i])
        i += 1
    sections, cur = [], []
    for line in rest[i:]:
        if line.strip() == "---":
            if cur:
                sections.append(cur)
            sections.append([("page", "")])
            cur = []
        elif not line.strip():
            if cur:
                sections.append(cur)
            cur = []
        elif not cur and not line.startswith((" ", "[")) and re.sub(r"[^A-Za-z]", "", line.split("(")[0].split('"')[0]).isupper():
            cur.append(("label", line.strip()))
        elif "[" in line and not line.startswith(" "):
            cur.append(("chords", line))
        elif line.startswith(" "):
            cur.append(("mono", line))
        else:
            cur.append(("note", line))
    if cur:
        sections.append(cur)
    return {"title": title, "meta": meta, "sections": sections}


def segments(line):
    """'[A]Chestnuts [Bm7]roasting' -> [('', ''), ('A', 'Chestnuts '), ('Bm7', 'roasting')]"""
    parts = re.split(r"\[([^\]]+)\]", line)
    segs = [("", parts[0])] if parts[0] else []
    segs += list(zip(parts[1::2], parts[2::2]))
    # A chord in the middle of a word: hyphenate the first half (Eski-mos), as chord charts do.
    return [(ch, t + "-" if t and t[-1].isalpha() and i + 1 < len(segs) and segs[i + 1][1][:1].isalpha() else t)
            for i, (ch, t) in enumerate(segs)]
