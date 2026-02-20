"""String utility functions."""

from typing import Any, Optional


def as_str_or_none(value: Any) -> Optional[str]:
    """
    Convert a value to string safely, returning None if the value is None or cannot be converted.
    
    Args:
        value: Any value to convert to string
        
    Returns:
        String representation of the value, or None
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and len(value) > 0:
        # Handle cases where HTML attributes might be lists
        return str(value[0])
    try:
        return str(value)
    except Exception:
        return None
