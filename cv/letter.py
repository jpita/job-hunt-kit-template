#!/usr/bin/env python3
"""Build one cover letter from a data file.

    me/.venv/bin/python cv/letter.py /tmp/acme_letter.py

The data file needs OUT, TITLE, ROLE, TAGLINE and BODY (a list of paragraphs,
the first one is the greeting).
"""
import importlib.util
import os
import sys

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvlib as cv  # noqa: E402

FIELDS = ("OUT", "TITLE", "ROLE", "TAGLINE", "BODY")

# A letter is read, not scanned, so the body is larger than the CV body.
LETTER = ParagraphStyle("letter", fontName="Helvetica", fontSize=9.6, leading=13.4,
                        textColor=cv.BODY, spaceAfter=7)


def load(path):
    spec = importlib.util.spec_from_file_location("letterdata", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [f for f in FIELDS if not hasattr(mod, f)]
    if missing:
        sys.exit(f"{os.path.basename(path)} is missing: {', '.join(missing)}")
    return mod


def render(d):
    story = cv.header(d.ROLE, d.TAGLINE)
    story.append(Spacer(1, 12))
    story += [Paragraph(p, LETTER) for p in d.BODY]
    cv.build(d.OUT, d.TITLE, story)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: me/.venv/bin/python cv/letter.py <data file>")
    render(load(sys.argv[1]))
