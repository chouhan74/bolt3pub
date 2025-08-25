import re
import hashlib
import secrets
import string
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s-.]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-.')

def calculate_time_remaining(start_time: datetime, duration_minutes: int) -> int:
    """Calculate remaining time in seconds"""
    if not start_time:
        return duration_minutes * 60
    
    elapsed = datetime.utcnow() - start_time
    elapsed_seconds = elapsed.total_seconds()
    total_seconds = duration_minutes * 60
    
    remaining = max(0, total_seconds - elapsed_seconds)
    return int(remaining)

def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def calculate_score_percentage(score: float, max_score: float) -> float:
    """Calculate percentage score"""
    if max_score <= 0:
        return 0.0
    return (score / max_score) * 100

def parse_tags(tags_string: str) -> List[str]:
    """Parse comma-separated tags string"""
    if not tags_string:
        return []
    
    tags = [tag.strip() for tag in tags_string.split(',')]
    return [tag for tag in tags if tag]  # Remove empty tags

def format_tags(tags: List[str]) -> str:
    """Format tags list as comma-separated string"""
    return ', '.join(tags)

def generate_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def is_safe_redirect_url(url: str, allowed_hosts: List[str]) -> bool:
    """Check if redirect URL is safe"""
    if not url:
        return False
    
    # Only allow relative URLs or URLs from allowed hosts
    if url.startswith('/'):
        return True
    
    for host in allowed_hosts:
        if url.startswith(f'http://{host}') or url.startswith(f'https://{host}'):
            return True
    
    return False

def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def parse_json_safely(json_string: str, default: Any = None) -> Any:
    """Safely parse JSON string"""
    try:
        return json.loads(json_string) if json_string else default
    except (json.JSONDecodeError, TypeError):
        return default

def format_json_safely(data: Any) -> str:
    """Safely format data as JSON string"""
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return '{}'

def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request"""
    # Check for forwarded headers first (for reverse proxies)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    if hasattr(request, 'client') and request.client:
        return request.client.host
    
    return None

def validate_programming_language(language: str) -> bool:
    """Validate if programming language is supported"""
    supported_languages = {'python', 'cpp', 'c', 'java', 'javascript', 'js'}
    return language.lower() in supported_languages

def normalize_language_name(language: str) -> str:
    """Normalize language name to standard format"""
    language = language.lower().strip()
    
    mapping = {
        'js': 'javascript',
        'py': 'python',
        'c++': 'cpp'
    }
    
    return mapping.get(language, language)

def calculate_complexity_score(code: str) -> int:
    """Calculate a simple complexity score for code"""
    lines = code.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # Basic metrics
    line_count = len(non_empty_lines)
    
    # Count control structures
    control_keywords = ['if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally']
    control_count = sum(1 for line in non_empty_lines 
                       for keyword in control_keywords 
                       if keyword in line.lower())
    
    # Simple complexity score
    complexity = line_count + (control_count * 2)
    return complexity

def extract_imports(code: str, language: str) -> List[str]:
    """Extract import statements from code"""
    imports = []
    lines = code.split('\n')
    
    if language == 'python':
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
    elif language in ['cpp', 'c']:
        for line in lines:
            line = line.strip()
            if line.startswith('#include'):
                imports.append(line)
    elif language == 'java':
        for line in lines:
            line = line.strip()
            if line.startswith('import '):
                imports.append(line)
    
    return imports

def detect_potential_cheating_patterns(code: str) -> List[str]:
    """Detect potential cheating patterns in code"""
    patterns = []
    
    # Check for suspicious comments
    suspicious_comments = [
        'stackoverflow', 'github', 'copied', 'copy', 'paste',
        'solution from', 'found online', 'internet'
    ]
    
    for comment_indicator in ['#', '//', '/*']:
        if comment_indicator in code:
            for line in code.split('\n'):
                if comment_indicator in line:
                    comment = line.split(comment_indicator, 1)[1].lower()
                    for suspicious in suspicious_comments:
                        if suspicious in comment:
                            patterns.append(f"Suspicious comment: {line.strip()}")
    
    # Check for unusual variable names
    unusual_patterns = [
        r'var\d+',  # var1, var2, etc.
        r'temp\d+',  # temp1, temp2, etc.
        r'[a-z]{1,2}\d+',  # a1, b2, etc.
    ]
    
    for pattern in unusual_patterns:
        if re.search(pattern, code):
            patterns.append(f"Unusual variable naming pattern: {pattern}")
    
    return patterns

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if timestamp > window_start
            ]
        else:
            self.requests[key] = []
        
        # Check if under limit
        if len(self.requests[key]) < max_requests:
            self.requests[key].append(now)
            return True
        
        return False
    
    def get_remaining_requests(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in current window"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        if key not in self.requests:
            return max_requests
        
        # Count requests in current window
        current_requests = len([
            timestamp for timestamp in self.requests[key]
            if timestamp > window_start
        ])
        
        return max(0, max_requests - current_requests)

# Global rate limiter instance
rate_limiter = RateLimiter()