#!/usr/bin/env python3
"""Job-hunt scanner. Pure stdlib, no LLM -> zero AI credits. Runs on the BoxLite cloud box.

Every INTERVAL seconds it writes /root/JOB_HUNT_REPORT.md with:
  1. Your open PRs (any org) and which ones had activity in the last 3 days
  2. Fresh, unassigned, low-comment issues in target repos (good PR candidates)
  3. Careers pages whose content changed since the last scan

Usage: python3 job_hunt_daemon.py            # loop forever (daily)
       python3 job_hunt_daemon.py --once     # single scan
Optional env GITHUB_TOKEN raises GitHub rate limits; works without it (slower).
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

GH_USER = "shobhitagnihotri69"
INTERVAL = 24 * 3600
OUT = Path(os.environ.get("JOB_HUNT_DIR", "/root"))
REPORT, STATE = OUT / "JOB_HUNT_REPORT.md", OUT / "job_hunt_state.json"

# Tier 1-2 from claude-startup-hunt/research/04_sandbox_targets.md
REPOS = [
    "e2b-dev/infra", "e2b-dev/E2B", "superradcompany/microsandbox", "smol-machines/smolvm",
    "daytonaio/daytona", "beam-cloud/beta9", "zerobootdev/zeroboot", "kvcache-ai/AgentENV",
    "SWE-agent/SWE-ReX", "rivet-dev/agentos", "pydantic/monty",
]
CAREERS = {
    "E2B": "https://e2b.dev/careers",
    "Pydantic": "https://pydantic.dev/jobs",
    "Superserve": "https://job-boards.greenhouse.io/superserve",
    "Blaxel (YC)": "https://www.ycombinator.com/companies/blaxel/jobs",
    "smolvm (YC)": "https://www.ycombinator.com/companies?query=smolvm",
}
LABELS = ["good first issue", "help wanted", "bug"]


def get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"User-Agent": "job-hunt-scanner", "Accept": accept})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def search(q):
    url = "https://api.github.com/search/issues?per_page=30&sort=updated&q=" + urllib.parse.quote(q)
    # unauthenticated search limit is 10/min
    time.sleep(2 if os.environ.get("GITHUB_TOKEN") else 7)
    return json.loads(get(url)).get("items", [])


def my_prs():
    since = datetime.now(timezone.utc) - timedelta(days=3)
    rows = []
    for it in search(f"is:pr is:open author:{GH_USER}"):
        repo = it["repository_url"].split("/repos/")[1]
        upd = datetime.fromisoformat(it["updated_at"].replace("Z", "+00:00"))
        flag = "🔔 activity" if upd > since else ""
        rows.append(f"| {flag} | [{repo}#{it['number']}]({it['html_url']}) | {it['title'][:70]} "
                    f"| {it['comments']} | {it['updated_at'][:10]} |")
    rows.sort(reverse=True)
    return rows


def fresh_issues():
    since = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%d")
    out = []
    for repo in REPOS:
        label_q = " ".join(f'label:"{l}"' for l in LABELS[:1])
        found = {}
        for q in (f"repo:{repo} is:issue is:open no:assignee {label_q} updated:>{since}",
                  f"repo:{repo} is:issue is:open no:assignee label:bug comments:<4 updated:>{since}"):
            try:
                for it in search(q):
                    if "pull_request" not in it and it["comments"] < 4:
                        found[it["number"]] = it
            except Exception as e:  # repo renamed / rate-limited: keep going
                out.append(f"| {repo} | ⚠️ {type(e).__name__}: {e} | | |")
                break
        for it in sorted(found.values(), key=lambda x: x["updated_at"], reverse=True)[:5]:
            out.append(f"| {repo} | [#{it['number']}]({it['html_url']}) {it['title'][:70]} "
                       f"| {it['comments']} | {it['updated_at'][:10]} |")
    return out


def page_text(url):
    raw = get(url, accept="text/html")
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def careers(state):
    out, hashes = [], state.setdefault("careers", {})
    for name, url in CAREERS.items():
        try:
            txt = page_text(url)
            h = hashlib.sha256(txt.encode()).hexdigest()[:12]
            status = "new" if name not in hashes else ("🔔 CHANGED" if hashes[name] != h else "same")
            hashes[name] = h
            hits = sorted(set(m.lower() for m in re.findall(
                r"\b(intern(?:ship)?|remote|india|bangalore|bengaluru|contract)\b", txt, re.I)))
            out.append(f"| {status} | [{name}]({url}) | {', '.join(hits) or '-'} |")
        except Exception as e:
            out.append(f"| ⚠️ error | [{name}]({url}) | {type(e).__name__} |")
    return out


def scan():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"# Job-hunt scan — {now}\n",
             "## 1. My open PRs (🔔 = activity in last 3 days → reply first)\n",
             "| | PR | Title | Comments | Updated |", "|---|---|---|---|---|", *my_prs(),
             "\n## 2. PR candidates (unassigned, <4 comments, updated in last 21 days)\n",
             "| Repo | Issue | Comments | Updated |", "|---|---|---|---|", *fresh_issues(),
             "\n## 3. Careers pages\n",
             "| Status | Company | Keywords on page |", "|---|---|---|", *careers(state)]
    REPORT.write_text("\n".join(parts) + "\n")
    STATE.write_text(json.dumps(state))
    print(f"[{now}] wrote {REPORT}", flush=True)


if __name__ == "__main__":
    while True:
        try:
            scan()
        except Exception as e:
            print("scan failed:", e, flush=True)
        if "--once" in sys.argv:
            break
        time.sleep(INTERVAL)
