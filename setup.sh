#!/bin/bash
# One-time setup. Safe to run again: it never overwrites files in me/.
set -u
KIT="$(cd "$(dirname "$0")" && pwd)"
cd "$KIT" || exit 1

mkdir -p me
for f in $(cd templates/me && find . -type f); do
  [ -e "me/$f" ] || { mkdir -p "me/$(dirname "$f")"; cp "templates/me/$f" "me/$f"; echo "created me/${f#./}"; }
done

mkdir -p ~/.claude/skills
if [ -L ~/.claude/skills/job-fit ] || [ ! -e ~/.claude/skills/job-fit ]; then
  ln -sfn "$KIT/skills/job-fit" ~/.claude/skills/job-fit
  echo "linked ~/.claude/skills/job-fit"
else
  echo "~/.claude/skills/job-fit exists and is not a link. Left it alone."
fi

# A private Python for the CV builder. Homebrew Python refuses a global pip install.
if [ ! -x me/.venv/bin/python ]; then
  python3 -m venv me/.venv && me/.venv/bin/pip install -q reportlab && echo "created me/.venv with reportlab"
fi
me/.venv/bin/python -c "import reportlab" 2>/dev/null && echo "ok reportlab" || echo "MISSING reportlab in me/.venv"
command -v pdftotext >/dev/null && echo "ok pdftotext" || echo "MISSING pdftotext: brew install poppler"
command -v claude >/dev/null && echo "ok claude" || echo "MISSING claude CLI"
