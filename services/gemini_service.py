import asyncio
import logging
from typing import List, Optional
from datetime import datetime

import google.generativeai as genai
from fastapi import WebSocket

from config import settings
from schemas import MessageType
from models import ChatMessage

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker for external service resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if self.last_failure_time and (
                datetime.now().timestamp() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Service temporarily unavailable (circuit breaker OPEN)")
        
        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
    
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class ContextManager:
    """Manages conversation context intelligently"""
    
    def __init__(self, max_context_length: int = None):
        self.max_context_length = max_context_length or settings.max_context_length
    
    def build_context(self, messages: List[ChatMessage], current_message: str) -> str:
        """Build optimized context with smart truncation"""
        context_parts = []
        total_length = len(current_message) + 50  # Buffer
        
        # System prompt
        system_prompt = (
            "You are a helpful AI assistant. Provide clear, accurate, and engaging responses. "
            "Maintain conversation context and refer to previous messages when relevant."
        )
        context_parts.append(f"System: {system_prompt}")
        total_length += len(system_prompt) + 10
        
        # Add recent messages (prioritize recent ones)
        recent_messages = []
        for message in reversed(messages):
            message_text = f"{message.message_type.title()}: {message.content}"
            if total_length + len(message_text) + 10 > self.max_context_length:
                break
            recent_messages.append(message_text)
            total_length += len(message_text) + 10
        
        context_parts.extend(reversed(recent_messages))
        context_parts.append(f"User: {current_message}")
        
        return "\n".join(context_parts)

class StreamingGeminiService:
    """Production-ready Gemini service with streaming support"""
    
    def __init__(self):
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured")
            self.model = None
        else:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self.model = genai.GenerativeModel(settings.gemini_model)
                logger.info("Gemini service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                self.model = None
        
        self.context_manager = ContextManager()
        self.circuit_breaker = CircuitBreaker()
    
    async def generate_response(
        self, 
        message: str, 
        messages: List[ChatMessage]
    ) -> tuple[str, float]:
        """Generate response without streaming"""
        if not self.model:
            raise ValueError("Gemini API not available")
        
        context = self.context_manager.build_context(messages, message)
        start_time = datetime.now()
        
        try:
            response = await self.circuit_breaker.call(
                self._generate_content_async, context
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
            
            return response.text.strip(), response_time
            
        except Exception as e:
            logger.error(f"Error in response generation: {e}")
            raise
    
    async def stream_response(
        self, 
        message: str, 
        messages: List[ChatMessage], 
        websocket: WebSocket
    ) -> str:
        """Stream response with improved error handling"""
        if not self.model:
            error_msg = "AI service temporarily unavailable"
            await websocket.send_json({
                "type": "error",
                "data": {"message": error_msg, "error_code": "SERVICE_UNAVAILABLE"}
            })
            raise ValueError(error_msg)
        
        context = self.context_manager.build_context(messages, message)
        
        try:
            response = await self.circuit_breaker.call(
                self._generate_content_async, context
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
            
            # Stream response smoothly
            response_text = response.text.strip()
            words = response_text.split()
            current_response = ""
            
            for i, word in enumerate(words):
                current_response += word + " "
                
                # Send chunks for smooth streaming
                if i % 3 == 0 or i == len(words) - 1:
                    await websocket.send_json({
                        "type": "streaming_response",
                        "data": {
                            "content": current_response.strip(),
                            "is_complete": i == len(words) - 1,
                            "progress": (i + 1) / len(words)
                        }
                    })
                    await asyncio.sleep(0.02)
            
            return current_response.strip()
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "I'm having trouble generating a response. Please try again.",
                    "error_code": "GENERATION_ERROR"
                }
            })
            raise

    async def _generate_content_async(self, context: str):
        """Async wrapper for Gemini API with timeout"""
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(context)
            ),
            timeout=30.0  # 30 second timeout
        )