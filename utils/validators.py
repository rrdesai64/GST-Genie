from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status
import json
import re

def validate_json_string(json_string: str, max_length: int = 5000) -> Optional[Dict[str, Any]]:
    """
    Validate and parse JSON string with size limits
    
    Args:
        json_string: JSON string to validate
        max_length: Maximum allowed length of JSON string
        
    Returns:
        Optional[Dict[str, Any]]: Parsed JSON data or None if empty
        
    Raises:
        HTTPException: If JSON is invalid or too large
    """
    if not json_string:
        return None
    
    if len(json_string) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JSON data too large (max {max_length} characters)"
        )
    
    try:
        parsed_data = json.loads(json_string)
        if not isinstance(parsed_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON data must be an object"
            )
        return parsed_data
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )

def validate_message_content(content: str, max_length: int = 4000) -> str:
    """
    Validate message content with length limits and basic checks
    
    Args:
        content: Message content to validate
        max_length: Maximum allowed message length
        
    Returns:
        str: Validated and trimmed message content
        
    Raises:
        HTTPException: If validation fails
    """
    if not content or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    
    content = content.strip()
    
    if len(content) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message too long (max {max_length} characters)"
        )
    
    # Check for excessive whitespace (potential spam)
    if len(content.split()) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message contains too many words"
        )
    
    # Check for suspicious patterns (basic spam detection)
    if contains_suspicious_patterns(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message contains suspicious content"
        )
    
    return content

def validate_session_title(title: Optional[str], max_length: int = 200) -> Optional[str]:
    """
    Validate session title
    
    Args:
        title: Session title to validate
        max_length: Maximum allowed title length
        
    Returns:
        Optional[str]: Validated title or None if empty
        
    Raises:
        HTTPException: If validation fails
    """
    if not title:
        return None
    
    title = title.strip()
    
    if len(title) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session title too long (max {max_length} characters)"
        )
    
    if not is_safe_title(title):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session title contains invalid characters"
        )
    
    return title

def contains_suspicious_patterns(text: str) -> bool:
    """
    Check for suspicious patterns in text (basic spam detection)
    
    Args:
        text: Text to check
        
    Returns:
        bool: True if suspicious patterns are found
    """
    suspicious_patterns = [
        r'(http|https)://',  # URLs
        r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',  # Email addresses
        r'\b\d{4}[-.]?\d{4}[-.]?\d{4}[-.]?\d{4}\b',  # Credit card numbers
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False

def is_safe_title(title: str) -> bool:
    """
    Check if session title contains only safe characters
    
    Args:
        title: Title to check
        
    Returns:
        bool: True if title is safe
    """
    # Allow alphanumeric, spaces, hyphens, and basic punctuation
    safe_pattern = r'^[a-zA-Z0-9\s\-\.,!?()@#$%^&*_+=\[\]{}|;:\'"<>/\\`~]+$'
    return bool(re.match(safe_pattern, title))

def validate_list_length(items: List[Any], field_name: str, 
                        max_items: int = 100) -> List[Any]:
    """
    Validate list length
    
    Args:
        items: List to validate
        field_name: Name of the field for error messages
        max_items: Maximum number of items allowed
        
    Returns:
        List[Any]: Validated list
        
    Raises:
        HTTPException: If list is too long
    """
    if len(items) > max_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot contain more than {max_items} items"
        )
    
    return items