#!/usr/bin/env python3
"""One report from both scanners.

  board-seen.json    every posting on the 750+ boards in companies.txt
  google-seen.json   every job page Google returned for the role keywords

Neither source is a superset of the other. Measured once: the board
sweep found 6 clean roles, Google found 4, and only one was in both. So both
run, and this merges them.

Nothing is hidden. Every job either scanner saw appears here, tagged with where
it came from and the day it first showed up.
"""
import json, pathlib, datetime, html

import config

import judge
import marks as feedback
import rank
import rule_reports
import rules
import runlog

HERE = config.STATE
OUT = HERE / "report.html"
OUT_NO = HERE / "report-rejected.html"
BOARD = HERE / "board-seen.json"
GOOGLE = HERE / "google-seen.json"

GEO = ("location:", "board says country", "body says based in")
OFF_TITLE = f"title is not a {config.TARGET_LABEL}"



# A report is only as fresh as the scan behind it. Anything older than two
# days is called out, and a failure newer than the last success is called out
# loudest: a regenerated file must never read as a successful search.
STALE_WARN, STALE_BAD = 2, 4
BOARD_LOG = HERE / "boards-read.json"
# Every board should be read once a week. Two rotations without one means it
# is failing quietly, because a board that never answers never gets a date.
BOARD_STALE = 15


def stale_boards(today):
    """(how many boards are overdue, the worst gap in days)."""
    try:
        log = json.loads(BOARD_LOG.read_text())
    except (OSError, json.JSONDecodeError):
        return 0, None
    gaps = [g for g in (runlog.age_days(d, today) for d in log.values())
            if g is not None]
    if not gaps:
        return 0, None
    return len([g for g in gaps if g > BOARD_STALE]), max(gaps)


def health(today):
    """One row per source: what it says, and how alarming it is."""
    items, worst = [], "ok"
    rank = {"ok": 0, "warn": 1, "bad": 2}

    for kind, label in (("boards", "Direct board scan"), ("google", "Google scan")):
        ok_run = runlog.last(kind, ok_only=True)
        any_run = runlog.last(kind, ok_only=False)
        age = runlog.age_days(ok_run.get("when"), today)

        if age is None:
            state, when = "bad", "never completed"
        else:
            state = ("ok" if age <= 1 else
                     "warn" if age < STALE_BAD else "bad")
            when = ("today" if age == 0 else "yesterday" if age == 1
                    else f"{age} days ago")
            if age >= STALE_WARN:
                state = "warn" if age < STALE_BAD else "bad"

        note = ""
        # A failure the success does not cover is the thing worth shouting.
        if any_run and not any_run.get("ok") and (
                not ok_run or any_run["when"] > ok_run["when"]):
            state = "bad"
            note = any_run.get("why") or "last attempt failed"
        elif kind == "boards":
            # "the scan ran today" is not "the boards are fresh": rotation
            # reads a seventh of them, so a board can be a week behind and a
            # permanently failing one never gets read at all.
            stale, oldest = stale_boards(today)
            bits = []
            if ok_run.get("boards_failed"):
                bits.append(f'{ok_run["boards_failed"]} of '
                            f'{ok_run["boards_failed"] + ok_run.get("boards_ok", 0)} '
                            f'did not answer')
            if stale:
                state = "warn" if state == "ok" else state
                bits.append(f"{stale} board(s) unread for {oldest} days")
            elif oldest is not None:
                bits.append(f"every board read within {oldest} days")
            note = ", ".join(bits)
        elif kind == "google" and ok_run.get("read_ok") is not None:
            note = (f'{ok_run["read_ok"]} of {ok_run.get("urls_in", 0)} '
                    f'job pages could be read')

        items.append(dict(label=label, when=when, note=note, state=state,
                          stamp=(ok_run.get("when") or "")[:16].replace("T", " ")))
        if rank[state] > rank[worst]:
            worst = state
    return items, worst


def health_html(today):
    items, worst = health(today)
    cells = "".join(
        f'<div class="hcell {i["state"]}"><span class="hlabel">{i["label"]}</span>'
        f'<span class="hwhen">{html.escape(i["when"])}</span>'
        f'<span class="hnote">{html.escape(i["note"] or i["stamp"] or "")}</span></div>'
        for i in items)
    words = {"ok": "Both scans are current",
             "warn": "One scan is falling behind",
             "bad": "This page is not backed by a fresh search"}
    return (f'<section class="health {worst}">'
            f'<div class="hverdict">{words[worst]}</div>{cells}</section>')


def row_for(url):
    """One row by url, or {}. serve.py uses it so a wrong-bucket report
    records the reasons the report actually shows, not what a page sent."""
    for r in load():
        if r["url"] == url:
            return r
    return {}


def bucket_of(hard, soft):
    """judge.py decides this, so the page and the scanners cannot disagree."""
    return judge.bucket_for(hard, soft)


