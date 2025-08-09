#!/usr/bin/env python3
"""
Static Web UI Build Script.
Generates static HTML interface for radar system.
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.radar.config import get_radar_config, ensure_radar_dirs

logger = logging.getLogger(__name__)


class StaticUIBuilder:
    """Builder for static web UI."""
    
    def __init__(self, output_dir: Optional[str] = None):
        config = get_radar_config()
        self.output_dir = Path(output_dir or config.get('reports.web_output_dir', 'reports/web'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_index_html(self, dossiers: List[Dict], search_index: List[Dict]) -> str:
        """Generate main index.html page."""
        
        # Get latest briefings
        recent_briefs = sorted(dossiers, key=lambda x: x.get('date', ''), reverse=True)[:10]
        
        # Extract unique tags
        all_tags = set()
        for dossier in dossiers:
            tags = dossier.get('tags', [])
            if isinstance(tags, list):
                all_tags.update(tags)
            elif isinstance(tags, str):
                all_tags.add(tags)
        
        sorted_tags = sorted(all_tags)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radar Research Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 2.5rem;
        }}
        
        .header p {{
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }}
        
        .dashboard {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }}
        
        .card {{
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .card h2 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #eee;
            padding-bottom: 0.5rem;
        }}
        
        .brief-item {{
            border-left: 4px solid #667eea;
            padding: 0.5rem 1rem;
            margin: 0.5rem 0;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        }}
        
        .brief-item h3 {{
            margin: 0 0 0.5rem 0;
            font-size: 1rem;
        }}
        
        .brief-item .meta {{
            font-size: 0.8rem;
            color: #666;
        }}
        
        .tag-filter {{
            margin-bottom: 1rem;
        }}
        
        .tag {{
            display: inline-block;
            background: #e9ecef;
            color: #495057;
            padding: 0.2rem 0.5rem;
            margin: 0.2rem;
            border-radius: 15px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .tag:hover {{
            background: #667eea;
            color: white;
        }}
        
        .tag.active {{
            background: #667eea;
            color: white;
        }}
        
        .search-box {{
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
            margin-bottom: 1rem;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: white;
            padding: 1rem;
            border-radius: 5px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .stat-number {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
        }}
        
        @media (max-width: 768px) {{
            .dashboard {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            body {{
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Radar Research Dashboard</h1>
        <p>Automated Research Intelligence & Discovery</p>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{len(dossiers)}</div>
            <div class="stat-label">Total Dossiers</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(search_index)}</div>
            <div class="stat-label">Indexed Items</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(sorted_tags)}</div>
            <div class="stat-label">Unique Tags</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(recent_briefs)}</div>
            <div class="stat-label">Recent Briefs</div>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="card">
            <h2>📋 Recent Daily Briefs</h2>
            <input type="text" class="search-box" id="searchBox" placeholder="Search briefs...">
            <div id="briefsList">
"""
        
        # Add recent briefs
        for brief in recent_briefs:
            title = brief.get('title', 'Untitled')
            date = brief.get('date', 'Unknown date')
            source = brief.get('source', 'Unknown source')
            tags = brief.get('tags', [])
            
            tags_html = ' '.join([f'<span class="tag">{tag}</span>' for tag in tags[:3]])
            
            html_content += f"""
                <div class="brief-item" data-tags="{','.join(tags)}" data-title="{title.lower()}">
                    <h3>{title}</h3>
                    <div class="meta">
                        📅 {date} | 📰 {source}
                        <br>
                        {tags_html}
                    </div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
        
        <div class="card">
            <h2>🏷️ Filter by Tags</h2>
            <div class="tag-filter" id="tagFilter">
"""
        
        # Add tag filters
        for tag in sorted_tags[:20]:  # Limit to 20 tags
            html_content += f'<span class="tag" onclick="toggleTag(\'{tag}\')">{tag}</span>\n'
        
        html_content += """
            </div>
            
            <h2>🔍 Quick Search</h2>
            <p>Use the search box above to filter briefs by title or content.</p>
            
            <h2>📊 System Status</h2>
            <div id="systemStatus">
                <p>✅ Radar system operational</p>
                <p>📡 Last update: """ + datetime.now().strftime('%H:%M:%S') + """</p>
            </div>
        </div>
    </div>
    
    <script>
        let selectedTags = new Set();
        
        function toggleTag(tag) {
            if (selectedTags.has(tag)) {
                selectedTags.delete(tag);
            } else {
                selectedTags.add(tag);
            }
            
            updateTagDisplay();
            filterBriefs();
        }
        
        function updateTagDisplay() {
            const tags = document.querySelectorAll('#tagFilter .tag');
            tags.forEach(tag => {
                if (selectedTags.has(tag.textContent)) {
                    tag.classList.add('active');
                } else {
                    tag.classList.remove('active');
                }
            });
        }
        
        function filterBriefs() {
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const briefs = document.querySelectorAll('.brief-item');
            
            briefs.forEach(brief => {
                const title = brief.getAttribute('data-title');
                const tags = brief.getAttribute('data-tags').split(',');
                
                let matchesSearch = title.includes(searchTerm);
                let matchesTags = selectedTags.size === 0 || 
                    [...selectedTags].some(tag => tags.includes(tag));
                
                if (matchesSearch && matchesTags) {
                    brief.style.display = 'block';
                } else {
                    brief.style.display = 'none';
                }
            });
        }
        
        document.getElementById('searchBox').addEventListener('input', filterBriefs);
        
        // Auto-refresh every 5 minutes
        setTimeout(() => {
            location.reload();
        }, 300000);
    </script>
</body>
</html>"""
        
        return html_content
    
    def generate_dossiers_json(self) -> List[Dict]:
        """Generate dossiers.json with topic metadata."""
        # This would normally load from actual dossier data
        # For now, generate sample data
        sample_dossiers = [
            {
                'id': 'dossier_001',
                'title': 'AI Research Trends Q4 2024',
                'date': '2024-12-15',
                'source': 'Research Aggregate',
                'tags': ['AI', 'research', 'trends'],
                'summary': 'Analysis of emerging AI research trends in Q4 2024',
                'url': '/dossiers/ai_trends_q4_2024.html',
                'confidence': 0.85
            },
            {
                'id': 'dossier_002', 
                'title': 'Web Technology Evolution',
                'date': '2024-12-14',
                'source': 'Tech News',
                'tags': ['web', 'technology', 'development'],
                'summary': 'Recent developments in web technology stack',
                'url': '/dossiers/web_tech_evolution.html',
                'confidence': 0.92
            }
        ]
        
        return sample_dossiers
    
    def generate_search_index_json(self) -> List[Dict]:
        """Generate search_index.json with searchable content."""
        # Sample search index data
        sample_index = [
            {
                'id': 'idx_001',
                'source': 'research.org',
                'ts': int(datetime.now().timestamp()),
                'top_sentences': [
                    'Artificial intelligence continues to evolve rapidly.',
                    'Machine learning models are becoming more sophisticated.',
                    'Research in AI ethics is gaining importance.'
                ],
                'tags': ['AI', 'research'],
                'url': 'https://research.org/ai-evolution'
            },
            {
                'id': 'idx_002',
                'source': 'tech-news.com',
                'ts': int(datetime.now().timestamp()) - 3600,
                'top_sentences': [
                    'Web development frameworks are rapidly changing.',
                    'New JavaScript libraries emerge frequently.',
                    'Performance optimization remains crucial.'
                ],
                'tags': ['web', 'development'],
                'url': 'https://tech-news.com/web-frameworks'
            }
        ]
        
        return sample_index
    
    def build_static_ui(self) -> None:
        """Build complete static UI."""
        logger.info(f"Building static UI in {self.output_dir}")
        
        # Generate data
        dossiers = self.generate_dossiers_json()
        search_index = self.generate_search_index_json()
        
        # Write JSON files
        with open(self.output_dir / 'dossiers.json', 'w') as f:
            json.dump(dossiers, f, indent=2)
        
        with open(self.output_dir / 'search_index.json', 'w') as f:
            json.dump(search_index, f, indent=2)
        
        # Generate HTML
        html_content = self.generate_index_html(dossiers, search_index)
        
        with open(self.output_dir / 'index.html', 'w') as f:
            f.write(html_content)
        
        # Create a simple CSS file
        css_content = """
/* Additional styles for radar dashboard */
.fade-in {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.loading {
    opacity: 0.5;
    pointer-events: none;
}
"""
        
        with open(self.output_dir / 'style.css', 'w') as f:
            f.write(css_content)
        
        logger.info(f"Static UI built successfully in {self.output_dir}")
        print(f"✅ Static UI generated at: {self.output_dir.absolute()}")
        print(f"🌐 Open {self.output_dir.absolute()}/index.html in your browser")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Build static web UI for Radar system')
    parser.add_argument(
        '--output-dir',
        help='Output directory for static files',
        default=None
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    # Ensure directories exist
    ensure_radar_dirs()
    
    # Build UI
    builder = StaticUIBuilder(args.output_dir)
    builder.build_static_ui()


if __name__ == '__main__':
    main()