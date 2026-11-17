#!/usr/bin/env python3
"""
Startup & Community Radar for AI Sandboxes / Agent Runtimes
Discovers newly created GitHub repos, Hacker News launches (Show HN),
and extracts Discord/community invite links and maintainer info.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# Create unverified context to bypass any local SSL certificate issues
ssl_ctx = ssl._create_unverified_context()

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "discovered_startups.json")
MARKDOWN_REPORT = os.path.join(OUTPUT_DIR, "STARTUP_RADAR_REPORT.md")

DISCORD_REGEX = re.compile(r"https?://(?:discord\.(?:gg|com/invite)/[a-zA-Z0-9_-]+)")
SLACK_REGEX = re.compile(r"https?://(?:join\.slack\.com/t/[^\s\)\"\'>]+|[a-zA-Z0-9-]+\.slack\.com)")

SEARCH_TOPICS = [
    "ai sandbox microvm",
    "agent sandbox microvm",
    "agent code execution sandbox",
    "coding agent sandbox",
    "cloud sandbox ai agent",
    "browser agent sandbox",
    "microvm firecracker agent",
    "agent execution environment",
]

HN_QUERIES = [
    "Show HN sandbox AI agent",
    "Show HN microVM AI",
    "Show HN code execution agent",
    "Show HN coding agent sandbox",
]

def fetch_json(url, headers=None):
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", USER_AGENT)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return None

def fetch_text(url):
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    headers = {"User-Agent": USER_AGENT}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=8) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def search_github_repos():
    print("🔍 [1/2] Searching GitHub for new & trending AI Sandbox repos...")
    found_repos = {}
    
    # Check repos updated/created in the last 180 days
    date_filter = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d")

    for query in SEARCH_TOPICS:
        q = f"{query} pushed:>{date_filter}"
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=updated&order=desc&per_page=15"
        
        data = fetch_json(url)
        if not data or "items" not in data:
            time.sleep(1)
            continue

        for item in data["items"]:
            full_name = item.get("full_name")
            if not full_name or full_name in found_repos:
                continue

            stars = item.get("stargazers_count", 0)
            desc = item.get("description") or ""
            html_url = item.get("html_url")
            homepage = item.get("homepage") or ""
            updated_at = item.get("updated_at", "")[:10]
            owner = item.get("owner", {}).get("login", "")

            # Filter out irrelevant or giant unrelated repos
            text_for_eval = (desc + " " + item.get("name", "")).lower()
            if not any(k in text_for_eval for k in ["sandbox", "microvm", "vm", "firecracker", "execution", "agent", "hypervisor"]):
                continue

            found_repos[full_name] = {
                "name": item.get("name"),
                "full_name": full_name,
                "url": html_url,
                "description": desc,
                "stars": stars,
                "homepage": homepage,
                "updated_at": updated_at,
                "owner": owner,
                "source": "GitHub Search",
                "community_links": [],
            }
        time.sleep(1.2)  # Respect GitHub rate limits

    print(f"   -> Found {len(found_repos)} matching repositories.")
    return found_repos

def search_hacker_news():
    print("📰 [2/2] Searching Hacker News Algolia API for recent Show HN launches...")
    found_stories = {}
    
    # Timestamp for last 12 months
    created_after = int((datetime.utcnow() - timedelta(days=365)).timestamp())

    for query in HN_QUERIES:
        url = (
            f"https://hn.algolia.com/api/v1/search_by_date?"
            f"query={urllib.parse.quote(query)}"
            f"&tags=story"
            f"&numericFilters=created_at_i>{created_after}"
            f"&hitsPerPage=10"
        )
        data = fetch_json(url)
        if not data or "hits" not in data:
            continue

        for hit in data["hits"]:
            story_id = hit.get("objectID")
            title = hit.get("title", "")
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            author = hit.get("author", "")
            points = hit.get("points", 0)
            created_at = hit.get("created_at", "")[:10]

            if story_id not in found_stories:
                found_stories[story_id] = {
                    "title": title,
                    "url": story_url,
                    "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                    "author": author,
                    "points": points,
                    "created_at": created_at,
                    "source": "Hacker News (Show HN)",
                    "community_links": [],
                }
        time.sleep(0.5)

    print(f"   -> Found {len(found_stories)} Show HN discussions.")
    return found_stories

def inspect_and_extract_community_links(repos, hn_stories):
    print("🌐 Inspecting homepages and readmes for Discord / Slack links...")
    
    # 1. Check GitHub Readmes
    for full_name, repo in repos.items():
        readme_url = f"https://raw.githubusercontent.com/{full_name}/main/README.md"
        content = fetch_text(readme_url)
        if not content:
            # Try master branch
            readme_url = f"https://raw.githubusercontent.com/{full_name}/master/README.md"
            content = fetch_text(readme_url)

        links = set(DISCORD_REGEX.findall(content) + SLACK_REGEX.findall(content))

        # Check homepage if provided
        if repo.get("homepage"):
            hp_content = fetch_text(repo["homepage"])
            links.update(DISCORD_REGEX.findall(hp_content))
            links.update(SLACK_REGEX.findall(hp_content))

        repo["community_links"] = list(links)

    # 2. Check HN project URLs
    for sid, story in hn_stories.items():
        target_url = story.get("url")
        if target_url and "news.ycombinator.com" not in target_url:
            content = fetch_text(target_url)
            links = set(DISCORD_REGEX.findall(content) + SLACK_REGEX.findall(content))
            story["community_links"] = list(links)

def generate_report(repos, hn_stories):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Combine results
    all_data = {
        "generated_at": now_str,
        "github_repos": list(repos.values()),
        "hn_launches": list(hn_stories.values()),
    }

    # Save raw JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    # Generate Markdown Report
    lines = [
        "# 📡 AI Sandbox & MicroVM Startup Radar Report",
        f"> **Last Updated:** `{now_str}`",
        "> Automatically tracks new AI code execution, microVM, and agent sandbox startups, repos, and their community channels.",
        "",
        "---",
        "",
        "## 🔥 Direct Community Channels (Discord / Slack Found)",
        "",
        "| Project / Startup | Stars / Points | Description / Pitch | Community Link |",
        "|---|---|---|---|",
    ]

    # Projects with confirmed community links first
    high_priority = []
    for r in repos.values():
        if r["community_links"]:
            high_priority.append({
                "name": f"[{r['name']}]({r['url']})",
                "score": f"⭐ {r['stars']}",
                "desc": (r["description"] or "No description")[:80] + "...",
                "links": ", ".join([f"[Discord/Slack]({l})" for l in r["community_links"]])
            })

    for s in hn_stories.values():
        if s["community_links"]:
            high_priority.append({
                "name": f"[{s['title'][:35]}...]({s['url']})",
                "score": f"▲ {s['points']} pts",
                "desc": f"Show HN discussion: [HN Thread]({s['hn_url']})",
                "links": ", ".join([f"[Discord/Slack]({l})" for l in s["community_links"]])
            })

    if high_priority:
        for item in high_priority:
            lines.append(f"| {item['name']} | {item['score']} | {item['desc']} | {item['links']} |")
    else:
        lines.append("| *None found in this scan batch* | - | - | - |")

    lines.extend([
        "",
        "---",
        "",
        "## 📦 Top GitHub Repositories (Active & Relevant)",
        "",
        "| Repository | Stars | Last Updated | Description | Links |",
        "|---|---|---|---|---|",
    ])

    sorted_repos = sorted(repos.values(), key=lambda x: x["stars"], reverse=True)
    for r in sorted_repos[:20]:
        disc = ", ".join([f"[Community]({l})" for l in r["community_links"]]) if r["community_links"] else "Check repo"
        hp = f"[Site]({r['homepage']})" if r["homepage"] else "-"
        lines.append(f"| [{r['full_name']}]({r['url']}) | ⭐ {r['stars']} | `{r['updated_at']}` | {(r['description'] or '')[:70]} | {hp} / {disc} |")

    lines.extend([
        "",
        "---",
        "",
        "## 📰 Hacker News (Show HN) Launches",
        "",
        "| Launch Title | Points | Date | Links |",
        "|---|---|---|---|",
    ])

    sorted_hn = sorted(hn_stories.values(), key=lambda x: x["points"], reverse=True)
    for s in sorted_hn[:15]:
        lines.append(f"| [{s['title']}]({s['url']}) | ▲ {s['points']} | `{s['created_at']}` | [HN Discussion]({s['hn_url']}) |")

    with open(MARKDOWN_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✅ Scan complete!")
    print(f"📄 Generated JSON database: {OUTPUT_FILE}")
    print(f"📊 Generated Markdown report: {MARKDOWN_REPORT}")

def main():
    repos = search_github_repos()
    hn = search_hacker_news()
    inspect_and_extract_community_links(repos, hn)
    generate_report(repos, hn)

if __name__ == "__main__":
    main()