def load():
    """Both history files, normalised to one row shape, merged by URL."""
    marks = feedback.load()
    rows = {}

    if BOARD.exists():
        for url, v in json.loads(BOARD.read_text()).items():
            hard, soft = v.get("blocked", []), v.get("check", [])
            closed = v.get("closed", "")
            rows[url] = dict(
                company=v.get("company", "?"), title=v.get("title", ""), url=url,
                hard=hard, soft=soft,
                # The board no longer lists it. That outranks every other
                # verdict: a role you cannot apply to is not worth reviewing.
                bucket="closed" if closed else bucket_of(hard, soft),
                first_seen=v.get("date", ""), sources={"boards"},
                pay=v.get("pay", ""), posted=v.get("posted", ""),
                loc=v.get("loc", ""), home=bool(v.get("home")),
                moved_from=v.get("moved_from", ""), moved_on=v.get("moved_on", ""),
                closed=closed, alt_url=v.get("alt_url", ""),
                link_broken=v.get("link_broken", ""))

    if GOOGLE.exists():
        for r in json.loads(GOOGLE.read_text()):
            url = r["url"]
            if url in rows:
                rows[url]["sources"].add("google")
                if not rows[url].get("alt_url"):
                    rows[url]["alt_url"] = r.get("alt_url", "")
                if not rows[url].get("pay"):
                    rows[url]["pay"] = r.get("pay", "")
                if not rows[url].get("loc"):
                    rows[url]["loc"] = r.get("loc", "")
                rows[url]["home"] = (rows[url].get("home")
                                      or bool(r.get("home")))
                google_posted = r.get("posted", "")
                if google_posted and (not rows[url].get("posted")
                                      or google_posted < rows[url]["posted"]):
                    rows[url]["posted"] = google_posted
                # Keep the earlier sighting.
                if r["first_seen"] and r["first_seen"] < rows[url]["first_seen"]:
                    rows[url]["first_seen"] = r["first_seen"]
            else:
                rows[url] = dict(
                    company=r["company"], title=r["title"], url=url,
                    hard=r["hard"], soft=r["soft"], bucket=r["bucket"],
                    first_seen=r["first_seen"], sources={"google"},
                    pay=r.get("pay", ""), posted=r.get("posted", ""),
                    loc=r.get("loc", ""), home=bool(r.get("home")),
                    moved_from=r.get("moved_from", ""),
                    moved_on=r.get("moved_on", ""),
                    closed=r.get("closed", ""), alt_url=r.get("alt_url", ""),
                    link_broken=r.get("link_broken", ""))
    reported = {}
    for i in rule_reports.load():
        if i.get("open"):
            reported[i["url"]] = i.get("note", "")
    for url, r in rows.items():
        r["reported"] = url in reported
        r["reported_note"] = reported.get(url, "")
        # A row you have disputed is not clean. It waits under Reported until
        # the rule behind it is fixed, so it stops competing for attention.
        if r["reported"]:
            r["bucket"] = "reported"
        m = marks.get(url) or {}
        r["mark"] = m.get("verdict", "")
        r["state"] = m.get("state", "")
        r["note"] = m.get("note", "")
        # A job you have dealt with leaves the live lists. Your own decision
        # outranks every rule, and a closed board listing.
        if feedback.is_handled(m):
            r["bucket"] = "handled"
    return list(rows.values())


