"""
Ollama LLM Service for generating AI responses.

Connects to a local Ollama instance running qwen2.5-coder:7b
and generates contextual responses for RAG queries.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Generate responses using Ollama with qwen2.5-coder model."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Initialize the LLM service.

        Args:
            host: Ollama server host (default: from settings)
            model: Model name (default: from settings)
            temperature: Sampling temperature (default: from settings)
            top_p: Top-p nucleus sampling (default: from settings)
            timeout: Request timeout in seconds (default: from settings)
        """
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.temperature = temperature if temperature is not None else settings.ollama_temperature
        self.top_p = top_p if top_p is not None else settings.ollama_top_p
        self.timeout = timeout or settings.ollama_timeout

        self._client = None
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify that Ollama is running and accessible."""
        try:
            import requests

            response = requests.get(
                f"{self.host}/api/tags",
                timeout=5,
            )
            if response.status_code != 200:
                logger.warning(
                    f"Ollama connection returned status {response.status_code}. "
                    f"Model may not be available."
                )
        except Exception as e:
            logger.error(
                f"Failed to verify Ollama connection at {self.host}: {e}. "
                f"Make sure Ollama is running."
            )

    def _get_client(self):
        """Lazy-load the Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama
            except ImportError:
                raise ImportError(
                    "ollama package is required. Install with: pip install ollama"
                )
        return self._client

    def generate_response(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The input prompt for the model
            max_tokens: Maximum tokens to generate (default: 1024)

        Returns:
            Generated text response

        Raises:
            RuntimeError: If model generation fails
            ValueError: If prompt is empty
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            client = self._get_client()

            # Use ollama.generate for more control
            response = client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": max_tokens or 1024,
                },
            )

            generated_text = response.get("response", "").strip()

            if not generated_text:
                logger.warning("Ollama returned empty response")
                raise RuntimeError("Model generated empty response")

            logger.info(
                f"Generated response with {len(generated_text)} chars "
                f"in {response.get('total_duration', 0) / 1e9:.2f}s"
            )

            return generated_text

        except ImportError as e:
            logger.error(f"Ollama package not available: {e}")
            raise RuntimeError(
                "LLM service not available. Install ollama package and ensure "
                "Ollama server is running at " + self.host
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    def health_check(self) -> bool:
        """
        Check if Ollama is running and model is available.

        Returns:
            True if healthy, False otherwise
        """
        try:
            import requests

            response = requests.get(
                f"{self.host}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                # Check if our model is available
                if any(self.model in name for name in model_names):
                    return True
                else:
                    logger.warning(
                        f"Model {self.model} not found. Available: {model_names}"
                    )
                    return False
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
