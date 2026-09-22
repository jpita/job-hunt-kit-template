#!/usr/bin/env python3
"""What to fix in rules.py, grouped by the reason that misfired.

  python3 rules_queue.py                 open reports, worst reason first
  python3 rules_queue.py --all           closed ones too
  python3 rules_queue.py --done "<reason>"   close every report on that reason

One reason string usually explains many rows, so one fix clears the group.
That is why the queue is grouped by reason and not by job.
"""
import collections, sys

import rule_reports


def show(items, show_all):
    open_items = [i for i in items if i.get("open") or show_all]
    if not open_items:
        print("  nothing reported")
        return

    by_reason = collections.defaultdict(list)
    for it in open_items:
        # A report with no reason at all is its own group: the row landed
        # somewhere with nothing said against it.
        for r in it.get("reasons") or ["(no reason recorded)"]:
            by_reason[r].append(it)

    print(f"  {len(open_items)} report(s), {len(by_reason)} distinct reason(s)\n")
    for reason, group in sorted(by_reason.items(),
                                key=lambda kv: -len(kv[1])):
        where = collections.Counter(i["bucket_now"] for i in group)
        print(f'  {len(group):>3}x  {reason}')
        print(f'        now in: '
              + ", ".join(f"{b} ({n})" for b, n in where.most_common()))
        for i in group:
            state = "" if i.get("open") else " [closed]"
            print(f'        {i["company"]} \u00b7 {i["title"][:58]}{state}')
            print(f'        {i["url"]}')
            # Your words are the reason to read this queue at all, so they
            # print in full and never get truncated into a summary.
            if i.get("expected"):
                print(f'        belongs in: {i["expected"]}')
            if i.get("note"):
                for line in i["note"].splitlines():
                    print(f'        > {line}')
            if not i.get("note") and not i.get("expected"):
                print('        > no words given, so there is nothing to act on')
        print()


def main():
    args = sys.argv[1:]
    items = rule_reports.load()
    if "--done" in args:
        i = args.index("--done")
        if i + 1 >= len(args):
            sys.exit(__doc__)
        reason = args[i + 1]
        n = rule_reports.resolve(reason)
        print(f"closed {n} report(s) on: {reason}")
        return
    show(items, "--all" in args)


if __name__ == "__main__":
    main()