CSS = r"""
:root{
 --ink:#090d10;--ink-2:#0d1318;--panel:#11191f;--panel-2:#152027;
 --paper:#edf1eb;--muted:#849098;--faint:#58646c;--line:#243139;
 --acid:#b8f06a;--sky:#8ecbff;--amber:#f4bd67;--coral:#ff8f78;
 --violet:#c2a7ff;--shadow:0 24px 70px rgba(0,0,0,.28)
}
*{box-sizing:border-box}
html{color-scheme:dark;scroll-behavior:smooth}
body{margin:0;background:
 radial-gradient(900px 540px at 92% -10%,rgba(79,145,165,.16),transparent 62%),
 radial-gradient(760px 500px at -8% 18%,rgba(184,240,106,.07),transparent 65%),
 var(--ink);color:var(--paper);font:14px/1.45 "Avenir Next",Avenir,"Segoe UI",sans-serif;
 min-height:100vh}
body::before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.035;
 background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 160 160' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.7'/%3E%3C/svg%3E")}
.page{width:min(1560px,calc(100% - 40px));margin:0 auto;padding:42px 0 64px}
.masthead{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(420px,.8fr);gap:36px;
 align-items:end;padding:30px 32px 28px;border:1px solid var(--line);border-radius:20px;
 background:linear-gradient(145deg,rgba(20,31,38,.96),rgba(11,17,21,.96));box-shadow:var(--shadow);
 overflow:hidden;position:relative}
.masthead::after{content:"";position:absolute;width:260px;height:260px;border:1px solid rgba(184,240,106,.16);
 border-radius:50%;right:-90px;top:-130px;box-shadow:0 0 0 38px rgba(184,240,106,.025),0 0 0 76px rgba(184,240,106,.018)}
.eyebrow{color:var(--acid);font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;margin-bottom:12px}
h1{font:600 clamp(38px,5vw,68px)/.98 "Iowan Old Style","Palatino Linotype",Georgia,serif;
 letter-spacing:-.045em;margin:0;max-width:780px}
.lede{color:var(--muted);font-size:15px;margin:16px 0 0;max-width:640px}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;position:relative;z-index:1}
.stat{background:rgba(8,13,16,.62);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-height:82px}
.stat-value{display:block;font:600 27px/1 "Iowan Old Style",Georgia,serif;letter-spacing:-.03em}
.stat-label{display:block;color:var(--muted);font-size:10px;font-weight:700;letter-spacing:.13em;text-transform:uppercase;margin-top:8px}
.stat.hot .stat-value{color:var(--acid)}
.source-line{grid-column:1/-1;color:var(--muted);font-size:12px;padding:5px 3px 0}
.source-line strong{color:var(--paper);font-weight:600}
.bar{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:8px;margin:18px 0 12px;
 padding:10px;background:rgba(9,13,16,.82);border:1px solid rgba(36,49,57,.9);border-radius:14px;
 backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
.search{flex:1;min-width:160px;position:relative}
.search::before{content:"⌕";position:absolute;left:13px;top:7px;color:var(--faint);font-size:19px}
.search input{width:100%;height:38px;background:var(--panel);border:1px solid transparent;border-radius:9px;
 color:var(--paper);padding:0 13px 0 38px;font:inherit;outline:none;transition:.18s ease}
.search input:focus{border-color:#52636d;background:var(--panel-2);box-shadow:0 0 0 3px rgba(142,203,255,.08)}
.search input::placeholder{color:#68747b}
.bar button{height:38px;background:transparent;color:var(--muted);border:1px solid var(--line);border-radius:9px;
 padding:0 13px;font:600 11px/1 "Avenir Next",sans-serif;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;transition:.18s ease}
.bar button:hover{color:var(--paper);border-color:#53626a;background:var(--panel)}
.results{display:grid;gap:12px}
details{--section:var(--sky);border:1px solid var(--line);border-radius:16px;background:rgba(13,19,24,.82);overflow:hidden}
details.clean{--section:var(--acid)} details.check{--section:var(--amber)}
details.country{--section:var(--sky)} details.blocked{--section:var(--coral)} details.failed{--section:var(--violet)}
details.reported{--section:var(--violet)}
details.closed{--section:#7c8a93} details.closed .role a{color:#9aa7ad}
summary{display:grid;grid-template-columns:34px minmax(150px,.7fr) minmax(220px,1.5fr) auto;gap:12px;
 align-items:center;list-style:none;cursor:pointer;user-select:none;padding:17px 20px;transition:background .18s ease}
summary::-webkit-details-marker{display:none} summary:hover{background:rgba(255,255,255,.018)}
.chev{display:grid;place-items:center;width:28px;height:28px;border:1px solid var(--line);border-radius:8px;color:var(--section);transition:transform .2s ease}
details[open] .chev{transform:rotate(90deg)}
.section-name{font:600 18px/1.1 "Iowan Old Style",Georgia,serif;letter-spacing:-.01em}
.section-note{color:var(--muted);font-size:12px}
.count{justify-self:end;color:var(--section);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
 border:1px solid color-mix(in srgb,var(--section) 32%,transparent);border-radius:999px;padding:5px 9px}
.scroll{max-height:690px;overflow:auto;border-top:1px solid var(--line);background:rgba(7,11,14,.48)}
.scroll::-webkit-scrollbar{width:8px;height:8px}.scroll::-webkit-scrollbar-thumb{background:#35434b;border-radius:20px}.scroll::-webkit-scrollbar-track{background:transparent}
.job-head,.job{display:grid;grid-template-columns:minmax(86px,.65fr) minmax(250px,2.15fr) minmax(150px,1.15fr) minmax(100px,.7fr) 70px 82px 88px 118px;
 gap:16px;align-items:start;padding-left:20px;padding-right:20px}
.job-head{position:sticky;top:0;z-index:2;padding-top:9px;padding-bottom:8px;background:#10181d;color:var(--faint);
 font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;border-bottom:1px solid var(--line)}
.job{padding-top:13px;padding-bottom:13px;border-bottom:1px solid rgba(36,49,57,.72);position:relative;transition:background .16s ease}
.job:last-child{border-bottom:0}.job:hover{background:rgba(255,255,255,.025)}
.job.fresh{background:linear-gradient(90deg,rgba(184,240,106,.07),transparent 46%)}
.job.fresh::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--acid)}
.co{color:#a7b0b5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;font-weight:650;text-transform:lowercase;padding-top:2px}
.role a{color:#dfe9f0;text-decoration:none;font-size:14px;font-weight:600;letter-spacing:-.005em}
.role a:hover{color:var(--sky)}
.why{color:#c9a969;font-size:11px;line-height:1.4}.pay{color:#9fd58c;font-size:11px;line-height:1.4}
.posted,.seen{color:#738087;font-size:10px;white-space:nowrap;padding-top:3px;font-variant-numeric:tabular-nums}
.posted{color:#9aa7ad}
.empty{color:var(--muted);padding:24px 20px;font-family:"Iowan Old Style",Georgia,serif;font-style:italic}
.new,.mark,.dupe,.tag{display:inline-flex;align-items:center;border-radius:999px;font-size:9px;font-weight:750;line-height:1;
 letter-spacing:.06em;text-transform:uppercase;padding:4px 7px;vertical-align:2px;white-space:nowrap}
.new{background:var(--acid);color:#142006;margin-right:6px}.mark{margin-right:6px}
.mark.good{background:#276657;color:#d7fff2}.mark.bad{background:#713a3b;color:#ffe1dd}
.dupe{background:#293139;color:#bdc7cd;margin-left:7px}.also{display:block;color:var(--faint);font-size:10px;margin-top:5px}
.also a{color:#809dac;margin-right:7px;font-size:10px}.src{font-size:10px;white-space:nowrap;padding-top:1px}
.tag.g{background:#203b51;color:#abd8ff}.tag.b{background:#493b22;color:#f0cc85}.tag.both{background:#3c3054;color:#d8c3ff}
.health{display:grid;grid-template-columns:minmax(200px,.9fr) repeat(2,minmax(180px,1fr));gap:1px;
 margin:14px 0 0;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--line)}
.health>*{background:rgba(13,19,24,.92);padding:13px 16px}
.hverdict{display:flex;align-items:center;font:600 14px/1.25 "Iowan Old Style",Georgia,serif;letter-spacing:-.01em}
.health.ok .hverdict{color:var(--acid)}.health.warn .hverdict{color:var(--amber)}
.health.bad .hverdict{color:var(--coral)}
.health.bad{border-color:rgba(255,143,120,.45)}
.hcell{display:grid;gap:3px;border-left:2px solid transparent}
.hcell.ok{border-left-color:var(--acid)}.hcell.warn{border-left-color:var(--amber)}
.hcell.bad{border-left-color:var(--coral)}
.hlabel{color:var(--faint);font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.hwhen{font-size:14px;font-weight:600}
.hcell.warn .hwhen{color:var(--amber)}.hcell.bad .hwhen{color:var(--coral)}
.hnote{color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
@media(max-width:720px){.health{grid-template-columns:1fr}}
.act{display:flex;flex-wrap:wrap;gap:4px;padding-top:1px}
.act button{background:transparent;color:var(--faint);border:1px solid var(--line);border-radius:7px;
 padding:4px 7px;font:700 9px/1 "Avenir Next",sans-serif;letter-spacing:.07em;text-transform:uppercase;
 cursor:pointer;transition:.15s ease;white-space:nowrap}
.act button:hover{color:var(--paper);border-color:#53626a;background:var(--panel)}
.act button.applied:hover{color:#a9f3c9;border-color:#2f7a5c}
.act button.wont:hover{color:#ffc0b4;border-color:#8a4a44}
.act button:disabled{opacity:.4;cursor:default}
.job.going{opacity:.25;transition:opacity .25s ease}
.mark.applied{background:#22614f;color:#c8fce8}.mark.wont{background:#5c4038;color:#ffd9cf}
.note{display:block;color:var(--faint);font-size:10px;font-style:italic;margin-top:4px}
.toast{position:fixed;left:50%;bottom:26px;transform:translate(-50%,14px);z-index:40;
 background:#11191f;border:1px solid var(--line);border-radius:10px;padding:10px 15px;
 font-size:12px;color:var(--paper);box-shadow:var(--shadow);opacity:0;pointer-events:none;
 transition:.22s ease}
.toast.show{opacity:1;transform:translate(-50%,0)}
.toast.bad{border-color:rgba(255,143,120,.6);color:#ffc0b4}
.offline{margin:14px 0 0;padding:11px 15px;border:1px solid rgba(244,189,103,.45);border-radius:12px;
 background:rgba(244,189,103,.07);color:var(--amber);font-size:12px}
.act button.flag:hover{color:#d8c3ff;border-color:#6b5a93}
.act select.expect{background:var(--panel);color:var(--paper);border:1px solid #53626a;
 border-radius:7px;font:600 10px/1 "Avenir Next",sans-serif;padding:4px 5px;max-width:112px;cursor:pointer}
.mark.flagged{background:#3c3054;color:#d8c3ff}
.fb{grid-column:1/-1;display:grid;gap:7px;margin-top:11px;padding:12px;
 border:1px solid #5b4a7d;border-radius:11px;background:rgba(60,48,84,.22)}
.fb textarea{width:100%;background:var(--ink-2);color:var(--paper);border:1px solid var(--line);
 border-radius:8px;padding:9px 11px;font:13px/1.45 inherit;resize:vertical;outline:none}
.fb textarea:focus{border-color:#7a68a3;box-shadow:0 0 0 3px rgba(194,167,255,.09)}
.fb textarea::placeholder{color:#6d7880}
.fbrow{display:flex;align-items:center;gap:8px}
.fbhint{flex:1;color:var(--faint);font-size:10px;letter-spacing:.04em}
.fb button{height:29px;background:transparent;color:var(--muted);border:1px solid var(--line);
 border-radius:8px;padding:0 12px;font:700 10px/1 "Avenir Next",sans-serif;letter-spacing:.07em;
 text-transform:uppercase;cursor:pointer;transition:.15s ease}
.fb button.send{color:#d8c3ff;border-color:#6b5a93}
.fb button.send:hover{background:rgba(194,167,255,.12)}
.fb button.cancel:hover{color:var(--paper);border-color:#53626a}
.fb button:disabled{opacity:.45;cursor:default}
.note.said{color:#b9a7d9}
.note.moved{color:#9fb4c4}
.note.link{color:#f4bd67;font-style:normal}.note.link a{color:var(--sky)}
details.notqa{--section:#6f7a82} details.notqa .role a{color:#a2adb4}
details.level{--section:#8ecbff} details.role{--section:#9aa7ad}
details.role .role a{color:#aeb9c0}
.chips{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 12px;padding:0 2px}
.chips button{background:transparent;color:var(--muted);border:1px solid var(--line);border-radius:999px;
 padding:5px 11px;font:650 10px/1 "Avenir Next",sans-serif;letter-spacing:.06em;text-transform:uppercase;
 cursor:pointer;transition:.15s ease}
.chips button:hover{color:var(--paper);border-color:#53626a}
.chips button.on{background:var(--acid);color:#142006;border-color:var(--acid)}
.chipnote{color:var(--faint);font-size:11px;margin-left:4px}
.pts{display:inline-block;margin-left:6px;padding:1px 5px;border:1px solid var(--line);border-radius:6px;
 color:var(--muted);font-size:10px;font-weight:700;font-variant-numeric:tabular-nums}
.job:hover .pts{border-color:#53626a;color:var(--paper)}
@media(max-width:720px){.chips{gap:5px}.chips button{padding:5px 9px;font-size:9px}}
.jump{display:grid;grid-template-columns:34px minmax(150px,.7fr) minmax(220px,1.5fr) auto;gap:12px;
 align-items:center;padding:17px 20px;border:1px solid var(--line);border-radius:16px;
 background:rgba(13,19,24,.82);text-decoration:none;color:var(--paper);transition:.18s ease}
.jump:hover{background:rgba(255,255,255,.03);border-color:#53626a}
.jump .chev{color:var(--sky)}
.jump .count{justify-self:end;color:var(--sky);font-size:11px;font-weight:700;letter-spacing:.08em;
 text-transform:uppercase;border:1px solid color-mix(in srgb,var(--sky) 32%,transparent);
 border-radius:999px;padding:5px 9px}
@media(max-width:720px){.jump{grid-template-columns:30px 1fr auto;padding:15px}
 .jump .section-note{display:none}}
.hidden{display:none!important}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.masthead,.bar,.results>details{animation:rise .5s both}.bar{animation-delay:.06s}.results>details:nth-child(1){animation-delay:.1s}
.results>details:nth-child(2){animation-delay:.14s}.results>details:nth-child(3){animation-delay:.18s}
@media(max-width:1050px){.masthead{grid-template-columns:1fr}.stats{grid-template-columns:repeat(4,1fr)}.source-line{grid-column:1/-1}
 .job-head{display:none}.job{grid-template-columns:110px minmax(240px,1.6fr) minmax(160px,1fr) 90px}.job .act{grid-row:2;grid-column:1}.job .src,.job .posted,.job .seen{grid-row:2}.job .src{grid-column:2}.job .posted{grid-column:3}.job .seen{grid-column:4}}
@media(max-width:720px){.page{width:min(100% - 22px,1560px);padding-top:12px}.masthead{padding:24px 20px;border-radius:15px}.stats{grid-template-columns:repeat(2,1fr)}
 .bar{flex-wrap:wrap}.search{flex-basis:100%}.bar button{flex:1}summary{grid-template-columns:30px 1fr auto;padding:15px}.section-note{display:none}
 .job{grid-template-columns:1fr;gap:7px;padding:15px 16px}.job .co,.job .role,.job .why,.job .pay,.job .src,.job .posted,.job .seen,.job .act{grid-column:1;grid-row:auto}.co{color:var(--muted)} }
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
"""

