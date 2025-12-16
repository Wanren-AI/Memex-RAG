"""
Utility Functions
Helper functions for the RAG system
通用工具
"""
import hashlib
import time
from typing import Callable, Any, TypeVar, Optional
from functools import wraps
from pathlib import Path


T = TypeVar('T')


def generate_hash(text: str, algorithm: str = 'md5') -> str:
    """
    Generate hash from text
    
    Args:
        text: Input text
        algorithm: Hash algorithm (md5, sha256, etc.)
        
    Returns:
        Hex digest of hash
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(text.encode('utf-8'))
    return hash_func.hexdigest()


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function on failure
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier for delay
        exceptions: Exceptions to catch
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    print(f"Attempt {attempt + 1} failed: {e}. "
                          f"Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def measure_time(func: Callable[..., T]) -> Callable[..., tuple[T, float]]:
    """
    Decorator to measure function execution time
    
    Args:
        func: Function to measure
        
    Returns:
        Tuple of (result, execution_time)
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> tuple[T, float]:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed
    
    return wrapper


class Timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, name: str = "Operation"):
        """
        Initialize timer
        
        Args:
            name: Operation name
        """
        self.name = name
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        """Start timer"""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and print result"""
        self.elapsed = time.perf_counter() - self.start_time
        print(f"{self.name} took {self.elapsed:.3f}s")
        return False


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, create if necessary
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division with default value
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to append if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def validate_file_extension(file_path: str, allowed_extensions: set) -> bool:
    """
    Validate file extension
    
    Args:
        file_path: File path
        allowed_extensions: Set of allowed extensions (with dot)
        
    Returns:
        True if valid
    """
    ext = Path(file_path).suffix.lower()
    return ext in allowed_extensions


class Cache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, ttl: float = 3600):
        """
        Initialize cache
        
        Args:
            ttl: Time to live in seconds
        """
        self.ttl = ttl
        self._cache: dict = {}
        self._timestamps: dict = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key not in self._cache:
            return None
        
        # Check if expired
        if time.time() - self._timestamps[key] > self.ttl:
            self.delete(key)
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """
        Delete value from cache
        
        Args:
            key: Cache key
        """
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear entire cache"""
        self._cache.clear()
        self._timestamps.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self._cache)


# Example usage
if __name__ == "__main__":
    # Hash generation
    text_hash = generate_hash("example text")
    print(f"Hash: {text_hash}")
    
    # Timer
    with Timer("Sleep operation"):
        time.sleep(1)
    
    # Retry decorator
    @retry_on_failure(max_attempts=3, delay=0.5)
    def flaky_function():
        import random
        if random.random() < 0.7:
            raise ValueError("Random failure")
        return "Success"
    
    # Cache
    cache = Cache(ttl=5)
    cache.set("key1", "value1")
    print(f"Cached: {cache.get('key1')}")
    
    time.sleep(6)
    print(f"After TTL: {cache.get('key1')}")  # Should be None
