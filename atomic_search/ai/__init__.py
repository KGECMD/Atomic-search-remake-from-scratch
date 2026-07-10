"""
AI service for Atomic Search.

Provides AI-powered features:
- Search result summaries
- Webpage summarization
- Chat assistant
- Multiple provider support (OpenAI, Anthropic, Gemini, Ollama)
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from atomic_search.config import AIProvider, config


@dataclass
class AIMessage:
    """AI message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class AIResponse:
    """Response from AI provider."""
    content: str
    provider: AIProvider
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None


class AIProviderBase(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key or config.AI_API_KEY
        self.endpoint = endpoint or config.AI_API_ENDPOINT
        self.model = config.AI_MODEL
        self.max_tokens = config.AI_MAX_TOKENS
        self.temperature = config.AI_TEMPERATURE

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a completion."""
        pass

    @abstractmethod
    async def stream_complete(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        pass

    @abstractmethod
    async def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Chat with the AI."""
        pass

    @abstractmethod
    async def stream_chat(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        pass


class OpenAIProvider(AIProviderBase):
    """OpenAI GPT provider."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        super().__init__(api_key, endpoint)
        self._client = None

    async def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    async def complete(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a completion."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            )

            return AIResponse(
                content=response.choices[0].message.content,
                provider=AIProvider.OPENAI,
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as e:
            return AIResponse(
                content="",
                provider=AIProvider.OPENAI,
                model=model,
                error=str(e),
            )

    async def stream_complete(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error: {str(e)}"

    async def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Chat with the AI."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            chat_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]

            response = await client.chat.completions.create(
                model=model,
                messages=chat_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            )

            return AIResponse(
                content=response.choices[0].message.content,
                provider=AIProvider.OPENAI,
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as e:
            return AIResponse(
                content="",
                provider=AIProvider.OPENAI,
                model=model,
                error=str(e),
            )

    async def stream_chat(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            chat_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]

            response = await client.chat.completions.create(
                model=model,
                messages=chat_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error: {str(e)}"


class AnthropicProvider(AIProviderBase):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        super().__init__(api_key, endpoint)
        self._client = None

    async def _get_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    async def complete(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a completion."""
        client = await self._get_client()
        model = kwargs.get("model", "claude-3-sonnet-20240229")
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            response = await client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return AIResponse(
                content=response.content[0].text,
                provider=AIProvider.ANTHROPIC,
                model=model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )
        except Exception as e:
            return AIResponse(
                content="",
                provider=AIProvider.ANTHROPIC,
                model=model,
                error=str(e),
            )

    async def stream_complete(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        client = await self._get_client()
        model = kwargs.get("model", "claude-3-sonnet-20240229")
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            async with client.messages.stream(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            yield f"Error: {str(e)}"

    async def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Chat with the AI."""
        return await self.complete(
            "\n".join([f"{m.role}: {m.content}" for m in messages]),
            **kwargs
        )

    async def stream_chat(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        await self.stream_complete(
            "\n".join([f"{m.role}: {m.content}" for m in messages]),
            **kwargs
        )


class OllamaProvider(AIProviderBase):
    """Ollama local LLM provider."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        super().__init__(api_key, endpoint)
        self.base_url = endpoint or "http://localhost:11434"
        self.model = kwargs.get("model", "llama2")

    async def complete(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a completion."""
        import httpx

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False,
                    }
                )
                response.raise_for_status()
                data = response.json()

                return AIResponse(
                    content=data.get("response", ""),
                    provider=AIProvider.OLLAMA,
                    model=model,
                )
        except Exception as e:
            return AIResponse(
                content="",
                provider=AIProvider.OLLAMA,
                model=model,
                error=str(e),
            )

    async def stream_complete(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        import httpx

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": True,
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if data.get("response"):
                                yield data["response"]

        except Exception as e:
            yield f"Error: {str(e)}"

    async def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Chat with the AI."""
        import httpx

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": m.role, "content": m.content}
                            for m in messages
                        ],
                        "temperature": temperature,
                        "stream": False,
                    }
                )
                response.raise_for_status()
                data = response.json()

                return AIResponse(
                    content=data.get("message", {}).get("content", ""),
                    provider=AIProvider.OLLAMA,
                    model=model,
                )
        except Exception as e:
            return AIResponse(
                content="",
                provider=AIProvider.OLLAMA,
                model=model,
                error=str(e),
            )

    async def stream_chat(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        import httpx

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": m.role, "content": m.content}
                            for m in messages
                        ],
                        "temperature": temperature,
                        "stream": True,
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if data.get("message", {}).get("content"):
                                yield data["message"]["content"]

        except Exception as e:
            yield f"Error: {str(e)}"


class AIService:
    """Main AI service class."""

    def __init__(self):
        self._provider: Optional[AIProviderBase] = None
        self._initialized = False
        self._conversation_history: Dict[str, List[AIMessage]] = {}

    def _get_provider(self) -> AIProviderBase:
        """Get the configured AI provider."""
        provider_type = config.AI_PROVIDER

        if provider_type == AIProvider.OPENAI:
            return OpenAIProvider()
        elif provider_type == AIProvider.ANTHROPIC:
            return AnthropicProvider()
        elif provider_type == AIProvider.OLLAMA:
            return OllamaProvider()
        else:
            raise ValueError(f"Unsupported AI provider: {provider_type}")

    async def initialize(self) -> None:
        """Initialize the AI service."""
        if self._initialized:
            return

        if config.AI_PROVIDER == AIProvider.NONE:
            self._initialized = True
            return

        self._provider = self._get_provider()
        self._initialized = True

    async def summarize_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> str:
        """Generate a summary of search results."""
        await self.initialize()

        if not config.AI_SUMMARIES_ENABLED or config.AI_PROVIDER == AIProvider.NONE:
            return ""

        results_text = "\n\n".join([
            f"- {r.get('title', '')}: {r.get('snippet', '')}"
            for r in results[:10]
        ])

        prompt = f"""Based on the following search results for "{query}", provide a brief summary of the key findings and themes:

{results_text}

Provide a 2-3 sentence summary that helps understand what these results collectively tell us."""

        response = await self._provider.complete(prompt)
        return response.content

    async def summarize_webpage(self, content: str, url: str) -> str:
        """Summarize a webpage's content."""
        await self.initialize()

        if not config.AI_PROVIDER or config.AI_PROVIDER == AIProvider.NONE:
            return ""

        prompt = f"""Summarize the following webpage content from {url}. Focus on the main points and key information:

{content[:10000]}

Provide a concise summary in 3-5 sentences."""

        response = await self._provider.complete(prompt)
        return response.content

    async def chat(
        self,
        message: str,
        conversation_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        """Chat with the AI assistant."""
        await self.initialize()

        if config.AI_PROVIDER == AIProvider.NONE:
            return AIResponse(
                content="AI features are not configured. Please set up an AI provider.",
                provider=AIProvider.NONE,
                model="none",
            )

        # Get or create conversation history
        if conversation_id not in self._conversation_history:
            self._conversation_history[conversation_id] = []

        # Add context messages if provided
        if context:
            system_prompt = self._build_context_prompt(context)
            self._conversation_history[conversation_id].insert(
                0,
                AIMessage(role="system", content=system_prompt)
            )

        # Add user message
        import time
        self._conversation_history[conversation_id].append(
            AIMessage(role="user", content=message, timestamp=time.time())
        )

        # Get response
        response = await self._provider.chat(self._conversation_history[conversation_id])

        # Add assistant response to history
        if not response.error:
            self._conversation_history[conversation_id].append(
                AIMessage(role="assistant", content=response.content, timestamp=time.time())
            )

        return response

    async def stream_chat(
        self,
        message: str,
        conversation_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat with the AI assistant."""
        await self.initialize()

        if config.AI_PROVIDER == AIProvider.NONE:
            yield "AI features are not configured."
            return

        # Get or create conversation history
        if conversation_id not in self._conversation_history:
            self._conversation_history[conversation_id] = []

        # Add context messages if provided
        if context:
            system_prompt = self._build_context_prompt(context)
            self._conversation_history[conversation_id].insert(
                0,
                AIMessage(role="system", content=system_prompt)
            )

        # Add user message
        import time
        self._conversation_history[conversation_id].append(
            AIMessage(role="user", content=message, timestamp=time.time())
        )

        # Stream response
        full_response = ""
        async for chunk in self._provider.stream_chat(self._conversation_history[conversation_id]):
            full_response += chunk
            yield chunk

        # Add to history
        if full_response and not full_response.startswith("Error:"):
            self._conversation_history[conversation_id].append(
                AIMessage(role="assistant", content=full_response, timestamp=time.time())
            )

    def _build_context_prompt(self, context: Dict[str, Any]) -> str:
        """Build a context prompt from search context."""
        parts = ["You are a helpful assistant integrated into Atomic Search, a privacy-focused search engine."]

        if context.get("query"):
            parts.append(f"Current search query: {context['query']}")

        if context.get("current_url"):
            parts.append(f"User is currently viewing: {context['current_url']}")

        if context.get("search_results"):
            parts.append("\nCurrent search results:")
            for i, r in enumerate(context["search_results"][:5], 1):
                parts.append(f"{i}. {r.get('title', '')} - {r.get('snippet', '')}")

        return "\n".join(parts)

    def get_conversation_history(self, conversation_id: str) -> List[AIMessage]:
        """Get conversation history for a session."""
        return self._conversation_history.get(conversation_id, [])

    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if conversation_id in self._conversation_history:
            del self._conversation_history[conversation_id]

    def is_available(self) -> bool:
        """Check if AI is available."""
        return config.AI_PROVIDER != AIProvider.NONE


# Global AI service instance
ai_service = AIService()
