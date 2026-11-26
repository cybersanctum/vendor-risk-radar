# vendor-risk-radar

**Third-party breach monitoring from public security news feeds, piped to your SIEM.**

When a vendor you depend on gets breached, the news often hits security blogs and advisories hours or days before the vendor emails you. vendor-risk-radar watches those feeds, flags any article that mentions a vendor on your watchlist, and writes the hits to a CSV your SIEM can ingest and alert on.

## Why use this

Commercial third-party risk and threat intelligence platforms can cost thousands of dollars a year, and much of what they surface about vendor breaches starts as public reporting. vendor-radar covers that early-warning piece for free: it watches the same public security news and advisories, flags mentions of the vendors you rely on, and feeds them straight into the SIEM you already run. It doesn't replace a full TPRM program (questionnaires, security ratings, contract reviews), but it gives smaller teams breach awareness without another license, and gives larger teams a cheap second source to check paid feeds against.

## Extending it

Both lists are plain YAML, so no code changes are needed. To watch a new vendor, add a `- name:` entry to `config/watchlist.yaml`, with `aliases` for its product names and `exclude` for phrases that cause false hits. To add a source, add any RSS or Atom feed URL to `config/feeds.yaml`, such as vendor security blogs, CERT advisories, or your industry's ISAC. Changes take effect on the next run.

## How it works

```
feeds.yaml ──► fetch RSS/Atom ──► clean HTML ──► match against watchlist.yaml ──► risk_feed.csv ──► SIEM
```

1. Pulls every feed listed in `config/feeds.yaml`.
2. Strips HTML from titles and summaries.
3. Checks each article against the vendors, aliases and exclusions in `config/watchlist.yaml`.
4. Writes matching articles to `risk_feed.csv`.

Matching is case-insensitive and uses word boundaries, so `Zoom` matches "Zoom patches client bug" but not "Zoominfo". Aliases roll up to the parent vendor, so an "Entra ID flaw" headline is logged as `Microsoft`.

## Quick start

Requires Python 3.8+.

```bash
git clone https://github.com/cybersanctum/vendor-risk-radar.git
cd vendor-risk-radar
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
python -m pip install -r requirements.txt
python riskfeed.py
```

Example output:

```
[+] BleepingComputer: 15 articles
    [HIT] Microsoft: Microsoft patches Exchange Online zero-day
[+] The Hacker News: 50 articles
[+] Wrote 1 rows to risk_feed.csv
```

## Configuration

### `config/watchlist.yaml`: who to watch

```yaml
vendors:
  - name: Microsoft
    aliases: [Azure, Entra, Exchange Online, Microsoft 365, M365]
  - name: Zoom
    exclude: [zoom in, zoom out]
```

| Field     | Required | Purpose |
|-----------|----------|---------|
| `name`    | yes      | Vendor name written to the CSV `vendor` column |
| `aliases` | no       | Product or brand names that also count as this vendor |
| `exclude` | no       | Phrases that contain the name but aren't about the vendor |

The included list is only an example. Replace it with the vendors your organization actually uses.

### `config/feeds.yaml`: where to look

```yaml
feeds:
  - name: BleepingComputer
    url: https://www.bleepingcomputer.com/feed/
```

Any RSS or Atom feed works. `name` is shown in the console output.

## Output

`risk_feed.csv` is UTF-8 with a header row:

| Column    | Example |
|-----------|---------|
| `vendor`  | `Microsoft` (multiple vendors are joined with `;`) |
| `title`   | `Microsoft patches Exchange Online zero-day` |
| `link`    | `https://...` |
| `summary` | Plain-text summary with HTML removed |

## Sending it to a SIEM

Point your SIEM's file monitor or forwarder at `risk_feed.csv`. For example, a Splunk Universal Forwarder `inputs.conf` stanza:

```ini
[monitor://C:\path\to\vendor-risk-radar\risk_feed.csv]
sourcetype = csv
index = threat_intel
```

## Running on a schedule

- **Windows:** Task Scheduler → Create Basic Task → run `C:\path\to\vendor-risk-radar\.venv\Scripts\python.exe` with argument `C:\path\to\vendor-risk-radar\riskfeed.py`.
- **macOS/Linux (cron, hourly):**
  ```
  0 * * * * /path/to/vendor-risk-radar/.venv/bin/python /path/to/vendor-risk-radar/riskfeed.py
  ```

The script finds its config files relative to its own location, so it can be run from any working directory.

## Limitations

- Matching is keyword-based. A vendor named in passing ("unlike Microsoft, ...") is still a hit. Tune with `exclude`.
- Only the title and summary are checked, not the full article.
- The CSV is rewritten on each run, and repeat runs can include the same article again.

## Roadmap

- [ ] De-duplicate articles across runs and feeds
- [ ] Append mode with a `detected_at` timestamp for SIEM event indexing
- [ ] Optional JSON output
- [ ] Unit tests

## License

MIT. See [LICENSE](LICENSE).
