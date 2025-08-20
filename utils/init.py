"""
Utility functions for the chat application

This package provides validation, sanitization, and security utilities
for the chat application.
"""

from .security import (
    validate_password_strength,
    sanitize_input,
    validate_email_format,
    validate_username_format
)

from .validators import (
    validate_json_string,
    validate_message_content,
    validate_session_title
)

__version__ = "1.0.0"
__author__ = "Chat Application Team"

__all__ = [
    'validate_password_strength',
    'sanitize_input',
    'validate_email_format',
    'validate_username_format',
    'validate_json_string',
    'validate_message_content',
    'validate_session_title'
]

# Package metadata
__package_metadata__ = {
    "version": __version__,
    "author": __author__,
    "description": "Utility functions for validation and security",
    "modules": {
        "security": "Security and input validation utilities",
        "validators": "Data validation and sanitization functions"
    }
}

def get_utils_info() -> dict:
    """
    Get information about available utility functions.
    
    Returns:
        dict: Package metadata and available functions
    """
    return __package_metadata__