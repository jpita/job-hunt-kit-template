#!/usr/bin/env python3
"""Serve the report so clicking in it can write to disk.

A page opened as file:// cannot save anything, so the checkboxes would live
only in the browser and report.py would never see them. This serves the same
report over http from 127.0.0.1 and accepts the writes.

It also rebuilds the page when a scan finishes, and the page polls /version so
an open tab refreshes itself.

  python3 serve.py            http://127.0.0.1:<PORT from me/search.py>
  python3 serve.py --port N

Nothing is exposed off this machine: it binds 127.0.0.1 and refuses a request
whose Host header is not local, so another site cannot reach it.

A launchd agent keeps it running, so editing this file changes nothing until:

  launchctl kickstart -k gui/$(id -u)/com.$(whoami).job-scan-server
"""
import argparse, datetime, json, pathlib, threading, webbrowser

import config
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import marks
import report
import rule_reports

HERE = config.STATE
CODE = pathlib.Path(__file__).parent
PAGE = HERE / "report.html"
ASIDE = HERE / "report-rejected.html"
# Any of these changing means the page is out of date.
WATCH = [HERE / n for n in ("board-seen.json", "google-seen.json",
         "feedback.json", "rule-reports.json", "runs.json")] + [
         CODE / n for n in ("report.py", "rules.py", "judge.py", "rank.py",
         "marks.py")] + [config.FILE]
ALLOWED_HOSTS = ("127.0.0.1", "localhost", "[::1]")

_build_lock = threading.Lock()


def version():
    """A token that changes when any source of the page changes."""
    stamps = []
    for f in WATCH:
        stamps.append(int(f.stat().st_mtime) if f.exists() else 0)
    return "-".join(str(s) for s in stamps)


def build_if_stale(which=None):
    """Rebuild both pages when their sources are newer. Returns one page."""
    which = which or PAGE
    with _build_lock:
        newest = max(int(f.stat().st_mtime) for f in WATCH if f.exists())
        stale = [f for f in (PAGE, ASIDE)
                 if not f.exists() or int(f.stat().st_mtime) < newest]
        if stale:
            report.main()
        return which.read_bytes()


class Handler(BaseHTTPRequestHandler):
    server_version = "job-scan"

    def log_message(self, fmt, *a):
        # One line per write, nothing for the version polling. launchd captures
        # stdout through a pipe, so an unflushed line is invisible for hours.
        if self.command == "POST":
            print(f"{datetime.datetime.now():%H:%M:%S} {fmt % a}", flush=True)

    def _local_only(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host in ALLOWED_HOSTS:
            return True
        self.send_error(403, "this server only answers on 127.0.0.1")
        return False

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._local_only():
            return
        path = self.path.split("?")[0]
        if path == "/version":
            return self._send(200, {"version": version()})
        if path in ("/", "/report.html", "/report-rejected.html"):
            try:
                html = build_if_stale(
                    ASIDE if path == "/report-rejected.html" else PAGE)
            except Exception as e:
                return self._send(500, f"could not build the report: {e}",
                                  "text/plain; charset=utf-8")
            return self._send(200, html, "text/html; charset=utf-8")
        self.send_error(404)

    def do_POST(self):
        if not self._local_only():
            return
        path = self.path.split("?")[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 16384:
                raise ValueError("payload too large")
            data = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError) as e:
            return self._send(400, {"error": str(e)})

        url = (data.get("url") or "").strip()
        if not url.startswith(("http://", "https://")) or len(url) > 500:
            return self._send(400, {"error": "url must be a job page link"})

        if path == "/mark":
            fields = {k: v for k, v in data.items()
                      if k in ("verdict", "state", "note")}
            if not fields:
                return self._send(400, {"error": "nothing to change"})
            try:
                entry = marks.set_fields(url, **fields)
            except (ValueError, OSError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, {"url": url, "entry": entry,
                                    "version": version()})

        if path == "/rule-report":
            if not (data.get("note") or "").strip() and not data.get("expected"):
                return self._send(400, {"error": "say what is wrong"})
            try:
                row = report.row_for(url)
                if not row:
                    return self._send(404, {"error": "no such job in the report"})
                item = rule_reports.add(
                    url,
                    bucket_now=row.get("bucket", ""),
                    expected=str(data.get("expected", "")),
                    reasons=(row.get("hard") or []) + (row.get("soft") or []),
                    company=row.get("company", ""),
                    title=row.get("title", ""),
                    note=str(data.get("note", "")))
            except (ValueError, TypeError, OSError) as e:
                return self._send(400, {"error": str(e)})
            # rule-reports.json is watched, so the page rebuilds and the badge
            # appears without a manual refresh.
            return self._send(200, {"item": item, "version": version()})
        self.send_error(404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=config.PORT)
    ap.add_argument("--no-open", action="store_true",
                    help="do not open a browser tab")
    a = ap.parse_args()
    where = f"http://127.0.0.1:{a.port}"
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"job scan report on {where}", flush=True)
    print("  marks go to feedback.json, wrong-bucket reports to "
          "rule-reports.json", flush=True)
    if not a.no_open:
        webbrowser.open(where)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
