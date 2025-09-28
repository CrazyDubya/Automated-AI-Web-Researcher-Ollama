"""
HTML Report Generator for Local Radar
Generates daily/weekly briefs and dossiers in HTML format with static index
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from pathlib import Path
import logging

from .base import ReportEntry, ResearchBrief, Dossier
from .config import config
from .security import (
    sanitize_html, escape_html, validate_filename, safe_path_join,
    validate_tag, validate_url, secure_delete_file, log_security_event
)


class HTMLReportGenerator:
    """Generates HTML reports from research data"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.config.ensure_directories()
        
        # Set up Jinja2 environment with auto-escaping enabled for security
        template_loader = FileSystemLoader(self.config.report.template_dir)
        self.env = Environment(
            loader=template_loader,
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters for additional security
        self.env.filters['sanitize_html'] = sanitize_html
        self.env.filters['escape_html'] = escape_html
        
        # Create templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default HTML templates if they don't exist"""
        templates = {
            'index.html': self._get_index_template(),
            'brief.html': self._get_brief_template(),
            'dossier.html': self._get_dossier_template()
        }
        
        for template_name, template_content in templates.items():
            template_path = Path(self.config.report.template_dir) / template_name
            if not template_path.exists():
                template_path.write_text(template_content)
        
        # Create CSS file
        css_path = Path(self.config.report.static_dir) / 'style.css'
        if not css_path.exists():
            css_path.write_text(self._get_default_css())
        
        # Create JavaScript file
        js_path = Path(self.config.report.static_dir) / 'app.js'
        if not js_path.exists():
            js_path.write_text(self._get_default_js())
    
    def generate_daily_brief(self, entries: List[ReportEntry]) -> ResearchBrief:
        """Generate a daily research brief with security validation"""
        try:
            # Validate and sanitize entries
            validated_entries = []
            for entry in entries:
                validated_entry = self._validate_report_entry(entry)
                if validated_entry:
                    validated_entries.append(validated_entry)
            
            today = datetime.now()
            date_range = today.strftime("%Y-%m-%d")
            
            # Extract and validate unique tags
            all_tags = set()
            for entry in validated_entries:
                for tag in entry.tags:
                    try:
                        safe_tag = validate_tag(tag)
                        all_tags.add(safe_tag)
                    except Exception as e:
                        self.logger.warning(f"Invalid tag '{tag}' removed: {e}")
            
            # Generate summary using LLM if available
            summary = self._generate_summary(validated_entries, "daily")
            
            brief = ResearchBrief(
                brief_type="daily",
                date_range=date_range,
                entries=validated_entries,
                summary=summary,
                tags=list(all_tags),
                generated_at=datetime.now()
            )
            
            return brief
        except Exception as e:
            self.logger.error(f"Error generating daily brief: {e}")
            log_security_event("REPORT_GENERATION_ERROR", {
                "brief_type": "daily",
                "error": str(e)
            })
            raise
    
    def generate_weekly_brief(self, entries: List[ReportEntry]) -> ResearchBrief:
        """Generate a weekly research brief"""
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        date_range = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        
        # Extract unique tags
        all_tags = set()
        for entry in entries:
            all_tags.update(entry.tags)
        
        # Generate summary
        summary = self._generate_summary(entries, "weekly")
        
        brief = ResearchBrief(
            brief_type="weekly",
            date_range=date_range,
            entries=entries,
            summary=summary,
            tags=list(all_tags),
            generated_at=datetime.now()
        )
        
        return brief
    
    def generate_dossier(self, topic: str, entries: List[ReportEntry]) -> Dossier:
        """Generate a research dossier on a specific topic"""
        # Extract unique tags
        all_tags = set()
        for entry in entries:
            all_tags.update(entry.tags)
        
        # Generate analysis
        analysis = self._generate_analysis(entries, topic)
        
        now = datetime.now()
        dossier = Dossier(
            topic=topic,
            description=f"Research dossier on {topic}",
            entries=entries,
            analysis=analysis,
            created_at=now,
            updated_at=now,
            tags=list(all_tags)
        )
        
        return dossier
    
    def export_to_html(self, data: Any, template_name: str) -> str:
        """Export report data to HTML format"""
        try:
            template = self.env.get_template(template_name)
            return template.render(data=data, config=self.config)
        except Exception as e:
            print(f"Error rendering template {template_name}: {e}")
            return f"<html><body><h1>Error</h1><p>{e}</p></body></html>"
    
    def save_brief_html(self, brief: ResearchBrief) -> str:
        """Save brief as HTML file and return filename"""
        html_content = self.export_to_html(brief, 'brief.html')
        
        # Generate filename
        safe_date = brief.date_range.replace(" to ", "_").replace("-", "_")
        filename = f"{brief.brief_type}_brief_{safe_date}.html"
        filepath = Path(self.config.report.output_dir) / filename
        
        # Write HTML file
        filepath.write_text(html_content)
        
        return filename
    
    def save_dossier_html(self, dossier: Dossier) -> str:
        """Save dossier as HTML file and return filename"""
        html_content = self.export_to_html(dossier, 'dossier.html')
        
        # Generate filename
        safe_topic = "".join(c for c in dossier.topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_topic = safe_topic.replace(' ', '_')
        filename = f"dossier_{safe_topic}.html"
        filepath = Path(self.config.report.output_dir) / filename
        
        # Write HTML file
        filepath.write_text(html_content)
        
        return filename
    
    def generate_index(self) -> str:
        """Generate static index dashboard with links to all reports"""
        reports_dir = Path(self.config.report.output_dir)
        
        # Scan for existing reports
        briefs = []
        dossiers = []
        all_tags = set()
        
        for file_path in reports_dir.glob("*.html"):
            if file_path.name.startswith(('daily_brief_', 'weekly_brief_')):
                brief_info = self._extract_brief_info(file_path)
                if brief_info:
                    briefs.append(brief_info)
                    all_tags.update(brief_info.get('tags', []))
            elif file_path.name.startswith('dossier_'):
                dossier_info = self._extract_dossier_info(file_path)
                if dossier_info:
                    dossiers.append(dossier_info)
                    all_tags.update(dossier_info.get('tags', []))
        
        # Sort by date
        briefs.sort(key=lambda x: x.get('date', ''), reverse=True)
        dossiers.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        # Generate index HTML
        index_data = {
            'briefs': briefs,
            'dossiers': dossiers,
            'all_tags': sorted(list(all_tags)),
            'generated_at': datetime.now(),
            'total_briefs': len(briefs),
            'total_dossiers': len(dossiers)
        }
        
        html_content = self.export_to_html(index_data, 'index.html')
        
        # Save index file
        index_path = reports_dir / 'index.html'
        index_path.write_text(html_content)
        
        return str(index_path)
    
    def _generate_summary(self, entries: List[ReportEntry], brief_type: str) -> str:
        """Generate summary for a brief"""
        if not entries:
            return f"No entries found for this {brief_type} brief."
        
        # Basic summary generation (can be enhanced with LLM integration)
        total_entries = len(entries)
        unique_sources = len(set(entry.source_url for entry in entries))
        avg_confidence = sum(entry.confidence_score for entry in entries) / total_entries if total_entries > 0 else 0
        
        summary = f"This {brief_type} brief contains {total_entries} research entries from {unique_sources} unique sources. "
        summary += f"Average confidence score: {avg_confidence:.2f}. "
        
        # Add top tags
        tag_counts = {}
        for entry in entries:
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            tag_list = [f"{tag} ({count})" for tag, count in top_tags]
            summary += f"Top topics: {', '.join(tag_list)}."
        
        return summary
    
    def _generate_analysis(self, entries: List[ReportEntry], topic: str) -> str:
        """Generate analysis for a dossier"""
        if not entries:
            return f"No research entries found for topic: {topic}"
        
        # Basic analysis generation
        total_entries = len(entries)
        date_range = ""
        if entries:
            dates = [entry.timestamp for entry in entries if entry.timestamp]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                date_range = f" spanning from {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        
        analysis = f"Research analysis for '{topic}' based on {total_entries} entries{date_range}. "
        
        # Analyze confidence scores
        confidences = [entry.confidence_score for entry in entries if entry.confidence_score > 0]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            high_confidence_count = len([c for c in confidences if c >= 0.8])
            analysis += f"Average confidence: {avg_confidence:.2f}. "
            analysis += f"{high_confidence_count} high-confidence entries (≥0.8). "
        
        return analysis
    
    def _extract_brief_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract brief information from HTML file"""
        try:
            # Try to find corresponding JSON metadata file
            json_path = file_path.with_suffix('.json')
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
            
            # Basic info from filename
            filename = file_path.stem
            if filename.startswith('daily_brief_'):
                date_part = filename[12:]  # Remove 'daily_brief_'
                return {
                    'filename': file_path.name,
                    'type': 'daily',
                    'date': date_part.replace('_', '-'),
                    'tags': []
                }
            elif filename.startswith('weekly_brief_'):
                date_part = filename[13:]  # Remove 'weekly_brief_'
                return {
                    'filename': file_path.name,
                    'type': 'weekly', 
                    'date': date_part.replace('_', '-'),
                    'tags': []
                }
        except Exception:
            pass
        
        return None
    
    def _extract_dossier_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract dossier information from HTML file"""
        try:
            # Try to find corresponding JSON metadata file
            json_path = file_path.with_suffix('.json')
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
            
            # Basic info from filename
            filename = file_path.stem
            if filename.startswith('dossier_'):
                topic = filename[8:].replace('_', ' ')  # Remove 'dossier_'
                return {
                    'filename': file_path.name,
                    'topic': topic,
                    'updated_at': datetime.now().isoformat(),
                    'tags': []
                }
        except Exception:
            pass
        
        return None
    
    def _get_index_template(self) -> str:
        """Default index template"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Radar - Research Dashboard</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Local Radar Dashboard</h1>
            <p>Research briefs and dossiers generated on {{ data.generated_at.strftime('%Y-%m-%d %H:%M') }}</p>
            <div class="stats">
                <span class="stat">{{ data.total_briefs }} Briefs</span>
                <span class="stat">{{ data.total_dossiers }} Dossiers</span>
            </div>
        </header>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search reports...">
            </div>
            <div class="filter-tags">
                <label>Filter by tags:</label>
                <select id="tagFilter">
                    <option value="">All tags</option>
                    {% for tag in data.all_tags %}
                    <option value="{{ tag }}">{{ tag }}</option>
                    {% endfor %}
                </select>
            </div>
        </div>
        
        <main>
            <section class="briefs-section">
                <h2>Research Briefs</h2>
                <div class="grid" id="briefsGrid">
                    {% for brief in data.briefs %}
                    <div class="card brief-card" data-tags="{{ brief.tags|join(',') }}">
                        <h3><a href="{{ brief.filename }}">{{ brief.type|title }} Brief</a></h3>
                        <p class="date">{{ brief.date }}</p>
                        <div class="tags">
                            {% for tag in brief.tags %}
                            <span class="tag">{{ tag }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </section>
            
            <section class="dossiers-section">
                <h2>Research Dossiers</h2>
                <div class="grid" id="dossiersGrid">
                    {% for dossier in data.dossiers %}
                    <div class="card dossier-card" data-tags="{{ dossier.tags|join(',') }}">
                        <h3><a href="{{ dossier.filename }}">{{ dossier.topic }}</a></h3>
                        <p class="date">Updated: {{ dossier.updated_at[:10] }}</p>
                        <div class="tags">
                            {% for tag in dossier.tags %}
                            <span class="tag">{{ tag }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </section>
        </main>
    </div>
    
    <script src="static/app.js"></script>
</body>
</html>'''
    
    def _get_brief_template(self) -> str:
        """Default brief template"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.brief_type|title }} Brief - {{ data.date_range }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ data.brief_type|title }} Research Brief</h1>
            <p>{{ data.date_range }}</p>
            <div class="metadata">
                <span>Generated: {{ data.generated_at.strftime('%Y-%m-%d %H:%M') }}</span>
                <span>Entries: {{ data.entries|length }}</span>
            </div>
        </header>
        
        <nav>
            <a href="index.html">← Back to Dashboard</a>
        </nav>
        
        <main>
            <section class="summary">
                <h2>Summary</h2>
                <p>{{ data.summary }}</p>
                
                <div class="tags">
                    {% for tag in data.tags %}
                    <span class="tag">{{ tag }}</span>
                    {% endfor %}
                </div>
            </section>
            
            <section class="entries">
                <h2>Research Entries</h2>
                {% for entry in data.entries %}
                <article class="entry">
                    <h3>{{ entry.title }}</h3>
                    <div class="entry-meta">
                        <span class="source"><a href="{{ entry.source_url }}" target="_blank">Source</a></span>
                        <span class="timestamp">{{ entry.timestamp.strftime('%Y-%m-%d %H:%M') }}</span>
                        <span class="confidence">Confidence: {{ (entry.confidence_score * 100)|round(1) }}%</span>
                    </div>
                    <div class="content">{{ entry.content }}</div>
                    <div class="entry-tags">
                        {% for tag in entry.tags %}
                        <span class="tag small">{{ tag }}</span>
                        {% endfor %}
                    </div>
                </article>
                {% endfor %}
            </section>
        </main>
    </div>
</body>
</html>'''
    
    def _get_dossier_template(self) -> str:
        """Default dossier template"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dossier: {{ data.topic }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Research Dossier</h1>
            <h2>{{ data.topic }}</h2>
            <p>{{ data.description }}</p>
            <div class="metadata">
                <span>Created: {{ data.created_at.strftime('%Y-%m-%d %H:%M') }}</span>
                <span>Updated: {{ data.updated_at.strftime('%Y-%m-%d %H:%M') }}</span>
                <span>Entries: {{ data.entries|length }}</span>
            </div>
        </header>
        
        <nav>
            <a href="index.html">← Back to Dashboard</a>
        </nav>
        
        <main>
            <section class="analysis">
                <h2>Analysis</h2>
                <p>{{ data.analysis }}</p>
                
                <div class="tags">
                    {% for tag in data.tags %}
                    <span class="tag">{{ tag }}</span>
                    {% endfor %}
                </div>
            </section>
            
            <section class="entries">
                <h2>Research Entries</h2>
                {% for entry in data.entries %}
                <article class="entry">
                    <h3>{{ entry.title }}</h3>
                    <div class="entry-meta">
                        <span class="source"><a href="{{ entry.source_url }}" target="_blank">Source</a></span>
                        <span class="timestamp">{{ entry.timestamp.strftime('%Y-%m-%d %H:%M') }}</span>
                        <span class="confidence">Confidence: {{ (entry.confidence_score * 100)|round(1) }}%</span>
                    </div>
                    <div class="content">{{ entry.content }}</div>
                    <div class="entry-tags">
                        {% for tag in entry.tags %}
                        <span class="tag small">{{ tag }}</span>
                        {% endfor %}
                    </div>
                </article>
                {% endfor %}
            </section>
        </main>
    </div>
</body>
</html>'''
    
    def _get_default_css(self) -> str:
        """Default CSS styles"""
        return '''/* Local Radar Dashboard Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background-color: white;
    min-height: 100vh;
}

header {
    text-align: center;
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 2px solid #007acc;
}

header h1 {
    color: #007acc;
    margin-bottom: 10px;
}

.stats, .metadata {
    margin-top: 15px;
}

.stat, .metadata span {
    display: inline-block;
    margin: 0 10px;
    padding: 5px 10px;
    background-color: #f0f8ff;
    border-radius: 5px;
    font-size: 0.9em;
}

.controls {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
    align-items: center;
    flex-wrap: wrap;
}

.search-box input, .filter-tags select {
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 5px;
    font-size: 16px;
}

.search-box input {
    width: 300px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.card h3 {
    margin-bottom: 10px;
}

.card h3 a {
    color: #007acc;
    text-decoration: none;
}

.card h3 a:hover {
    text-decoration: underline;
}

.date {
    color: #666;
    font-size: 0.9em;
    margin-bottom: 10px;
}

.tags {
    margin-top: 10px;
}

.tag {
    display: inline-block;
    background-color: #e7f3ff;
    color: #007acc;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    margin-right: 5px;
    margin-bottom: 3px;
}

.tag.small {
    font-size: 0.7em;
    padding: 1px 6px;
}

nav {
    margin-bottom: 20px;
}

nav a {
    color: #007acc;
    text-decoration: none;
    font-weight: bold;
}

nav a:hover {
    text-decoration: underline;
}

.summary, .analysis {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
}

.entries {
    margin-top: 30px;
}

.entry {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

.entry h3 {
    color: #007acc;
    margin-bottom: 10px;
}

.entry-meta {
    display: flex;
    gap: 15px;
    margin-bottom: 15px;
    flex-wrap: wrap;
}

.entry-meta span {
    font-size: 0.9em;
    color: #666;
}

.entry-meta a {
    color: #007acc;
    text-decoration: none;
}

.entry-meta a:hover {
    text-decoration: underline;
}

.content {
    line-height: 1.6;
    margin-bottom: 15px;
}

.entry-tags {
    margin-top: 10px;
}

section {
    margin-bottom: 40px;
}

section h2 {
    color: #333;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .controls {
        flex-direction: column;
        align-items: stretch;
    }
    
    .search-box input {
        width: 100%;
    }
    
    .grid {
        grid-template-columns: 1fr;
    }
    
    .entry-meta {
        flex-direction: column;
        gap: 5px;
    }
}'''
    
    def _get_default_js(self) -> str:
        """Default JavaScript for interactive features"""
        return '''// Local Radar Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const tagFilter = document.getElementById('tagFilter');
    const briefsGrid = document.getElementById('briefsGrid');
    const dossiersGrid = document.getElementById('dossiersGrid');
    
    // Search functionality
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterContent();
        });
    }
    
    // Tag filter functionality
    if (tagFilter) {
        tagFilter.addEventListener('change', function() {
            filterContent();
        });
    }
    
    function filterContent() {
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const selectedTag = tagFilter ? tagFilter.value : '';
        
        // Filter briefs
        if (briefsGrid) {
            const briefCards = briefsGrid.querySelectorAll('.card');
            briefCards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                const tags = card.dataset.tags || '';
                
                const matchesSearch = title.includes(searchTerm);
                const matchesTag = !selectedTag || tags.includes(selectedTag);
                
                card.style.display = (matchesSearch && matchesTag) ? 'block' : 'none';
            });
        }
        
        // Filter dossiers
        if (dossiersGrid) {
            const dossierCards = dossiersGrid.querySelectorAll('.card');
            dossierCards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                const tags = card.dataset.tags || '';
                
                const matchesSearch = title.includes(searchTerm);
                const matchesTag = !selectedTag || tags.includes(selectedTag);
                
                card.style.display = (matchesSearch && matchesTag) ? 'block' : 'none';
            });
        }
    }
    
    // Auto-refresh functionality (if enabled)
    const autoRefreshInterval = 300000; // 5 minutes
    if (window.location.pathname.endsWith('index.html')) {
        setInterval(() => {
            window.location.reload();
        }, autoRefreshInterval);
    }
});'''
    
    def _validate_report_entry(self, entry: ReportEntry) -> ReportEntry:
        """
        Validate and sanitize a report entry for security
        
        Args:
            entry: Raw report entry
            
        Returns:
            Validated and sanitized report entry
            
        Raises:
            ValueError: If entry is invalid
        """
        if not entry:
            raise ValueError("Report entry cannot be None")
        
        # Validate and sanitize title
        if not entry.title or not entry.title.strip():
            raise ValueError("Report entry must have a title")
        safe_title = sanitize_html(str(entry.title).strip())
        
        # Validate and sanitize content  
        if not entry.content or not entry.content.strip():
            raise ValueError("Report entry must have content")
        safe_content = sanitize_html(str(entry.content).strip())
        
        # Validate URL
        if entry.source_url and not validate_url(entry.source_url):
            self.logger.warning(f"Invalid URL in entry '{safe_title}': {entry.source_url}")
            log_security_event("INVALID_URL_DETECTED", {
                "title": safe_title,
                "url": entry.source_url
            })
            # Don't fail, just log and continue with empty URL
            safe_url = ""
        else:
            safe_url = entry.source_url or ""
        
        # Validate and sanitize tags
        safe_tags = []
        for tag in entry.tags:
            try:
                safe_tag = validate_tag(tag)
                safe_tags.append(safe_tag)
            except Exception as e:
                self.logger.warning(f"Invalid tag '{tag}' in entry '{safe_title}': {e}")
        
        # Validate confidence score
        safe_confidence = float(entry.confidence_score) if isinstance(entry.confidence_score, (int, float)) else 0.0
        safe_confidence = max(0.0, min(1.0, safe_confidence))  # Clamp to 0-1 range
        
        # Validate timestamp
        safe_timestamp = entry.timestamp if isinstance(entry.timestamp, datetime) else datetime.now()
        
        # Validate metadata
        safe_metadata = {}
        if isinstance(entry.metadata, dict):
            for key, value in entry.metadata.items():
                # Sanitize metadata keys and values
                safe_key = escape_html(str(key)[:50])  # Limit key length
                if isinstance(value, str):
                    safe_value = escape_html(value[:500])  # Limit value length
                elif isinstance(value, (int, float, bool)):
                    safe_value = value
                else:
                    safe_value = escape_html(str(value)[:500])
                safe_metadata[safe_key] = safe_value
        
        return ReportEntry(
            title=safe_title,
            content=safe_content,
            source_url=safe_url,
            timestamp=safe_timestamp,
            tags=safe_tags,
            confidence_score=safe_confidence,
            metadata=safe_metadata
        )