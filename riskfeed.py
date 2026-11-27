"""vendor-radar: pull security news RSS feeds and flag articles that mention your vendors.

Writes matches to a CSV that a SIEM can ingest. See README.md for setup."""

import csv
import html
import re
import socket
from pathlib import Path
import feedparser
import yaml

# Paths are resolved from the script's own folder, so it works when run by a
# scheduler (Task Scheduler / cron) from a different working directory.
BASE_DIR = Path(__file__).resolve().parent
FEEDS_FILE = BASE_DIR / "config" / "feeds.yaml"
WATCHLIST_FILE = BASE_DIR / "config" / "watchlist.yaml"
OUTPUT_FILE = BASE_DIR / "risk_feed.csv"

# feedparser has no timeout option; without this a hung feed server would
# block the script forever.
socket.setdefaulttimeout(15)
USER_AGENT = "vendor-radar/0.1 (third-party risk feed monitor)"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        raise SystemExit(f"[!] {path} is empty or only has comments.")
    return data


def fetch_feed(name, url):
    """Download and parse one feed. Returns a list of normalized article dicts."""
    parsed = feedparser.parse(url, agent=USER_AGENT)
    if parsed.bozo and not parsed.entries:
        print(f"[!] {name}: could not read feed ({parsed.bozo_exception})")
        return []

    articles = []
    for entry in parsed.entries:
        articles.append({
            "source": name,
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", ""),
            "published": entry.get("published", entry.get("updated", "")),
            "summary": entry.get("summary", ""),
        })
    return articles


def clean(text):
    """Strip HTML tags, decode entities like &amp;, and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def build_matchers(watchlist):
    """Turn each vendor in watchlist.yaml into a compiled regex plus its exclude list."""
    matchers = []
    for vendor in watchlist["vendors"]:
        terms = [vendor["name"]] + vendor.get("aliases", [])
        # \b = word boundary, so "Zoom" matches "Zoom" but not "Zoominfo".
        # re.escape stops names like "C++" or "M365." from being read as regex syntax.
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b",
            re.IGNORECASE,
        )
        excludes = [e.lower() for e in vendor.get("exclude", [])]
        matchers.append((vendor["name"], pattern, excludes))
    return matchers


def find_vendors(article, matchers):
    """Return the names of every watchlist vendor mentioned in the article."""
    text = (article["title"] + " " + article["summary"]).lower()
    hits = []
    for name, pattern, excludes in matchers:
        checked = text
        for phrase in excludes:          # blank out "zoom in" before looking for "zoom"
            checked = checked.replace(phrase, " ")
        if pattern.search(checked):
            hits.append(name)
    return hits


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["vendor", "title", "link", "summary"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"[+] Wrote {len(rows)} rows to {path}")


def main():
    feeds = load_yaml(FEEDS_FILE)["feeds"]
    matchers = build_matchers(load_yaml(WATCHLIST_FILE))

    rows = []
    for feed in feeds:
        articles = fetch_feed(feed["name"], feed["url"])
        print(f"[+] {feed['name']}: {len(articles)} articles")

        for a in articles:
            a["title"] = clean(a["title"])
            a["summary"] = clean(a["summary"])
            vendors = find_vendors(a, matchers)
            if vendors:                  # only keep articles that mention a vendor
                print(f"    [HIT] {', '.join(vendors)}: {a['title']}")
                rows.append({
                    "vendor": ";".join(vendors),
                    "title": a["title"],
                    "link": a["link"],
                    "summary": a["summary"],
                })

    write_csv(rows, OUTPUT_FILE)


if __name__ == "__main__":
    main()
