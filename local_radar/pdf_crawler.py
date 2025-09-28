"""
PDF Pattern Crawler for Local Radar
Crawls PDF sources using pattern matching and extracts text with OCR fallback
"""

import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from dataclasses import dataclass
import tempfile
import contextlib

from pdfminer.high_level import extract_text
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO
try:
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF for PDF to image conversion
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .config import config
from .security import validate_url, validate_filename, log_security_event, SecurityError


@dataclass
class PDFSource:
    """Represents a PDF source configuration"""
    name: str
    url_pattern: str
    description: str
    enabled: bool = True
    max_pages: int = 0  # 0 = no limit
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PDFExtractionResult:
    """Result of PDF text extraction"""
    url: str
    text: str
    method: str  # 'pdfminer', 'ocr', 'hybrid'
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PDFPatternCrawler:
    """Crawls PDF sources using pattern matching and extracts text"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set up requests session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Local-Radar-PDF-Crawler/1.0'
        })
        
        # Create output directory
        Path(self.config.pdf.output_dir).mkdir(parents=True, exist_ok=True)
    
    def crawl_pattern(self, url_pattern: str) -> List[str]:
        """Crawl URLs matching a pattern and return PDF URLs"""
        try:
            # Convert glob pattern to regex-style expansion
            pdf_urls = self._expand_pattern(url_pattern)
            
            # Filter valid PDF URLs using HEAD requests
            valid_urls = []
            for url in pdf_urls:
                if self._is_valid_pdf_url(url):
                    valid_urls.append(url)
                
                # Respect rate limiting
                time.sleep(0.1)
            
            self.logger.info(f"Found {len(valid_urls)} valid PDF URLs from pattern: {url_pattern}")
            return valid_urls
            
        except Exception as e:
            self.logger.error(f"Error crawling pattern {url_pattern}: {e}")
            return []
    
    def extract_text(self, pdf_url: str) -> Optional[str]:
        """Extract text from a single PDF URL"""
        result = self._extract_single_pdf(pdf_url)
        return result.text if result.success else None
    
    def extract_text_batch(self, pdf_urls: List[str]) -> Dict[str, Optional[str]]:
        """Extract text from multiple PDFs in batch with concurrency control"""
        results = {}
        
        # Limit batch size
        if len(pdf_urls) > self.config.pdf.batch_size:
            pdf_urls = pdf_urls[:self.config.pdf.batch_size]
        
        # Process in parallel with controlled concurrency
        with ThreadPoolExecutor(max_workers=self.config.pdf.max_concurrent) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self._extract_single_pdf, url): url 
                for url in pdf_urls
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result(timeout=self.config.pdf.timeout_seconds)
                    results[url] = result.text if result.success else None
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {e}")
                    results[url] = None
        
        return results
    
    def get_pdf_sources(self) -> List[PDFSource]:
        """Get configured PDF sources"""
        sources_data = self.config.get_pdf_sources()
        return [
            PDFSource(
                name=source.get('name', ''),
                url_pattern=source.get('url_pattern', ''),
                description=source.get('description', ''),
                enabled=source.get('enabled', True),
                max_pages=source.get('max_pages', 0),
                metadata=source.get('metadata', {})
            )
            for source in sources_data
            if source.get('enabled', True)
        ]
    
    def crawl_all_sources(self) -> Dict[str, List[PDFExtractionResult]]:
        """Crawl all enabled PDF sources and extract text"""
        all_results = {}
        sources = self.get_pdf_sources()
        
        for source in sources:
            if not source.enabled:
                continue
                
            self.logger.info(f"Crawling PDF source: {source.name}")
            
            try:
                # Get PDF URLs for this source
                pdf_urls = self.crawl_pattern(source.url_pattern)
                
                if not pdf_urls:
                    self.logger.warning(f"No PDFs found for source: {source.name}")
                    continue
                
                # Extract text from PDFs
                source_results = []
                for url in pdf_urls:
                    result = self._extract_single_pdf(url)
                    result.metadata['source_name'] = source.name
                    result.metadata['source_pattern'] = source.url_pattern
                    source_results.append(result)
                
                all_results[source.name] = source_results
                
            except Exception as e:
                self.logger.error(f"Error crawling source {source.name}: {e}")
                all_results[source.name] = []
        
        return all_results
    
    def _expand_pattern(self, url_pattern: str) -> List[str]:
        """Expand a URL pattern to concrete URLs"""
        urls = []
        
        # Handle simple wildcard patterns
        if '*' in url_pattern:
            # Try to expand common patterns
            base_url = url_pattern.replace('*', '')
            
            # If it's a simple filename wildcard, try to get directory listing
            if url_pattern.endswith('/*.pdf'):
                directory_url = url_pattern[:-6]  # Remove '*.pdf'
                urls.extend(self._get_directory_pdfs(directory_url))
            
            # Try numeric expansion (e.g., doc{1..10}.pdf)
            elif '{' in url_pattern and '}' in url_pattern:
                urls.extend(self._expand_numeric_pattern(url_pattern))
            
            # Try to find PDFs by parsing HTML page
            else:
                urls.extend(self._find_pdfs_in_page(base_url))
        
        else:
            # Direct PDF URL
            if url_pattern.lower().endswith('.pdf'):
                urls.append(url_pattern)
        
        return list(set(urls))  # Remove duplicates
    
    def _get_directory_pdfs(self, directory_url: str) -> List[str]:
        """Try to get PDF files from a directory listing"""
        pdfs = []
        
        try:
            response = self.session.get(directory_url, timeout=10)
            response.raise_for_status()
            
            # Look for PDF links in the HTML
            pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', response.text, re.IGNORECASE)
            
            for link in pdf_links:
                full_url = urljoin(directory_url, link)
                pdfs.append(full_url)
                
        except Exception as e:
            self.logger.debug(f"Could not get directory listing from {directory_url}: {e}")
        
        return pdfs
    
    def _expand_numeric_pattern(self, pattern: str) -> List[str]:
        """Expand numeric patterns like document{1..10}.pdf"""
        urls = []
        
        # Find {start..end} patterns
        match = re.search(r'\{(\d+)\.\.(\d+)\}', pattern)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            
            for i in range(start, end + 1):
                url = pattern.replace(match.group(0), str(i))
                urls.append(url)
        
        return urls
    
    def _find_pdfs_in_page(self, page_url: str) -> List[str]:
        """Find PDF links in an HTML page"""
        pdfs = []
        
        try:
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()
            
            # Look for PDF links
            pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', response.text, re.IGNORECASE)
            
            for link in pdf_links:
                full_url = urljoin(page_url, link)
                pdfs.append(full_url)
                
        except Exception as e:
            self.logger.debug(f"Could not parse page {page_url}: {e}")
        
        return pdfs
    
    def _is_valid_pdf_url(self, url: str) -> bool:
        """Check if URL points to a valid PDF using HEAD request"""
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            
            # Check status code
            if response.status_code != 200:
                return False
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' in content_type:
                return True
            
            # Check file extension if content-type is not reliable
            if url.lower().endswith('.pdf'):
                return True
            
            # Check content length (avoid huge files)
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.config.pdf.max_file_size_mb:
                    self.logger.warning(f"PDF too large ({size_mb:.1f}MB): {url}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Could not validate PDF URL {url}: {e}")
            return False
    
    def _extract_single_pdf(self, pdf_url: str) -> PDFExtractionResult:
        """Extract text from a single PDF with enhanced security and resource management"""
        self.logger.info(f"Extracting text from: {pdf_url}")
        
        # Validate URL first
        if not validate_url(pdf_url):
            return PDFExtractionResult(
                url=pdf_url,
                text='',
                method='none',
                success=False,
                error='Invalid URL format'
            )
        
        temp_file = None
        try:
            # Download PDF content with size limits
            response = self.session.get(
                pdf_url, 
                timeout=self.config.pdf.timeout_seconds,
                stream=True  # Stream to handle large files
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                log_security_event("SUSPICIOUS_CONTENT_TYPE", {
                    "url": pdf_url,
                    "content_type": content_type
                })
            
            # Read content with size limit
            pdf_content = b''
            total_size = 0
            max_size = self.config.pdf.max_file_size_mb * 1024 * 1024
            
            for chunk in response.iter_content(chunk_size=8192):
                total_size += len(chunk)
                if total_size > max_size:
                    raise Exception(f"PDF file too large: {total_size} bytes (max: {max_size})")
                pdf_content += chunk
            
            if not pdf_content:
                return PDFExtractionResult(
                    url=pdf_url,
                    text='',
                    method='none',
                    success=False,
                    error='Empty PDF content'
                )
            
            # Try pdfminer first
            try:
                text = self._extract_with_pdfminer(pdf_content)
                if text and len(text.strip()) > 50:  # Reasonable amount of text
                    return PDFExtractionResult(
                        url=pdf_url,
                        text=text[:10000],  # Limit text length
                        method='pdfminer',
                        success=True,
                        metadata={
                            'size_bytes': len(pdf_content),
                            'text_length': len(text)
                        }
                    )
            except Exception as e:
                self.logger.debug(f"PDFMiner failed for {pdf_url}: {e}")
            
            # Try OCR fallback if enabled
            if self.config.pdf.enable_ocr and TESSERACT_AVAILABLE:
                try:
                    text = self._extract_with_ocr(pdf_content)
                    if text and len(text.strip()) > 20:
                        return PDFExtractionResult(
                            url=pdf_url,
                            text=text[:10000],  # Limit text length
                            method='ocr',
                            success=True,
                            metadata={
                                'size_bytes': len(pdf_content),
                                'text_length': len(text)
                            }
                        )
                except Exception as e:
                    self.logger.debug(f"OCR failed for {pdf_url}: {e}")
            
            # Both methods failed
            return PDFExtractionResult(
                url=pdf_url,
                text='',
                method='none',
                success=False,
                error='Both pdfminer and OCR extraction failed',
                metadata={'size_bytes': len(pdf_content)}
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting PDF {pdf_url}: {e}")
            return PDFExtractionResult(
                url=pdf_url,
                text='',
                method='none',
                success=False,
                error=str(e)
            )
        finally:
            # Clean up any temporary files
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def _extract_with_pdfminer(self, pdf_content: bytes) -> str:
        """Extract text using pdfminer"""
        output_string = StringIO()
        resource_manager = PDFResourceManager()
        laparams = LAParams()
        
        with StringIO() as temp_string:
            device = TextConverter(resource_manager, temp_string, laparams=laparams)
            interpreter = PDFPageInterpreter(resource_manager, device)
            
            from io import BytesIO
            with BytesIO(pdf_content) as pdf_file:
                for page in PDFPage.get_pages(pdf_file):
                    interpreter.process_page(page)
            
            text = temp_string.getvalue()
        
        return text
    
    def _extract_with_ocr(self, pdf_content: bytes) -> str:
        """Extract text using OCR (tesseract) with enhanced resource management"""
        if not TESSERACT_AVAILABLE:
            raise Exception("Tesseract OCR not available")
        
        doc = None
        try:
            # Convert PDF to images using PyMuPDF
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text_parts = []
            
            # Limit number of pages for performance and security
            max_pages = min(doc.page_count, 10)  # Process at most 10 pages
            
            for page_num in range(max_pages):
                page = doc[page_num]
                
                # Convert page to image with controlled resolution
                mat = fitz.Matrix(2.0, 2.0)  # 2x resolution for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Clean up page resources immediately
                pix = None
                page = None
                
                # Convert to PIL Image and run OCR
                from io import BytesIO
                try:
                    with Image.open(BytesIO(img_data)) as image:
                        # Limit image size for security
                        if image.width * image.height > 4000 * 4000:  # 16M pixels max
                            self.logger.warning(f"Image too large, skipping page {page_num}")
                            continue
                        
                        # Run OCR with configuration
                        ocr_config = '--oem 3 --psm 6'  # Use LSTM OCR engine
                        languages = '+'.join(self.config.pdf.ocr_languages)
                        
                        text = pytesseract.image_to_string(
                            image, 
                            lang=languages,
                            config=ocr_config
                        )
                        
                        if text and text.strip():
                            text_parts.append(text)
                            
                except Exception as e:
                    self.logger.warning(f"OCR failed for page {page_num}: {e}")
                    continue
            
            return '\n\n'.join(text_parts)
            
        finally:
            # Ensure document is closed to free memory
            if doc:
                try:
                    doc.close()
                except:
                    pass
    
    def save_extraction_results(self, results: Dict[str, List[PDFExtractionResult]], 
                              output_file: str = None) -> str:
        """Save extraction results to a file"""
        if output_file is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"pdf_extraction_results_{timestamp}.json"
        
        output_path = Path(self.config.pdf.output_dir) / output_file
        
        # Convert results to JSON-serializable format
        serializable_results = {}
        for source_name, source_results in results.items():
            serializable_results[source_name] = [
                {
                    'url': result.url,
                    'text': result.text,
                    'method': result.method,
                    'success': result.success,
                    'error': result.error,
                    'metadata': result.metadata
                }
                for result in source_results
            ]
        
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        return str(output_path)