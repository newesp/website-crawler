from urllib.parse import urlparse, urlunparse, urldefrag
import os
import re

def normalize_url(url: str) -> str:
    """
    Normalizes a URL by:
    1. Stripping fragments (#...)
    2. Stripping query parameters (?m=1, etc.)
    3. Normalizing scheme to lowercase
    4. Normalizing netloc to lowercase
    5. Stripping trailing slash from path (unless path is just '/')
    """
    if not url:
        return ""
    
    defragged, _ = urldefrag(url)
    parsed = urlparse(defragged)
    
    scheme = parsed.scheme.lower()
    if scheme == 'http':
        scheme = 'https'
    netloc = parsed.netloc.lower()
    path = parsed.path
    
    if path.endswith('/') and len(path) > 1:
        path = path.rstrip('/')
    elif path == '/':
        path = ""
        
    normalized = urlunparse((scheme, netloc, path, "", "", ""))
    return normalized

def extract_slug_from_url(url: str) -> str:
    """
    Extracts the article slug from a URL.
    E.g. https://.../2019/04/day-574-using-shame.html -> day-574-using-shame
    """
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    path = parsed.path
    
    filename = os.path.basename(path)
    if filename.endswith(".html") or filename.endswith(".htm"):
        slug = os.path.splitext(filename)[0]
    elif filename:
        slug = filename
    else:
        # Fallback to sanitized path or 'index'
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', path.strip('/')) or "index"
        
    return slug

def is_same_host(root_url: str, target_url: str) -> bool:
    """
    Checks if target_url belongs to the same host boundary as root_url.
    """
    root_parsed = urlparse(root_url)
    target_parsed = urlparse(target_url)
    return root_parsed.netloc.lower() == target_parsed.netloc.lower()
