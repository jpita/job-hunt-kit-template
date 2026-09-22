#!/bin/bash
# Rebuild every CV in me/cv-data and check them all.
#   cv/build.sh                         all CVs
#   cv/build.sh me/cv-data/backend.py   one CV, still checks them all
# Done only when it prints ALL GOOD.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
ME="${JOBKIT_ME:-$ROOT/me}"
export JOBKIT_ME="$ME"
PY="${PY:-$ME/.venv/bin/python}"; [ -x "$PY" ] || PY=python3

$PY -c "import reportlab" 2>/dev/null || { echo "reportlab missing for $PY. Run: $PY -m pip install reportlab"; exit 1; }
command -v pdftotext >/dev/null || { echo "pdftotext missing. Run: brew install poppler"; exit 1; }

FILES=("$@"); [ ${#FILES[@]} -eq 0 ] && FILES=("$ME"/cv-data/*.py)
[ -e "${FILES[0]}" ] || { echo "No data files in $ME/cv-data"; exit 1; }
fail=0
for f in "${FILES[@]}"; do
  if ! out=$($PY cv/render.py "$f" 2>&1); then
    echo "BUILD FAILED  $f"; echo "$out" | tail -5; fail=1
  fi
done
[ $fail -eq 1 ] && { echo; echo "Fix the error above, then run again."; exit 1; }

$PY - <<'CHECK'
import collections, glob, os, re, subprocess, sys
sys.path.insert(0, "cv")
import cvlib as cv

ME = os.environ["JOBKIT_ME"]
DATA = sorted(glob.glob(os.path.join(ME, "cv-data", "*.py")))
problems = []

# A missing space at a Python string join silently glues two words together.
for f in DATA + [os.path.join(ME, "profile.py")]:
    L = open(f).read().split("\n")
    for i in range(len(L) - 1):
        a, b = L[i].rstrip(), L[i + 1].strip()
        ma, mb = re.search(r'"([^"]*)"$', a), re.match(r'"([^"]*)"', b)
        if ma and mb and not a.endswith(('",', '"),', '")', '"]')):
            l, r = ma.group(1), mb.group(1)
            if l and r and not l.endswith(" ") and not r.startswith(" "):
                problems.append(f"glued string {os.path.basename(f)}:{i+1} ...{l[-25:]!r} + {r[:25]!r}")

# An override that equals the default is a copy waiting to go stale.
flat = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
defaults = {j["key"]: flat("".join(j["bullets"])) for j in cv.JOBS[1:]}
for f in DATA:
    spec = __import__("importlib.util").util.spec_from_file_location("d", f)
    m = __import__("importlib.util").util.module_from_spec(spec); spec.loader.exec_module(m)
    for k, v in (getattr(m, "OVERRIDES", None) or {}).items():
        if flat("".join(v)) == defaults.get(k):
            problems.append(f"pointless override {os.path.basename(f)}: {k} equals the default")

pdfs = sorted({mm.group(1) for f in DATA
               for mm in [re.search(r'^OUT = "([^"]+\.pdf)"', open(f).read(), re.M)] if mm})
path = lambda f: os.path.join(cv.OUT_DIR, f)
run = lambda *a: subprocess.run(list(a), capture_output=True, text=True).stdout
text = {f: run("pdftotext", "-layout", path(f), "-").replace("\f", "\n") for f in pdfs}

print("  CV                                          pages  fill   p2   dupes")
for f in pdfs:
    p = int(re.search(r"Pages:\s+(\d+)", run("pdfinfo", path(f))).group(1))
    ys = [float(y) for y in re.findall(r'yMax="([0-9.]+)"', run("pdftotext", "-bbox", "-f", "1", "-l", "1", path(f), "-"))]
    fl = max(ys) / 814 * 100 if ys else 0
    w = re.findall(r"[a-z0-9%+/&-]+", re.sub(r"\s+", " ", text[f].lower()))
    d = [x for x, c in collections.Counter(" ".join(w[i:i+6]) for i in range(len(w) - 5)).items() if c > 1]
    n2 = len([l for l in run("pdftotext", "-f", "2", "-l", "2", path(f), "-").split("\n") if l.strip()]) if p == 2 else 0
    flag = ""
    if p > 2: flag += " <- TOO LONG"; problems.append(f"{f}: {p} pages")
    elif p == 2 and n2 < 6: flag += " <- page 2 is a stub"
    if p == 1 and fl < 88: flag += " <- looks thin"
    if d: problems.append(f"{f}: {len(d)} repeated 6-word phrases")
    print(f"  {f[:-4]:<42} {p:>3}   {fl:>4.0f}%  {n2:>3}   {len(d):>4}{flag}")
    for x in d[:3]: print(f"        repeated: {x}")
    if re.search("[\u2013\u2014]", text[f]): problems.append(f"{f}: has an en or em dash")
    for tool in cv.BANNED:
        if re.search(r"\b" + re.escape(tool.lower()) + r"\b", text[f].lower()):
            problems.append(f"{f}: banned tool {tool!r} is on the page")

print()
print("  ALL GOOD" if not problems else "  PROBLEMS:\n    " + "\n    ".join(problems))
sys.exit(1 if problems else 0)
CHECK
