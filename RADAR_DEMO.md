# Local Radar Demo

This demonstrates the Local Radar functionality for NYC civic/OSINT monitoring.

## Installation & Setup

```bash
# Install dependencies
pip install pyyaml feedparser pdfminer.six beautifulsoup4

# Initialize configuration
python cli/radar_cli.py init
```

## Usage Examples

### Basic Daily Run
```bash
# Fetch from all sources, process changes, generate reports
python cli/radar_cli.py run --mode daily
```

### Full Pipeline (Daily + Weekly)
```bash
# Run both daily and weekly processing
python cli/radar_cli.py run --mode all
```

### Generate Reports from Cache
```bash
# Regenerate daily report from existing data
python cli/radar_cli.py report --kind daily

# Regenerate weekly report
python cli/radar_cli.py report --kind weekly
```

## Configuration

The system uses `config/watchlist.yaml` with NYC-focused sources:

### Feeds Monitored:
- NYC Council Legislation & Calendar
- NY Governor Press Releases  
- Federal Register (Broadband/Housing/Infrastructure)
- FCC Daily Digest
- NTIA & HUD Press Releases

### HTML Pages Tracked:
- NYC Mayor News Index
- MTA Press Releases
- NYC OTI Broadband Initiative
- NYC HPD Policy Announcements
- PSC Regulatory Dockets

### Topics Tracked:
1. **NYC Congestion Pricing** - MTA tolling, CBD fees
2. **NYC Housing & Zoning Reform** - HPD policy, inclusionary housing
3. **NYC/State Broadband & Digital Equity** - NTIA programs, PSC orders
4. **Climate Resilience NYC Waterfront** - flood mitigation, storm surge

## Output Structure

```
.radar/
├── snapshots_index.jsonl          # Change tracking
├── snapshots/                     # Raw content by source
└── reports/
    ├── daily/                     # Daily analysis reports
    ├── weekly/                    # Weekly summaries
    └── dossiers/                  # Living topic files
```

## Features

- **Ethical Scraping**: Respects robots.txt, rate-limited to 6 requests/minute per domain
- **Change Detection**: SHA256 content hashing with unified diffs
- **Relevance Filtering**: Keyword matching and tag-based filtering
- **LLM Analysis**: Automated report generation and topic analysis
- **Provenance Tracking**: Full audit trail of all content changes