SECTIONS = [
    ("clean", "Clean", "nothing against them"),
    ("check", "Worth a glance", "right role, only the arrangement is unclear"),
    ("level", "One level down", f"a real {config.ROLE_NOUN}, below the level you want"),
    ("role", "Wrong kind of role", f"not a {config.ROLE_NOUN}"),
    ("reported", "Reported", "you said the bucket is wrong, waiting on a rules fix"),
    ("failed", "Could not read", "likely closed, still listed by Google"),
    ("handled", "Handled", "applied, or you decided against it"),
    ("country", "Wrong country", "tied to a place you cannot work from"),
    ("blocked", "Legally impossible", "US persons, clearance, US-only"),
    ("closed", "Archived", "the board stopped listing it"),

    ("notqa", f"Not a {config.ROLE_NOUN}", "the title does not match your role"),
]
# Keep SECTIONS in the order they should be read, not the order they grew in.
_ORDER = ["clean", "check", "level", "role", "reported", "failed",
          "country", "blocked", "notqa", "handled", "closed"]
SECTIONS = sorted(SECTIONS, key=lambda x: _ORDER.index(x[0]))

# Only what you have finished with leaves the main page: a posting the board
# took down, and one you have applied to or ruled out yourself. Everything else
# stays in front of you, because you tag these by hand and a row you cannot
# see is a row you cannot correct.
REJECTED = {"closed", "handled"}
MAIN = [x for x in SECTIONS if x[0] not in REJECTED]
ASIDE = [x for x in SECTIONS if x[0] in REJECTED]


