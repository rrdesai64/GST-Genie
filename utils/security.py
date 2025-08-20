import re
from typing import Optional
from fastapi import HTTPException, status

def validate_password_strength(password: str) -> Optional[str]:
    """
    Validate password strength and return error message if weak
    
    Args:
        password: The password to validate
        
    Returns:
        Optional[str]: Error message if validation fails, None if valid
        
    Raises:
        HTTPException: If password doesn't meet strength requirements
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    
    return None

def sanitize_input(input_string: str, max_length: int = 4000) -> str:
    """
    Basic input sanitization to prevent XSS and other attacks
    
    Args:
        input_string: The input string to sanitize
        max_length: Maximum length of the output string
        
    Returns:
        str: Sanitized input string
    """
    if not input_string:
        return input_string
    
    # Trim and limit length
    sanitized = input_string.strip()[:max_length]
    
    # Basic HTML escaping (for display purposes, not for storage)
    sanitized = (
        sanitized.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
    
    return sanitized

def validate_email_format(email: str) -> bool:
    """
    Validate email format using regex
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email format is valid, False otherwise
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_regex, email))

def validate_username_format(username: str) -> bool:
    """
    Validate username format (alphanumeric + underscores, 3-50 chars)
    
    Args:
        username: Username to validate
        
    Returns:
        bool: True if username format is valid, False otherwise
    """
    username_regex = r'^[a-zA-Z0-9_]{3,50}$'
    return bool(re.match(username_regex, username))

# Additional security utilities
def is_safe_string(input_string: str, max_length: int = 1000) -> bool:
    """
    Check if a string contains only safe characters
    
    Args:
        input_string: String to check
        max_length: Maximum allowed length
        
    Returns:
        bool: True if string is safe, False otherwise
    """
    if not input_string or len(input_string) > max_length:
        return False
    
    # Allow alphanumeric, spaces, and basic punctuation
    safe_pattern = r'^[a-zA-Z0-9\s\.,!?@#$%^&*()_+\-=\[\]{}|;:\'"<>/\\`~]+$'
    return bool(re.match(safe_pattern, input_string))

def validate_input_length(input_string: str, field_name: str, 
                         min_length: int = 1, max_length: int = 1000) -> str:
    """
    Validate input length and raise appropriate HTTPException if invalid
    
    Args:
        input_string: Input to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length
        max_length: Maximum allowed length
        
    Returns:
        str: Validated input string
        
    Raises:
        HTTPException: If validation fails
    """
    if not input_string or len(input_string.strip()) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at least {min_length} characters long"
        )
    
    if len(input_string) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be less than {max_length} characters"
        )
    
    return input_string.strip()