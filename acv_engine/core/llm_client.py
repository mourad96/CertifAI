"""LLM Client supporting Gemini, OpenAI, Anthropic, and offline fallback."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from acv_engine.config import ACVConfig, default_config

logger = logging.getLogger("acv_engine.llm")


def clean_json_response(text: str) -> Any:
    """Extract and parse JSON from LLM response text, stripping markdown code fences if present."""
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try finding the first [ or { and matching last ] or }
        first_bracket = min([i for i in [text.find("["), text.find("{")] if i != -1], default=-1)
        last_bracket = max([text.rfind("]"), text.rfind("}")])
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            sub = text[first_bracket : last_bracket + 1]
            return json.loads(sub)
        raise ValueError(f"Failed to parse valid JSON from LLM response: {e}\nRaw output: {text[:200]}...")


class LLMClient:
    """Unified client for interacting with LLM providers with user-configured settings."""

    def __init__(self, config: Optional[ACVConfig] = None):
        self.config = config or default_config
        self.provider = self.config.resolve_provider()

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text from the configured provider."""
        if self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        elif self.provider == "offline":
            raise RuntimeError(
                "Offline mode is active. No LLM provider configured or no API keys found. "
                "Use deterministic static synthesis or set GEMINI_API_KEY / GOOGLE_API_KEY."
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        """Generate response and parse into Python JSON data structure."""
        resp_text = self.generate(system_prompt, user_prompt)
        return clean_json_response(resp_text)

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        api_key = self.config.gemini_api_key
        # Try google.genai first
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            config_kwargs = {"system_instruction": system_prompt}
            if self.config.temperature is not None:
                config_kwargs["temperature"] = self.config.temperature

            config = types.GenerateContentConfig(**config_kwargs)
            response = client.models.generate_content(
                model=self.config.model_name,
                contents=user_prompt,
                config=config,
            )
            return response.text or ""
        except ImportError:
            # Fallback to google.generativeai
            import google.generativeai as genai_legacy

            genai_legacy.configure(api_key=api_key)
            generation_config = {}
            if self.config.temperature is not None:
                generation_config["temperature"] = self.config.temperature

            model = genai_legacy.GenerativeModel(
                model_name=self.config.model_name,
                system_instruction=system_prompt,
                generation_config=generation_config or None,
            )
            response = model.generate_content(user_prompt)
            return response.text or ""

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        import openai

        client = openai.OpenAI(api_key=self.config.openai_api_key)
        kwargs = {
            "model": self.config.model_name if "gpt" in self.config.model_name else "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature

        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
        kwargs = {
            "model": self.config.model_name if "claude" in self.config.model_name else "claude-3-5-sonnet-20241022",
            "system": system_prompt,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature

        resp = client.messages.create(**kwargs)
        return resp.content[0].text
