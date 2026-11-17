#!/usr/bin/env python3
"""
Top 100 AI Agent Sandbox, MicroVM & Code Execution Startups / Communities Engine
Scrapes GitHub search across multi-angle queries, validates projects,
extracts Discord/Slack/community links, and generates a structured master database.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

ssl_ctx = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

WORKSPACE = "/Users/shobhitagnihotri/Desktop/internship"
JSON_OUTPUT = os.path.join(WORKSPACE, "TOP_100_SANDBOX_STARTUPS.json")
MD_OUTPUT = os.path.join(WORKSPACE, "TOP_100_SANDBOX_STARTUPS.md")

DISCORD_REGEX = re.compile(r"https?://(?:discord\.(?:gg|com/invite)/[a-zA-Z0-9_-]+)")
SLACK_REGEX = re.compile(r"https?://(?:join\.slack\.com/t/[^\s\)\"\'>]+|[a-zA-Z0-9-]+\.slack\.com)")

# Comprehensive multi-angle search queries
SEARCH_QUERIES = [
    "ai sandbox microvm",
    "agent sandbox code execution",
    "ai code interpreter sandbox",
    "agent microvm runtime",
    "coding agent sandbox",
    "firecracker agent sandbox",
    "cloud browser agent sandbox",
    "ai execution environment",
    "isolated code execution agent",
    "llm sandbox environment",
    "ai agent container runtime",
    "autonomous agent sandbox",
]

# Curated known leaders and fast-growing startups in the ecosystem
CURATED_SEED_PROJECTS = [
    {"name": "E2B", "repo": "e2b-dev/E2B", "website": "https://e2b.dev", "desc": "Cloud sandboxes for AI agents (Firecracker microVMs)", "category": "MicroVM Cloud Sandbox", "community": "https://discord.gg/e2b"},
    {"name": "Modal", "repo": "modal-labs/modal-client", "website": "https://modal.com", "desc": "Serverless cloud compute and sandboxes for AI & coding agents", "category": "Serverless Compute & Sandboxes", "community": "https://modal.com/slack"},
    {"name": "Daytona", "repo": "daytonaio/daytona", "website": "https://daytona.io", "desc": "Automated developer environments & sandboxes for AI agents", "category": "Dev Environments & Sandboxes", "community": "https://daytona.io/slack"},
    {"name": "BoxLite", "repo": "boxlite-ai/boxlite", "website": "https://boxlite.ai", "desc": "Embeddable micro-VM runtime & cloud sandboxes for AI agents", "category": "MicroVM Runtime & Cloud", "community": "https://discord.gg/boxlite"},
    {"name": "Browserbase", "repo": "browserbase/stagehand", "website": "https://browserbase.com", "desc": "Developer platform and cloud browser infrastructure for AI agents", "category": "Cloud Browser Sandbox", "community": "https://discord.gg/browserbase"},
    {"name": "Browser-Use", "repo": "browser-use/browser-use", "website": "https://browser-use.com", "desc": "Open-source web automation agent running inside sandboxes", "category": "Browser Agent", "community": "https://discord.gg/NxqusWjjQK"},
    {"name": "InstaBox", "repo": "InsForge/instabox", "website": "https://instabox.sh", "desc": "Cloud microVM sandboxes for AI coding agents (YC)", "category": "Coding Agent Sandbox", "community": "https://discord.gg/instabox"},
    {"name": "Boat", "repo": "boat-dev/boat", "website": "https://boat.dev", "desc": "Persistent Ubuntu VMs for AI coding agents", "category": "Coding Agent VM", "community": "https://boat.dev/discord"},
    {"name": "Superagent (VibeKit)", "repo": "superagent-ai/vibekit", "website": "https://vibekit.bot", "desc": "Run AI coding agents in isolated sandboxes", "category": "Agent Sandbox Framework", "community": "https://discord.gg/spZ7MnqFT4"},
    {"name": "Bullet", "repo": "trybullet/cli", "website": "https://codewithbullet.com", "desc": "Fast terminal coding agent with parallelized execution (YC S26)", "category": "Coding Agent", "community": "https://discord.gg/nGj97KffS4"},
    {"name": "smolvm", "repo": "smol-machines/smolvm", "website": "https://smolmachines.com", "desc": "Embeddable, branchable virtual machine for AI agents", "category": "MicroVM Runtime", "community": "https://discord.gg/vx375Jyn"},
    {"name": "Microsandbox", "repo": "superradcompany/microsandbox", "website": "https://microsandbox.dev", "desc": "Local-first microVM runtime for untrusted AI agent workloads", "category": "Local MicroVM Sandbox", "community": "https://discord.gg/microsandbox"},
    {"name": "Blaxel", "repo": "blaxel-ai/blaxel", "website": "https://blaxel.ai", "desc": "Ultra-low latency AI agent sandboxes scaling to zero cost", "category": "Fast Standby Sandboxes", "community": "https://discord.gg/blaxel"},
    {"name": "Northflank", "repo": "northflank/northflank-cli", "website": "https://northflank.com", "desc": "Developer platform running microVM sandboxes and BYOC", "category": "Cloud Sandboxes & BYOC", "community": "https://discord.gg/northflank"},
    {"name": "Fly.io Sprites", "repo": "superfly/flyctl", "website": "https://fly.io", "desc": "Hardware-isolated microVMs with fast boot times", "category": "Edge MicroVMs", "community": "https://community.fly.io"},
    {"name": "OpenHands", "repo": "All-Hands-AI/OpenHands", "website": "https://openhands.dev", "desc": "Autonomous AI software engineer running in container sandboxes", "category": "SWE Agent Runtime", "community": "https://discord.gg/openhands"},
    {"name": "Aider", "repo": "Aider-AI/aider", "website": "https://aider.chat", "desc": "AI pair programming in your terminal with git & sandbox execution", "category": "CLI Coding Agent", "community": "https://discord.gg/aider"},
    {"name": "Cline", "repo": "cline/cline", "website": "https://cline.bot", "desc": "Autonomous coding agent in VS Code with MCP and shell execution", "category": "VS Code Agent", "community": "https://discord.gg/cline"},
    {"name": "Perplexity SPACE", "repo": "perplexity-ai/space", "website": "https://perplexity.ai", "desc": "Firecracker microVM sandbox platform for AI search and code", "category": "Enterprise MicroVM Sandbox", "community": "https://discord.gg/perplexity"},
    {"name": "Kuasar", "repo": "kuasar-io/kuasar", "website": "https://kuasar.io", "desc": "Multi-sandbox container runtime supporting MicroVMs & WebAssembly", "category": "Cloud Native MicroVM", "community": "https://github.com/kuasar-io/kuasar"},
]

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def fetch_text(url):
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=8) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def collect_top_startups():
    print("🚀 Initializing deep scan for Top 100 AI Sandbox & Agent Runtime Startups...")
    database = {}

    # 1. Register Seed Leaders
    for seed in CURATED_SEED_PROJECTS:
        full_name = seed["repo"]
        database[full_name] = {
            "name": seed["name"],
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "website": seed["website"],
            "description": seed["desc"],
            "category": seed["category"],
            "stars": 0,
            "community_links": [seed["community"]] if seed.get("community") else [],
            "source": "Curated Seed Leader"
        }

    # 2. Query GitHub across multiple queries
    for q_idx, q in enumerate(SEARCH_QUERIES, 1):
        print(f"[{q_idx}/{len(SEARCH_QUERIES)}] Querying: '{q}'...")
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=30"
        data = fetch_json(url)
        if not data or "items" not in data:
            time.sleep(1)
            continue

        for item in data["items"]:
            full_name = item.get("full_name")
            if not full_name:
                continue

            desc = (item.get("description") or "")
            name = item.get("name")
            combined_text = (name + " " + desc).lower()

            # Ensure high relevance to sandboxes/runtimes/agents
            relevance_keywords = ["sandbox", "microvm", "vm", "firecracker", "execution", "agent", "interpreter", "runtime", "virtual machine", "hypervisor"]
            if not any(k in combined_text for k in relevance_keywords):
                continue

            stars = item.get("stargazers_count", 0)
            website = item.get("homepage") or ""
            html_url = item.get("html_url")

            if full_name in database:
                database[full_name]["stars"] = max(database[full_name]["stars"], stars)
                if not database[full_name]["website"] and website:
                    database[full_name]["website"] = website
            else:
                database[full_name] = {
                    "name": name,
                    "full_name": full_name,
                    "url": html_url,
                    "website": website,
                    "description": desc,
                    "category": "AI Sandbox / Agent Tool",
                    "stars": stars,
                    "community_links": [],
                    "source": "GitHub Star Search"
                }

        time.sleep(1.5)  # Respect rate limits

    print(f"Total unique candidates collected: {len(database)}")
    return database

def enrich_and_extract_communities(database):
    print("🔍 Extracting community links (Discord / Slack) from repos and landing pages...")
    # Sort by stars descending
    sorted_items = sorted(database.values(), key=lambda x: x["stars"], reverse=True)
    
    # Process top 120 candidates
    top_candidates = sorted_items[:120]

    for idx, item in enumerate(top_candidates, 1):
        if item.get("community_links"):
            continue

        full_name = item["full_name"]
        print(f"[{idx}/{len(top_candidates)}] Scanning {full_name}...")
        
        # Check GitHub Readme
        readme_raw = fetch_text(f"https://raw.githubusercontent.com/{full_name}/main/README.md")
        if not readme_raw:
            readme_raw = fetch_text(f"https://raw.githubusercontent.com/{full_name}/master/README.md")

        links = set(DISCORD_REGEX.findall(readme_raw) + SLACK_REGEX.findall(readme_raw))

        # Check Website if available
        if item.get("website"):
            web_raw = fetch_text(item["website"])
            links.update(DISCORD_REGEX.findall(web_raw))
            links.update(SLACK_REGEX.findall(web_raw))

        item["community_links"] = list(links)
        time.sleep(0.3)

    return top_candidates[:100]

def export_reports(top_100):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Save JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"total": len(top_100), "generated_at": now_str, "startups": top_100}, f, indent=2)

    # 2. Save Markdown
    lines = [
        "# 🌐 Top 100 AI Agent Sandbox & MicroVM Startups / Communities",
        f"> **Generated:** `{now_str}`",
        "> Complete intelligence directory of 100 cloud sandboxes, microVM runtimes, browser agents, and coding execution environments with direct community channels.",
        "",
        "---",
        "",
        "| # | Startup / Project | Stars | Category / Description | Official Website | Community (Discord / Slack) |",
        "|---|---|---|---|---|---|",
    ]

    for idx, s in enumerate(top_100, 1):
        name_link = f"[{s['name']}]({s['url']})"
        stars = f"⭐ {s['stars']:,}" if s['stars'] > 0 else "-"
        desc = (s.get("description") or "AI execution runtime")[:80].replace("|", "/")
        website = f"[Visit]({s['website']})" if s.get("website") else "-"
        
        comm_list = []
        for c in s.get("community_links", []):
            if "discord" in c:
                comm_list.append(f"[Discord]({c})")
            elif "slack" in c:
                comm_list.append(f"[Slack]({c})")
            else:
                comm_list.append(f"[Community]({c})")
        
        comm_str = ", ".join(comm_list) if comm_list else "[Check Repo]" + f"({s['url']})"

        lines.append(f"| {idx} | {name_link} | {stars} | {desc} | {website} | {comm_str} |")

    with open(MD_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n🎉 Successfully compiled Top 100 database!")
    print(f"📄 JSON: {JSON_OUTPUT}")
    print(f"📊 Markdown: {MD_OUTPUT}")

def main():
    db = collect_top_startups()
    top_100 = enrich_and_extract_communities(db)
    export_reports(top_100)

if __name__ == "__main__":
    main()

