"""
Security utilities for Local Radar
Provides input validation, XSS protection, and secure file operations
"""

import os
import re
import html
import bleach
from typing import Any, List, Dict, Optional, Union
from pathlib import Path, PurePath
import logging

logger = logging.getLogger(__name__)

# Allowed HTML tags and attributes for content sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'a', 'span', 'div'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'span': ['class'],
    'div': ['class'],
    '*': ['class']
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


def sanitize_html(content: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks
    
    Args:
        content: Raw HTML content
        
    Returns:
        Sanitized HTML content
    """
    if not content:
        return ""
    
    try:
        # Use bleach to sanitize HTML
        sanitized = bleach.clean(
            content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True
        )
        
        # Additional check for javascript: protocol that might slip through
        if 'javascript:' in sanitized.lower():
            sanitized = re.sub(r'javascript:\s*[^"\']*', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    except Exception as e:
        logger.error(f"Error sanitizing HTML: {e}")
        # Fallback to basic HTML escaping
        return html.escape(content)


def escape_html(text: str) -> str:
    """
    Escape HTML characters in text
    
    Args:
        text: Raw text content
        
    Returns:
        HTML-escaped text
    """
    if not text:
        return ""
    return html.escape(str(text))


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize filename to prevent path traversal
    
    Args:
        filename: Input filename
        
    Returns:
        Sanitized filename
        
    Raises:
        SecurityError: If filename is invalid or contains dangerous patterns
    """
    if not filename:
        raise SecurityError("Filename cannot be empty")
    
    # Convert to string and normalize
    filename = str(filename).strip()
    
    # Check for path traversal attempts
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        raise SecurityError(f"Invalid filename: {filename}")
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in filename for char in dangerous_chars):
        raise SecurityError(f"Filename contains dangerous characters: {filename}")
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Ensure filename isn't too long
    if len(filename) > 255:
        raise SecurityError(f"Filename too long: {len(filename)} characters (max: 255)")
    
    # Prevent reserved names on Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
        'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
        'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = os.path.splitext(filename)[0].upper()
    if name_without_ext in reserved_names:
        raise SecurityError(f"Reserved filename: {filename}")
    
    return filename


def safe_path_join(base_path: Union[str, Path], *components: str) -> Path:
    """
    Safely join path components, preventing path traversal attacks
    
    Args:
        base_path: Base directory path
        *components: Path components to join
        
    Returns:
        Safe resolved path
        
    Raises:
        SecurityError: If the resulting path would escape the base directory
    """
    base = Path(base_path).resolve()
    
    # Validate each component
    safe_components = []
    for component in components:
        if not component:
            continue
        component = validate_filename(component)
        safe_components.append(component)
    
    # Join components
    if not safe_components:
        return base
    
    result_path = base.joinpath(*safe_components).resolve()
    
    # Ensure the result is within the base directory
    try:
        result_path.relative_to(base)
    except ValueError:
        raise SecurityError(f"Path traversal attempt detected: {result_path}")
    
    return result_path


def validate_url(url: str) -> bool:
    """
    Validate URL format and protocol
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid and safe
    """
    if not url:
        return False
    
    # Basic URL format validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'javascript:', r'data:', r'vbscript:', r'file:', r'ftp:'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    
    return True


def validate_tag(tag: str) -> str:
    """
    Validate and sanitize a tag name
    
    Args:
        tag: Tag name to validate
        
    Returns:
        Sanitized tag name
        
    Raises:
        SecurityError: If tag is invalid
    """
    if not tag:
        raise SecurityError("Tag cannot be empty")
    
    tag = str(tag).strip()
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'", '`']
    if any(char in tag for char in dangerous_chars):
        raise SecurityError(f"Tag contains dangerous characters: {tag}")
    
    # Remove control characters
    tag = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', tag)
    
    # Limit length
    if len(tag) > 50:
        raise SecurityError(f"Tag too long: {len(tag)} characters (max: 50)")
    
    # Ensure tag is not empty after sanitization
    if not tag.strip():
        raise SecurityError("Tag contains only invalid characters")
    
    return tag


def validate_search_query(query: str) -> str:
    """
    Validate and sanitize search query
    
    Args:
        query: Search query to validate
        
    Returns:
        Sanitized search query
        
    Raises:
        SecurityError: If query is invalid
    """
    if not query:
        raise SecurityError("Search query cannot be empty")
    
    query = str(query).strip()
    
    # Limit length
    if len(query) > 500:
        raise SecurityError("Search query too long")
    
    # Remove dangerous characters but preserve search operators
    dangerous_chars = ['<', '>', '&', '"', "'", '`']
    if any(char in query for char in dangerous_chars):
        raise SecurityError(f"Search query contains dangerous characters: {query}")
    
    # Remove control characters
    query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)
    
    return query


def validate_config_value(key: str, value: Any, allowed_types: List[type] = None) -> Any:
    """
    Validate configuration values
    
    Args:
        key: Configuration key
        value: Value to validate
        allowed_types: List of allowed types for the value
        
    Returns:
        Validated value
        
    Raises:
        SecurityError: If value is invalid
    """
    if allowed_types and not any(isinstance(value, t) for t in allowed_types):
        raise SecurityError(f"Invalid type for config key '{key}': {type(value)}")
    
    # Specific validations for known config keys
    if key in ['max_entries_per_page', 'batch_size', 'max_concurrent']:
        if not isinstance(value, int) or value < 1 or value > 10000:
            raise SecurityError(f"Invalid value for '{key}': must be integer between 1 and 10000")
    
    elif key in ['similarity_threshold', 'confidence_score']:
        if not isinstance(value, (int, float)) or value < 0 or value > 1:
            raise SecurityError(f"Invalid value for '{key}': must be number between 0 and 1")
    
    elif key.endswith('_dir') or key.endswith('_file'):
        if not isinstance(value, str) or not value.strip():
            raise SecurityError(f"Invalid path for '{key}': cannot be empty")
        # Validate path doesn't contain dangerous patterns
        if '..' in value or value.startswith('/') and key != 'index_dir':
            raise SecurityError(f"Invalid path for '{key}': potential path traversal")
    
    return value


def secure_delete_file(file_path: Union[str, Path]) -> bool:
    """
    Securely delete a file
    
    Args:
        file_path: Path to file to delete
        
    Returns:
        True if file was deleted successfully
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception as e:
        logger.error(f"Error securely deleting file {file_path}: {e}")
    
    return False


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "WARNING"):
    """
    Log security-related events
    
    Args:
        event_type: Type of security event
        details: Event details
        severity: Log severity level
    """
    log_level = getattr(logging, severity.upper(), logging.WARNING)
    logger.log(log_level, f"SECURITY EVENT [{event_type}]: {details}")


# Input validation decorators
def validate_inputs(**validators):
    """
    Decorator to validate function inputs
    
    Args:
        **validators: Mapping of parameter names to validation functions
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    try:
                        bound_args.arguments[param_name] = validator(bound_args.arguments[param_name])
                    except SecurityError as e:
                        log_security_event("INPUT_VALIDATION_FAILED", {
                            "function": func.__name__,
                            "parameter": param_name,
                            "error": str(e)
                        })
                        raise
            
            return func(*bound_args.args, **bound_args.kwargs)
        return wrapper
    return decorator