"""Shared layout and the fixed facts for every CV.

The facts (name, contact, jobs, education) come from me/profile.py, so every
CV prints the same work history and dates. Change them there, never in a CV.
"""
import importlib.util
import os
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ME = os.environ.get("JOBKIT_ME", os.path.join(ROOT, "me"))


def _load_profile():
    path = os.path.join(ME, "profile.py")
    if not os.path.exists(path):
        sys.exit(f"No {path}. Run setup: copy templates/me to me/ and fill profile.py.")
    spec = importlib.util.spec_from_file_location("profile", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load_profile()

NAME = P.NAME
CONTACT = P.CONTACT
EDUCATION = P.EDUCATION
SPEAKING = getattr(P, "SPEAKING", "")
TOOLS = P.TOOLS
JOBS = P.JOBS
BANNED = getattr(P, "BANNED", [])
OUT_DIR = os.path.join(ME, "cvs")

ACCENT_HEX = getattr(P, "ACCENT", "#00695C")
ACCENT = HexColor(ACCENT_HEX)
DARK = HexColor("#1A1A1A")
BODY = HexColor("#2E2E2E")
GRAY = HexColor("#6B6B6B")
HAIR = HexColor("#D6DEDC")

MARGIN = 17  # mm, left and right

S = {
    "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=DARK),
    "role": ParagraphStyle("role", fontName="Helvetica-Bold", fontSize=11, leading=13.5, textColor=ACCENT),
    "tagline": ParagraphStyle("tagline", fontName="Helvetica", fontSize=8.4, leading=10.8, textColor=GRAY),
    "contact": ParagraphStyle("contact", fontName="Helvetica", fontSize=8.4, leading=10.8, textColor=GRAY),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9.5, leading=11.5, textColor=ACCENT,
                        spaceBefore=7.5, spaceAfter=0),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.6, leading=11.3, textColor=BODY),
    "skill": ParagraphStyle("skill", fontName="Helvetica", fontSize=8.6, leading=11.3, textColor=BODY,
                            spaceAfter=2.2),
    "jobline": ParagraphStyle("jobline", fontName="Helvetica", fontSize=9.4, leading=12, textColor=DARK,
                              spaceAfter=2.5),
    "edu": ParagraphStyle("edu", fontName="Helvetica", fontSize=7.6, leading=9.7, textColor=BODY,
                          spaceBefore=3),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=8.6, leading=11.3, textColor=BODY,
                             leftIndent=8, bulletIndent=1, spaceAfter=1.9),
}


def with_defaults(current, overrides=None):
    """Bullets for every job, in JOBS order.

    The first job is the current one and is tailored on every CV. The older
    jobs use their default bullets unless this CV overrides one by its key.
    """
    overrides = overrides or {}
    unknown = set(overrides) - {j["key"] for j in JOBS}
    if unknown:
        sys.exit(f"OVERRIDES names unknown job keys: {', '.join(sorted(unknown))}")
    out = [current]
    for j in JOBS[1:]:
        out.append(overrides.get(j["key"]) or j["bullets"])
    return out


def header(role, tagline, contact=None):
    return [
        Paragraph(NAME.upper(), S["name"]),
        Spacer(1, 1.5),
        Paragraph(role, S["role"]),
        Spacer(1, 2.5),
        Paragraph(tagline, S["tagline"]),
        Paragraph(contact or CONTACT, S["contact"]),
        HRFlowable(width="100%", thickness=1.1, color=ACCENT, spaceBefore=5, spaceAfter=0),
    ]


def sec(text):
    return [Paragraph(text, S["h"]),
            HRFlowable(width="100%", thickness=0.5, color=HAIR, spaceBefore=1.5, spaceAfter=4)]


def job(index, bullets):
    # Keep this one Paragraph. A two-column table extracts out of order and CV parsers
    # then detach the role from its employer.
    j = JOBS[index]
    line = ('<b>%s</b> &middot; <font color="%s">%s</font> '
            '&middot; <font color="#6B6B6B">%s</font>' % (j["title"], ACCENT_HEX, j["company"], j["dates"]))
    out = [Spacer(1, 4), Paragraph(line, S["jobline"])]
    out += [Paragraph(t, S["bullet"], bulletText="•") for t in bullets]
    return out


def skills(pairs):
    return [Paragraph("<b>%s</b> &middot; %s" % (k, v), S["skill"]) for k, v in pairs]


def summary(text):
    return [Paragraph(text, S["body"])]


def speaking():
    if not SPEAKING:
        return []
    return [Paragraph('<b><font color="%s">SPEAKING</font></b>&nbsp;&nbsp; %s' % (ACCENT_HEX, SPEAKING),
                      S["edu"])]


def education():
    return [Paragraph('<b><font color="%s">EDUCATION</font></b>&nbsp;&nbsp; %s' % (ACCENT_HEX, EDUCATION),
                      S["edu"])]


def build(out_name, doc_title, story):
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = SimpleDocTemplate(os.path.join(OUT_DIR, out_name), pagesize=A4,
                            leftMargin=MARGIN * mm, rightMargin=MARGIN * mm,
                            topMargin=11 * mm, bottomMargin=10 * mm,
                            title=doc_title, author=NAME)
    doc.build(story)
    print("built", out_name)