def variant_label(r):
    """The word that tells one listing of a role apart from its twins."""
    for h in r["hard"] + r["soft"]:
        if h.startswith("board says country "):
            return h.rsplit(" ", 1)[1]
        if h.startswith(("location: ", "location unclear: ")):
            return h.split(": ", 1)[1][:22]
    return "listing"


def group_dupes(items):
    """One row per role. The same job posted per country is one role.

    Nothing is dropped: every other listing hangs off the row as a link.
    """
    groups = {}
    for r in items:
        groups.setdefault((r["company"], r["title"].strip().lower()), []).append(r)
    out = []
    for g in groups.values():
        # Prefer a listing that carries pay, then the earliest sighting.
        g.sort(key=lambda x: (not x.get("pay"), x["first_seen"]))
        head = dict(g[0])
        head["dupes"] = g[1:]
        seen = [x["first_seen"] for x in g if x["first_seen"]]
        if seen:
            head["first_seen"] = min(seen)
        posted = [x.get("posted", "") for x in g if x.get("posted")]
        if posted:
            head["posted"] = min(posted)
        out.append(head)
    return out


def dupe_bits(r):
    """A count badge plus a link to every other listing of the same role."""
    d = r.get("dupes") or []
    if not d:
        return ""
    links = " ".join(
        f'<a href="{html.escape(x["url"])}" target="_blank">'
        f'{html.escape(variant_label(x))}</a>' for x in d)
    return (f'<span class="dupe">&times;{len(d) + 1}</span>'
            f'<span class="also">also: {links}</span>')


def src_tag(s):
    if s == {"boards", "google"}:
        return '<span class="tag both">both</span>'
    if s == {"google"}:
        return '<span class="tag g">google</span>'
    return '<span class="tag b">boards</span>'



def actions(r):
    """The buttons on one row. They post to serve.py, which owns the writes."""
    u = html.escape(r["url"], quote=True)
    if r.get("state") in ("applied", "wont"):
        return f'<button data-mark="" data-url="{u}">reopen</button>'
    return (f'<button class="applied" data-mark="applied" data-url="{u}">applied</button>'
            f'<button class="wont" data-mark="wont" data-url="{u}">won\'t</button>'
            f'<button class="flag" data-flag="{u}">wrong</button>')


def feedback_box(r):
    """Where you say in your own words what is wrong with this row.

    A picker could only say which bucket. The reasons that put it there are
    captured by serve.py, so the words are the part only you can supply.
    """
    u = html.escape(r["url"], quote=True)
    return (f'<form class="fb hidden" data-url="{u}">'
            f'<textarea rows="2" placeholder="What is wrong with this one? '
            f'Plain words. I read these and change rules.py." '
            f'aria-label="what is wrong with this row"></textarea>'
            f'<div class="fbrow"><span class="fbhint">cmd + enter to send</span>'
            f'<button type="button" class="cancel">cancel</button>'
            f'<button type="submit" class="send">send</button></div></form>')


