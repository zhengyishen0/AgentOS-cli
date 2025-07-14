"""LLM Provider for AgentOS - Clean abstraction for LLM interactions with validation."""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ValidationError
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMProvider:
    """Reusable LLM provider with schema validation.
    
    Provides clean abstraction for:
    - JSON mode completions
    - Input/output schema validation
    - Error handling
    - Multiple response formats
    """
    
    def __init__(self, model: str = "gpt-4.1-nano"):
        self.client = OpenAI()
        self.default_model = model
    
    def complete(
        self,
        message: str,
        system_message: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = True
    ) -> Union[Dict[str, Any], T, str]:
        """Execute LLM completion with configurable output format.
        
        Args:
            message: User message content
            system_message: Optional system message to prepend
            schema: Optional Pydantic model for output validation
            model: Model to use (defaults to self.default_model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            json_mode: If True, use JSON response format; if False, use text
            
        Returns:
            Dict/validated model for JSON mode, str for text mode
            
        Raises:
            ValidationError: If input or output validation fails
        """

        # Build messages list internally
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": message})

        request_params = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature
        }
        
        if json_mode:
            request_params["response_format"] = {"type": "json_object"}

        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        try:
            response = self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            # Return text directly if not in JSON mode
            if not json_mode:
                return content
            
            # Parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {content}")
                raise
            
            # Validate output if schema provided
            if schema:
                try:
                    return schema(**result)
                except ValidationError as e:
                    logger.error(f"Output validation failed for {schema.__name__}: {e}")
                    logger.error(f"Response data: {result}")
                    raise
            
            return result
            
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise
    
    def validate_schema(self, data: Dict[str, Any], schema: Type[T]) -> T:
        """Validate output data against schema.
        
        Args:
            data: Output data to validate
            schema: Pydantic schema to validate against
            
        Returns:
            Validated model instance
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            return schema(**data)
        except ValidationError as e:
            logger.error(f"Output validation failed for {schema.__name__}: {e}")
            logger.error(f"Output data: {data}")
            raise


# Global instance for convenience
llm = LLMProvider()