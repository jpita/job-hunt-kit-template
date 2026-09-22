#!/usr/bin/env python3
"""Record your verdict on a job, so the rules can be corrected against it.

  python3 mark.py good <url> [note]    this one was worth seeing
  python3 mark.py bad  <url> [note]    this one was noise
  python3 mark.py applied <url>        applied, hide it from the live lists
  python3 mark.py wont <url> [note]    will not apply, hide it
  python3 mark.py open <url>           undo applied or wont
  python3 mark.py list                 everything marked so far

The same store the report's checkboxes write to, so a click and a command
cannot disagree. The marks show on the report and are the evidence for
changing rules.py. A rule change is only justified when a mark disagrees with
the bucket it landed in.
"""
import sys

import marks


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] == "list":
        store = marks.load()
        for u, v in store.items():
            bits = [v["verdict"], v["state"]]
            print(f'  {"/".join(b for b in bits if b) or "-":<14} {u}'
                  + (f'  {v["note"]}' if v["note"] else ""))
        handled = len([v for v in store.values() if marks.is_handled(v)])
        print(f"  {len(store)} marked, {handled} handled")
        return

    cmd, rest = argv[0], argv[1:]
    if not rest:
        sys.exit(__doc__)
    url, note = rest[0], " ".join(rest[1:])

    if cmd in ("good", "bad"):
        fields = {"verdict": cmd}
    elif cmd in ("applied", "wont"):
        fields = {"state": cmd}
    elif cmd == "open":
        fields = {"state": ""}
    else:
        sys.exit(__doc__)
    if note:
        fields["note"] = note

    entry = marks.set_fields(url, **fields)
    print(f'{cmd}: {url}')
    print(f'  verdict={entry["verdict"] or "-"} state={entry["state"] or "-"}')


if __name__ == "__main__":
    main()