def render(rows, today, sections=None, aside=True):
    def table(items):
        if not items:
            return '<div class="empty">none in this category</div>'
        items = group_dupes(items)
        # Best first. Bucketing says whether you can apply; this says which to
        # read first, and a 600-day-old evergreen posting is not it.
        items = sorted(items, key=rank.sort_key)
        out = []
        for r in items:
            fresh = r["first_seen"] == today
            why = html.escape("; ".join(r["hard"] + r["soft"]))
            if r.get("closed"):
                why = f'closed {r["closed"]}' + (f' &middot; {why}' if why else "")
            tag = '<span class="new">NEW</span>' if fresh else ""
            if r.get("mark") == "good":
                tag = '<span class="mark good">GOOD</span>' + tag
            elif r.get("mark") == "bad":
                tag = '<span class="mark bad">NO</span>' + tag
            if r.get("reported"):
                tag = '<span class="mark flagged">REPORTED</span>' + tag
            if r.get("state") == "applied":
                tag = '<span class="mark applied">APPLIED</span>' + tag
            elif r.get("state") == "wont":
                tag = '<span class="mark wont">WON\'T</span>' + tag
            when = "today" if fresh else r["first_seen"]
            note = (f'<span class="note">{html.escape(r["note"])}</span>'
                    if r.get("note") else "")
            # The board publishes some postings on the company's own domain,
            # and that URL rots while the posting stays open. Say which link
            # to click rather than leaving you to find the dead one.
            if r.get("alt_url"):
                note += (f'<span class="note link">the board link is dead &middot; '
                         f'<a href="{html.escape(r["alt_url"])}" target="_blank" '
                         f'rel="noopener">open it here</a></span>')
            elif r.get("link_broken"):
                note += ('<span class="note link">no working link, the board '
                         'lists it but every page 404s</span>')
            if r.get("moved_from"):
                was = dict((k, n) for k, n, _ in SECTIONS).get(
                    r["moved_from"], r["moved_from"])
                note += (f'<span class="note moved">was in {html.escape(was)} '
                         f'until {html.escape(r["moved_on"])}</span>')
            if r.get("reported_note"):
                note += (f'<span class="note said">reported: '
                         f'{html.escape(r["reported_note"])}</span>')
            # Not "why": that is the review note, and rank's reasons are the
            # ordering, which belongs in the score tooltip only.
            points, ranked = rank.score(r)
            age = rank.age_days(r)
            attrs = (f' data-score="{points}" data-age="{age if age is not None else -1}"'
                     f' data-pay="{1 if r.get("pay") else 0}"'
                     f' data-home="{1 if (r.get("home") or rank.HOME.search(r.get("loc") or "")) else 0}"'
                     f' data-src="{"both" if len(r["sources"]) == 2 else next(iter(r["sources"]))}"'
                     f' data-mark="{r.get("mark") or "none"}"')
            search = html.escape(" ".join([
                r["company"], r["title"], " ".join(r["hard"] + r["soft"]),
                r.get("pay") or "", r.get("posted") or "",
                r.get("state") or "", r.get("note") or "",
                " ".join(sorted(r["sources"]))
            ]).lower(), quote=True)
            out.append(
                f'<article class="job {"fresh" if fresh else ""}" data-search="{search}"{attrs}>'
                f'<div class="co">{html.escape(r["company"])}</div>'
                f'<div class="role">{tag}<a href="{html.escape(r["url"])}" '
                f'target="_blank" rel="noopener">{html.escape(r["title"] or r["url"])}</a>'
                f'{dupe_bits(r)}{note}</div><div class="why">{why or "-"}</div>'
                f'<div class="pay">{html.escape(r.get("pay") or "-")}</div>'
                f'<div class="src">{src_tag(r["sources"])}</div>'
                f'<div class="posted">{html.escape(r.get("posted") or "-")}</div>'
                f'<div class="seen">{when}<span class="pts" title="{html.escape("; ".join(ranked))}">{points}</span></div>'
                f'<div class="act">{actions(r)}</div>'
                f'{feedback_box(r)}</article>')
        head = ('<div class="job-head"><span>company</span><span>role</span>'
                '<span>review note</span><span>compensation</span>'
                '<span>source</span><span>posted</span><span>first detected</span></div>')
        return f'<div class="scroll">{head}{"".join(out)}</div>'

    # Clean and Worth a glance open; the long lists start shut so they do not
    # bury the short ones. 1,144 wrong-country rows made the page unusable.
    OPEN = {"clean", "check", "reported"}
    sections = sections or MAIN
    parts = []
    for key, name, note in sections:
        items = [r for r in rows if r["bucket"] == key]
        n_new = len([r for r in items if r["first_seen"] == today])
        extra = f", {n_new} new" if n_new else ""
        op = " open" if key in OPEN else ""
        parts.append(
            f'<details class="{key}"{op}><summary>'
            f'<span class="chev">›</span><span class="section-name">{name}</span>'
            f'<span class="section-note">{note}</span>'
            f'<span class="count">{len(items)}{extra}</span>'
            f'</summary>{table(items)}</details>')

    n_g = len([r for r in rows if "google" in r["sources"]])
    n_b = len([r for r in rows if "boards" in r["sources"]])
    n_both = len([r for r in rows if len(r["sources"]) == 2])
    n_new = len([r for r in rows if r["first_seen"] == today])
    n_viable = len([r for r in rows if r["bucket"] in {"clean", "check"}])
    shown = [r for r in rows if r["bucket"] in {k for k, _, _ in sections}]
    date_label = datetime.date.fromisoformat(today).strftime("%d %b %Y").upper()
    n_aside = len([r for r in rows if r["bucket"] in REJECTED])
    aside_counts = ", ".join(
        f'{len([r for r in rows if r["bucket"] == k]):,} {n.lower()}'
        for k, n, _ in ASIDE if any(r["bucket"] == k for r in rows))
    jump = (f'<a class="jump" href="report-rejected.html">'
            f'<span class="chev">\u203a</span>'
            f'<span class="section-name">Done with</span>'
            f'<span class="section-note">{aside_counts}</span>'
            f'<span class="count">{n_aside:,} on the next page</span></a>'
            if aside and n_aside else
            f'<a class="jump" href="report.html">'
            f'<span class="chev">\u2039</span>'
            f'<span class="section-name">Back to the shortlist</span>'
            f'<span class="section-note">everything still in play</span>'
            f'<span class="count">go back</span></a>')
    if aside:
        other = (f'<a href="report-rejected.html">{n_aside:,} done with</a>'
                 if n_aside else "nothing set aside")
    else:
        other = '<a href="report.html">back to the shortlist</a>'
    head_title = "Job scan" if aside else "Applied and archived"
    lede = ("Every role found by the board sweep and Google, classified "
            "without hiding a single result."
            if aside else
            "Roles you have applied to or decided against, and roles the "
            "board stopped listing. Nothing here is waiting on you.")
    script = r"""
<script>
const input=document.querySelector('#job-filter');
const store=window.sessionStorage;

// ---------- filter
const chips=[...document.querySelectorAll('.chips button')];
function chipOn(b){return b.classList.contains('on')}
function passes(row,q){
 if(q&&!row.dataset.search.includes(q)) return false;
 const ages=chips.filter(b=>b.dataset.chip==='age'&&chipOn(b)).map(b=>+b.dataset.max);
 if(ages.length){
  const a=+row.dataset.age;
  // Several day chips read as "or", so the widest one wins.
  if(a<0||a>Math.max(...ages)) return false;
 }
 if(chips.some(b=>b.dataset.chip==='home'&&chipOn(b))&&row.dataset.home!=='1') return false;
 if(chips.some(b=>b.dataset.chip==='pay'&&chipOn(b))&&row.dataset.pay!=='1') return false;
 const marks=chips.filter(b=>b.dataset.chip==='mark'&&chipOn(b)).map(b=>b.dataset.val);
 if(marks.length&&!marks.includes(row.dataset.mark)) return false;
 const srcs=chips.filter(b=>b.dataset.chip==='src'&&chipOn(b)).map(b=>b.dataset.val);
 if(srcs.length&&!srcs.some(v=>row.dataset.src===v||row.dataset.src==='both')) return false;
 return true;
}
function applyFilter(){
 const q=input.value.trim().toLowerCase();
 let shown=0,total=0;
 document.querySelectorAll('.job').forEach(row=>{
  total++;
  const ok=passes(row,q);
  row.classList.toggle('hidden',!ok);
  if(ok) shown++;
 });
 const filtering=q||chips.some(chipOn);
 document.getElementById('chipnote').textContent=filtering?shown+' of '+total+' shown':'';
 if(filtering) document.querySelectorAll('details').forEach(d=>{if(d.querySelector('.job:not(.hidden)'))d.open=true});
 try{
  store.setItem('filter',input.value);
  store.setItem('chips',JSON.stringify(chips.map(chipOn)));
 }catch(e){}
}
input.addEventListener('input',applyFilter);
chips.forEach(b=>b.addEventListener('click',()=>{b.classList.toggle('on');applyFilter()}));
document.addEventListener('keydown',e=>{
 if(e.key!=='/') return;
 const a=document.activeElement;
 if(a===input||a.tagName==='TEXTAREA'||a.tagName==='INPUT') return;
 e.preventDefault();input.focus();
});

// ---------- keep the view across a rebuild
function saveView(){
 try{
  store.setItem('open',JSON.stringify([...document.querySelectorAll('details')].map(d=>d.open)));
  store.setItem('scroll',String(window.scrollY));
 }catch(e){}
}
window.addEventListener('beforeunload',saveView);
(function restore(){
 try{
  const f=store.getItem('filter'); if(f) input.value=f;
  const on=JSON.parse(store.getItem('chips')||'null');
  if(on) chips.forEach((b,i)=>{if(on[i]) b.classList.add('on')});
  if(f||(on&&on.some(Boolean))) applyFilter();
  const open=JSON.parse(store.getItem('open')||'null');
  if(open) document.querySelectorAll('details').forEach((d,i)=>{if(i<open.length)d.open=open[i]});
  const y=store.getItem('scroll'); if(y) window.scrollTo(0,+y);
 }catch(e){}
})();

// ---------- writing needs serve.py
const live=location.protocol.startsWith('http');
const toast=document.createElement('div');toast.className='toast';document.body.appendChild(toast);
let toastTimer;
function say(msg,bad){
 toast.textContent=msg;toast.classList.toggle('bad',!!bad);toast.classList.add('show');
 clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove('show'),2600);
}
if(!live){
 const w=document.createElement('div');w.className='offline';
 w.textContent='Opened as a file, so the buttons cannot save. Run python3 serve.py and open http://127.0.0.1:8777 instead.';
 document.querySelector('.bar').before(w);
}

// The section header count has to follow a row leaving, or the page lies.
function bumpCount(row){
 const d=row.closest('details'), c=d&&d.querySelector('.count');
 if(!c) return;
 c.textContent=c.textContent.replace(/^\d+/,n=>String(Math.max(0,+n-1)));
}

let known=null;
async function post(path,body){
 const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await r.json().catch(()=>({}));
 if(!r.ok) throw new Error(d.error||('http '+r.status));
 if(d.version) known=d.version;   // do not reload for our own write
 return d;
}

// ---------- say what is wrong, in your own words
document.addEventListener('click',e=>{
 const f=e.target.closest('button[data-flag]');
 if(f){
  if(!live){say('Writes need serve.py. See the note above.',true);return}
  const box=f.closest('.job').querySelector('.fb');
  box.classList.remove('hidden'); box.querySelector('textarea').focus();
  return;
 }
 const c=e.target.closest('.fb button.cancel');
 if(c) c.closest('.fb').classList.add('hidden');
});

async function sendFeedback(form){
 const text=form.querySelector('textarea').value.trim();
 if(!text){say('Write what is wrong first.',true);return}
 form.querySelectorAll('button,textarea').forEach(el=>el.disabled=true);
 try{
  await post('/rule-report',{url:form.dataset.url,note:text});
  form.classList.add('hidden');
  const row=form.closest('.job');
  // Out of this list now, not on the next rebuild. It reappears under
  // Reported when the page next refreshes.
  row.classList.add('going');
  setTimeout(()=>row.classList.add('hidden'),260);
  bumpCount(row);
  say('Sent, and moved out of this list. Waiting on a rules fix.');
 }catch(err){
  say('Could not send it: '+err.message,true);
  form.querySelectorAll('button,textarea').forEach(el=>el.disabled=false);
 }
}
document.addEventListener('submit',e=>{
 const form=e.target.closest('form.fb');
 if(!form) return;
 e.preventDefault(); sendFeedback(form);
});
document.addEventListener('keydown',e=>{
 if((e.metaKey||e.ctrlKey)&&e.key==='Enter'){
  const form=e.target.closest('form.fb');
  if(form){e.preventDefault();sendFeedback(form)}
 }
});

document.addEventListener('click',async e=>{
 const b=e.target.closest('button[data-mark]');
 if(!b) return;
 if(!live){say('Writes need serve.py. See the note above.',true);return}
 const row=b.closest('.job'), state=b.dataset.mark;
 b.disabled=true;
 try{
  await post('/mark',{url:b.dataset.url,state:state});
  if(state){
   row.classList.add('going');
   setTimeout(()=>row.classList.add('hidden'),260);
   bumpCount(row);
   say('Marked '+(state==='wont'?"won't apply":'applied')+', and moved to Handled.');
  }
  else{row.classList.remove('going');say('Reopened.')}
 }catch(err){say('Could not save: '+err.message,true);b.disabled=false}
});

// ---------- refresh when a scan finishes
if(live){
 setInterval(async()=>{
  try{
   const v=(await (await fetch('/version',{cache:'no-store'})).json()).version;
   if(known===null){known=v;return}
   if(v!==known){saveView();location.reload()}
  }catch(e){}
 },4000);
}
</script>"""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{head_title} · {date_label}</title><style>{CSS}</style></head><body>'
            f'<main class="page"><header class="masthead"><div>'
            f'<div class="eyebrow">{"Daily opportunity intelligence" if aside else "Done with"} · {date_label}</div>'
            f'<h1>Find the signal.<br>Skip the noise.</h1>'
            f'<p class="lede">{lede}</p>'
            f'</div><div class="stats">'
            f'<div class="stat"><span class="stat-value">{len(shown):,}</span><span class="stat-label">{"in front of you" if aside else "done with"}</span></div>'
            f'<div class="stat hot"><span class="stat-value">{n_new:,}</span><span class="stat-label">new today</span></div>'
            f'<div class="stat"><span class="stat-value">{n_viable:,}</span><span class="stat-label">worth reviewing</span></div>'
            f'<div class="stat"><span class="stat-value">{n_both:,}</span><span class="stat-label">found by both</span></div>'
            f'<div class="source-line"><strong>{n_b:,}</strong> board results &nbsp;·&nbsp; '
            f'<strong>{n_g:,}</strong> Google results &nbsp;·&nbsp; {other}</div></div></header>'
            + health_html(today) +
            f'<nav class="bar"><label class="search"><input id="job-filter" type="search" '
            f'placeholder="Filter company, role, reason, salary…" autocomplete="off" aria-label="Filter jobs"></label>'
            f'<button onclick="document.querySelectorAll(\'details\').forEach(d=>d.open=true)">expand all</button>'
            f'<button onclick="document.querySelectorAll(\'details\').forEach(d=>d.open=false)">collapse all</button></nav>'
            f'<nav class="chips">'
            f'<button data-chip="age" data-max="7">posted 7 days</button>'
            f'<button data-chip="age" data-max="14">14 days</button>'
            f'<button data-chip="age" data-max="30">30 days</button>'
            f'<button data-chip="home">{config.HOME_LABEL}</button>'
            f'<button data-chip="pay">pay disclosed</button>'
            f'<button data-chip="mark" data-val="good">marked good</button>'
            f'<button data-chip="mark" data-val="none">unreviewed</button>'
            f'<button data-chip="src" data-val="google">from Google</button>'
            f'<button data-chip="src" data-val="boards">from boards</button>'
            f'<span class="chipnote" id="chipnote"></span></nav>'
            f'<section class="results">{"".join(parts)}{jump}</section>'
            f'</main>{script}</body></html>')


def main():
    rows = load()
    today = str(datetime.date.today())
    runlog.record("report", ok=True, rows=len(rows),
                  viable=len([r for r in rows
                              if r["bucket"] in ("clean", "check")]))
    OUT.write_text(render(rows, today, MAIN, aside=True))
    OUT_NO.write_text(render(rows, today, ASIDE, aside=False))
    for key, name, _ in SECTIONS:
        items = [r for r in rows if r["bucket"] == key]
        new = len([r for r in items if r["first_seen"] == today])
        print(f"  {name}: {len(items)}" + (f" ({new} new)" if new else ""))
    print(OUT)


if __name__ == "__main__":
    main()
