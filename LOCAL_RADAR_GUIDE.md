# Local Radar Enhancement - User Guide

Local Radar is a production-oriented enhancement for the Automated AI Web Researcher that provides HTML report generation, PDF crawling capabilities, vector embeddings, and interactive CLI features.

## Features

### 1. HTML Report Generation
- **Daily Briefs**: Generate daily research briefs with entries from the past 24 hours
- **Weekly Briefs**: Generate weekly research summaries  
- **Dossiers**: Create topic-specific research dossiers
- **Static Index**: Interactive dashboard with tag filtering and search

### 2. PDF Pattern Crawling
- **Pattern-based URL discovery**: Use glob patterns to find PDF documents
- **Batch processing**: Configurable concurrency and batch sizes
- **Text extraction**: PDFMiner with OCR fallback using Tesseract
- **Automatic indexing**: Extracted content added to vector index

### 3. Vector Embeddings & RAG (Trailkeeper)
- **Semantic search**: Find similar content using embeddings or TF-IDF
- **Document indexing**: Automatic indexing of research entries and PDFs
- **Semantic diff**: Compare documents for changes
- **Sentence-level analysis**: Detect added, deleted, and modified sentences

### 4. Interactive CLI
- **Integrated commands**: Seamless integration with existing research CLI
- **Search capabilities**: Query indexed content
- **Report management**: Generate and list reports
- **System monitoring**: Status and configuration information

## Installation

The Local Radar features are included in the main installation. For full functionality, install additional dependencies:

```bash
pip install sentence-transformers faiss-cpu scikit-learn nltk pytesseract Pillow
```

For OCR functionality, also install Tesseract:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

### Starting the System

Run the main researcher as usual:
```bash
python Web-LLM.py
```

Local Radar commands are available using the `#` prefix:

### Basic Commands

#### Help and Status
```
#lr_help                 # Show all available commands
#lr_status               # Show system status
#lr_config               # Show configuration
```

#### Report Generation
```
#lr_generate_daily       # Generate daily brief
#lr_generate_weekly      # Generate weekly brief
#lr_generate_dossier AI research trends    # Generate topic dossier
#lr_list_reports         # List all generated reports
```

#### PDF Crawling
```
#lr_crawl_pdfs           # Crawl all configured sources
#lr_crawl_pdfs https://example.com/docs/*.pdf  # Crawl specific pattern
```

#### Search and Analysis
```
#lr_search artificial intelligence     # Search indexed content
#lr_semantic_diff doc1_id doc2_id     # Compare documents
#lr_index_stats         # Show vector index statistics
```

### Configuration

Local Radar uses a configuration file `local_radar_config.json` that's automatically created with default settings. You can modify:

- **Report settings**: Output directories, templates, page limits
- **PDF crawling**: Batch sizes, concurrency, OCR languages
- **Vector index**: Embedding models, similarity thresholds
- **CLI options**: History, autocomplete settings

### PDF Source Configuration

Create a `pdf_sources.json` file to configure PDF crawling sources:

```json
[
  {
    "name": "Research Papers",
    "url_pattern": "https://arxiv.org/pdf/cs.AI/*.pdf",
    "description": "AI research papers from arXiv",
    "enabled": true,
    "max_pages": 10
  },
  {
    "name": "Company Reports", 
    "url_pattern": "https://company.com/reports/{2020..2024}.pdf",
    "description": "Annual reports",
    "enabled": true
  }
]
```

### Generated Reports

Reports are saved in the `reports/` directory:

- **Daily briefs**: `daily_brief_YYYY_MM_DD.html`
- **Weekly briefs**: `weekly_brief_YYYY_MM_DD_to_YYYY_MM_DD.html`  
- **Dossiers**: `dossier_Topic_Name.html`
- **Index**: `index.html` - Interactive dashboard

### Integration with Research Workflow

Local Radar seamlessly integrates with the existing research workflow:

1. **During Research**: Content is automatically indexed as it's discovered
2. **After Research**: Generate reports from indexed content
3. **Ongoing Analysis**: Search and compare research findings
4. **Knowledge Management**: Build dossiers on specific topics

## Architecture

### Components

- **LocalRadarConfig**: Centralized configuration management
- **HTMLReportGenerator**: Template-based HTML report generation
- **PDFPatternCrawler**: Pattern-based PDF discovery and extraction
- **VectorIndex**: Semantic search and document comparison
- **LocalRadarCLI**: Interactive command interface

### Data Flow

1. **Input**: Research entries, PDF documents, manual queries
2. **Processing**: Text extraction, embedding generation, indexing
3. **Storage**: Vector index, metadata, extracted content
4. **Output**: HTML reports, search results, analysis

### Fallback Behavior

Local Radar gracefully handles missing dependencies:

- **No sentence-transformers**: Falls back to TF-IDF similarity
- **No scikit-learn**: Uses basic text matching
- **No Tesseract**: PDF extraction without OCR
- **No NLTK**: Simple sentence splitting

## Troubleshooting

### Common Issues

1. **Import errors**: Install missing dependencies with pip
2. **Permission errors**: Ensure write access to output directories  
3. **PDF extraction fails**: Check URL patterns and network access
4. **Empty search results**: Verify documents are indexed correctly

### Performance Optimization

- **Batch size**: Reduce PDF batch size for limited memory
- **Concurrency**: Adjust based on network and CPU capacity
- **Index size**: Monitor vector index size and clear if needed
- **Template caching**: Templates are cached for better performance

### Logging

Logs are written to `logs/` directory:
- Main system: `web_llm.log`
- Research: `research_llm.log` 
- Local Radar components write to the main logger

## Examples

### Example 1: Daily Research Brief

```bash
# Start researcher
python Web-LLM.py

# Conduct research
@analyze recent AI developments in healthcare

# Generate daily brief
#lr_generate_daily

# View reports
#lr_list_reports
```

### Example 2: PDF Analysis Workflow

```bash
# Configure PDF sources (edit pdf_sources.json)
# Crawl PDFs
#lr_crawl_pdfs

# Search extracted content  
#lr_search machine learning healthcare

# Generate topic dossier
#lr_generate_dossier healthcare AI applications
```

### Example 3: Content Comparison

```bash
# Search for documents
#lr_search AI ethics

# Compare two documents semantically
#lr_semantic_diff doc_id_1 doc_id_2

# Check index statistics
#lr_index_stats
```

## Advanced Features

### Custom Templates

Modify HTML templates in `local_radar/templates/`:
- `index.html`: Dashboard template
- `brief.html`: Brief report template  
- `dossier.html`: Dossier template

### Extending Search

The vector index supports:
- Semantic similarity search
- Exact text matching
- Tag-based filtering
- Metadata queries

### API Integration

Local Radar components can be used programmatically:

```python
from local_radar import LocalRadarConfig, VectorIndex
from local_radar.report_generator import HTMLReportGenerator

# Initialize components
config = LocalRadarConfig()
generator = HTMLReportGenerator()
vector_index = VectorIndex()

# Add content and generate reports
# ... your code here ...
```

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify configuration and dependencies
3. Test with simple examples
4. Review the source code for advanced usage

Local Radar enhances the research workflow with production-ready features while maintaining the simplicity and power of the original system.