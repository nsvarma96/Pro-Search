from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except Exception:
        return os.getenv(name, default)


@dataclass(frozen=True)
class AppConfig:
    searxng_url: str = ""
    brave_api_key: str = ""
    tavily_api_key: str = ""
    serpapi_api_key: str = ""
    llm_provider: str = "auto"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-70b-instruct"
    together_api_key: str = ""
    together_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    custom_openai_api_key: str = ""
    custom_openai_base_url: str = ""
    custom_openai_model: str = ""
    request_timeout: int = 15

    @classmethod
    def from_streamlit(cls) -> "AppConfig":
        return cls(
            searxng_url=_secret("SEARXNG_URL"),
            brave_api_key=_secret("BRAVE_API_KEY"),
            tavily_api_key=_secret("TAVILY_API_KEY"),
            serpapi_api_key=_secret("SERPAPI_API_KEY"),
            llm_provider=_secret("LLM_PROVIDER", "auto").lower(),
            openai_api_key=_secret("OPENAI_API_KEY"),
            openai_model=_secret("OPENAI_MODEL", "gpt-4o-mini"),
            anthropic_api_key=_secret("ANTHROPIC_API_KEY"),
            anthropic_model=_secret("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            groq_api_key=_secret("GROQ_API_KEY"),
            groq_model=_secret("GROQ_MODEL", "llama-3.1-70b-versatile"),
            openrouter_api_key=_secret("OPENROUTER_API_KEY"),
            openrouter_model=_secret("OPENROUTER_MODEL", "meta-llama/llama-3.1-70b-instruct"),
            together_api_key=_secret("TOGETHER_API_KEY"),
            together_model=_secret("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            ollama_base_url=_secret("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=_secret("OLLAMA_MODEL", "llama3.1"),
            custom_openai_api_key=_secret("CUSTOM_OPENAI_API_KEY"),
            custom_openai_base_url=_secret("CUSTOM_OPENAI_BASE_URL"),
            custom_openai_model=_secret("CUSTOM_OPENAI_MODEL"),
        )
