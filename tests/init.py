"""
Test suite for the Advanced Gemini Chat Application.

This package contains all the tests for the chat application, including:
- Authentication tests
- Chat endpoint tests
- Session management tests
- Integration tests
"""

__version__ = "1.0.0"
__author__ = "Chat Application Team"

# Import test modules to make them easily accessible
from . import test_auth
from . import test_chat
from . import test_sessions

__all__ = [
    'test_auth',
    'test_chat', 
    'test_sessions'
]