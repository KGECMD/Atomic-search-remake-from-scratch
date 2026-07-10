"""
Local AI Integration for Atomic Search.

Provides local LLM integration via Ollama API with automatic fallback
to lightweight text processing when Ollama is unavailable.
"""

import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import requests

from atomic_search.config import config


@dataclass
class LocalAIResult:
    """Result from local AI processing."""
    success: bool
    content: str
    model: str
    error: Optional[str] = None
    processing_time: float = 0.0


class LocalAIModel:
    """
    Local AI Model integration for Atomic Search.
    
    Features:
    - Ollama API integration
    - Multiple model support
    - Text summarization
    - Question answering
    - Keyword extraction
    - Automatic fallback
    """
    
    def __init__(self):
        self.ollama_url = getattr(config, 'OLLAMA_URL', 'http://localhost:11434')
        self.default_model = getattr(config, 'OLLAMA_MODEL', 'llama2')
        self.fallback_enabled = getattr(config, 'OLLAMA_FALLBACK_ENABLED', True)
        self.timeout = getattr(config, 'OLLAMA_TIMEOUT', 30)
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
        except:
            pass
        return []
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> LocalAIResult:
        """
        Generate text using local AI model.
        
        Args:
            prompt: The user prompt
            model: Model name (defaults to configured model)
            system: System prompt for context
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            LocalAIResult with generated content
        """
        model = model or self.default_model
        
        # Try Ollama first
        if self.is_available():
            try:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                if system:
                    payload["system"] = system
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return LocalAIResult(
                        success=True,
                        content=data.get('response', '').strip(),
                        model=model
                    )
            except Exception as e:
                pass
        
        # Fallback to local processing
        if self.fallback_enabled:
            return self._fallback_generate(prompt, system)
        
        return LocalAIResult(
            success=False,
            content="",
            model=model,
            error="Local AI unavailable and fallback disabled"
        )
    
    def _fallback_generate(self, prompt: str, system: Optional[str] = None) -> LocalAIResult:
        """
        Fallback text processing when Ollama is unavailable.
        
        Provides basic text analysis without requiring a model.
        """
        prompt_lower = prompt.lower()
        
        # Keyword extraction
        keywords = self._extract_keywords(prompt)
        
        # Determine intent
        if any(word in prompt_lower for word in ['summarize', 'summary', 'tl;dr', 'tldr']):
            return self._create_summary_response(prompt, keywords)
        elif any(word in prompt_lower for word in ['what is', 'who is', 'define', 'explain']):
            return self._create_explanation_response(prompt, keywords)
        elif any(word in prompt_lower for word in ['compare', 'difference', 'vs']):
            return self._create_comparison_response(prompt, keywords)
        elif any(word in prompt_lower for word in ['how to', 'steps', 'guide']):
            return self._create_guide_response(prompt, keywords)
        elif any(word in prompt_lower for word in ['list', 'top', 'best']):
            return self._create_list_response(prompt, keywords)
        else:
            return self._create_general_response(prompt, keywords)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'can', 'this',
                     'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
                     'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why',
                     'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
                     'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
                     'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but',
                     'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at',
                     'by', 'for', 'with', 'about', 'against', 'between', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below', 'to',
                     'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under'}
        
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        
        # Return most common
        from collections import Counter
        counter = Counter(keywords)
        return [word for word, count in counter.most_common(10)]
    
    def _create_summary_response(self, prompt: str, keywords: List[str]) -> LocalAIResult:
        """Create a summary-style response."""
        topic = ' '.join(keywords[:3]) if keywords else 'the topic'
        return LocalAIResult(
            success=True,
            content=f"""Based on your query about {topic}, here are key points:

1. **Topic**: {topic.title()}
2. **Related Terms**: {', '.join(keywords[:5])}

To learn more, search for specific aspects of {topic} or browse the search results for detailed information.

*Note: This is an automated summary. For detailed information, explore the search results.*""",
            model="fallback"
        )
    
    def _create_explanation_response(self, prompt: str, keywords: List[str]) -> LocalAIResult:
        """Create an explanation-style response."""
        topic = ' '.join(keywords[:2]) if keywords else 'this topic'
        return LocalAIResult(
            success=True,
            content=f"""**Quick Explanation of {topic.title()}**

{topic.title()} is a concept that relates to: {', '.join(keywords[:4])}

**Key Points:**
- This is an important topic in its field
- Search results below provide comprehensive information
- Consider exploring multiple sources for detailed understanding

*This is an automated overview. Check search results for full details.*""",
            model="fallback"
        )
    
    def _create_comparison_response(self, prompt: str, keywords: List[str]) -> LocalAIResult:
        """Create a comparison-style response."""
        return LocalAIResult(
            success=True,
            content=f"""**Comparison Analysis**

Key factors to consider: {', '.join(keywords[:5])}

**Search Approach:**
1. Search for each option individually
2. Look for comparison articles
3. Check user reviews and expert opinions

The search results below should provide comprehensive comparisons to help you decide.""",
            model="fallback"
        )
    
    def _create_guide_response(self, prompt: str, keywords: List[str]) -> LocalAIResult:
        """Create a guide-style response."""
        topic = ' '.join(keywords[:2]) if keywords else 'this topic'
        return LocalAIResult(
            success=True,
            content=f"""**How-To Guide: {topic.title()}**

**Steps to Follow:**
1. Research the basics using search results
2. Find step-by-step tutorials
3. Practice with simple examples
4. Progress to advanced techniques

**Resources:**
- Search for beginner tutorials
- Look for video guides
- Check official documentation

Explore the search results below for detailed instructions.""",
            model="fallback"
        )
    
    def _create_list_response(self, prompt: str, keywords: List[str]) -> LocalAIResult:
        """Create a list-style response."""
        topic = ' '.join(keywords[:2]) if keywords else 'this topic'
        return LocalAIResult(
            success=True,
            content=f"""**Top Results for {topic.title()}**

Based on popularity and relevance, here are common criteria to consider:

1. Quality and reliability
2. User ratings and reviews
3. Features and capabilities
4. Cost and value
5. Community support

**Recommendation:**
Use the search results below to find specific recommendations that match your needs.""",
            model="fallback"
        )
    
    def _create_general_response(self, prompt: str, keywords: List[str]) -> LocalAIResult:
        """Create a general response."""
        topic = ' '.join(keywords[:3]) if keywords else 'your search'
        return LocalAIResult(
            success=True,
            content=f"""**Search Analysis for: {topic.title()}**

Your search relates to: {', '.join(keywords[:5])}

**Suggestions:**
- Browse search results for comprehensive information
- Try specific searches for detailed topics
- Use advanced search operators for precise results

Explore the results below for more information.""",
            model="fallback"
        )
    
    def summarize(self, text: str, max_length: int = 200) -> LocalAIResult:
        """
        Summarize text content.
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
        
        Returns:
            LocalAIResult with summary
        """
        prompt = f"Summarize the following text in {max_length} words or less:\n\n{text[:2000]}"
        return self.generate(prompt, system="You are a helpful assistant that provides concise summaries.")
    
    def ask_question(self, question: str, context: Optional[str] = None) -> LocalAIResult:
        """
        Answer a question, optionally with context.
        
        Args:
            question: The question to answer
            context: Optional context/documents to reference
        
        Returns:
            LocalAIResult with answer
        """
        if context:
            prompt = f"Based on the following context, answer the question.\n\nContext:\n{context[:1000]}\n\nQuestion: {question}"
        else:
            prompt = question
        
        system = "You are a helpful, accurate assistant. Answer based on available information."
        return self.generate(prompt, system=system, max_tokens=300)


# Global instance
local_ai = LocalAIModel()
