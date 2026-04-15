"""
LLM Integration Module: Interfaces with Claude (Anthropic) and GPT-4 (OpenAI).

This module provides abstractions for calling LLMs with the agent-specific prompts.
Supports both Anthropic's Claude and OpenAI's GPT-4 with configurable fallback.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import os
import json
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    GPT4 = "gpt4"


class LLMResponse:
    """Structured response from LLM call."""
    
    def __init__(self, content: str, model: str, usage: Dict = None):
        """Initialize response."""
        self.content = content
        self.model = model
        self.usage = usage or {}
    
    def parse_json(self) -> Dict:
        """Try to parse response as JSON."""
        try:
            return json.loads(self.content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in self.content:
                start = self.content.find("```json") + 7
                end = self.content.find("```", start)
                if end > start:
                    return json.loads(self.content[start:end].strip())
            raise


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Call the LLM.
        
        Args:
            system_prompt: System message defining agent behavior
            user_prompt: User message with analysis request
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum response tokens
            
        Returns:
            LLMResponse with model output
        """
        pass


class ClaudeClient(LLMClient):
    """Anthropic Claude API client."""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229"):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name (defaults to Claude 3 Sonnet)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not provided and not in environment"
            )
        
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
    
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Call Claude API."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        )


class GPT4Client(LLMClient):
    """OpenAI GPT-4 API client."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo"):
        """
        Initialize GPT-4 client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to GPT-4 Turbo)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY not provided and not in environment"
            )
        
        try:
            import openai
            openai.api_key = self.api_key
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
    
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Call OpenAI GPT-4 API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
        )


class MockLLMClient(LLMClient):
    """Mock LLM client for testing (no API calls)."""
    
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Return mock response for testing."""
        # Return valid JSON structure expected by agents
        mock_response = {
            "findings": [
                {
                    "finding_type": "Code Quality",
                    "severity": "warning",
                    "file_path": "src/example.py",
                    "line_number": 42,
                    "description": "[Mock] Example finding for testing",
                    "suggestion": "[Mock] Consider refactoring this code"
                }
            ]
        }
        
        return LLMResponse(
            content=json.dumps(mock_response),
            model="mock",
            usage={"mock": True}
        )


def get_llm_client(provider: str = None) -> LLMClient:
    """
    Factory function to get LLM client.
    
    Args:
        provider: "claude", "gpt4", "mock", or None for auto-detection
        
    Returns:
        Configured LLM client
        
    Raises:
        ValueError: If provider not found and no API keys configured
    """
    if provider is None:
        # Auto-detect based on available API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = "claude"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "gpt4"
        else:
            # Default to mock for development
            provider = "mock"
    
    provider = provider.lower()
    
    if provider == "claude":
        return ClaudeClient()
    elif provider == "gpt4":
        return GPT4Client()
    elif provider == "mock":
        return MockLLMClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
