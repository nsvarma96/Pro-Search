# Ultimate Search

A Streamlit research dashboard for consultant-style questions that need cited, source-grounded answers.

The app works as a general research workflow engine:

1. Break a question into a research plan.
2. Search trusted public sources and optional web search.
3. Rank evidence by relevance, source type, geography, and recency.
4. Generate a cited brief with caveats and source links.
5. Export the evidence table or brief.

## Features

- Mobile-friendly Streamlit UI
- Source connectors for:
  - PubMed / NCBI E-utilities
  - Europe PMC
  - ClinicalTrials.gov
  - openFDA drug labels
  - Optional SearXNG metasearch
- Evidence table with source quality signals
- Extractive synthesis that works without an LLM API key
- Optional LLM synthesis with OpenAI-compatible APIs
- CSV, Excel, and Word exports

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Optional LLM Secrets

Create `.streamlit/secrets.toml` locally, or add these in Streamlit Community Cloud secrets:

```toml
# Pick one provider, or add several and let the app auto-select.
LLM_PROVIDER = "auto" # auto, extractive, openai, anthropic, groq, openrouter, together, ollama, custom

# ChatGPT / OpenAI
OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-4o-mini"

# Claude / Anthropic
ANTHROPIC_API_KEY = "..."
ANTHROPIC_MODEL = "claude-3-5-haiku-latest"

# Groq, useful for fast hosted open-weight models
GROQ_API_KEY = "..."
GROQ_MODEL = "llama-3.1-70b-versatile"

# OpenRouter, useful for trying many open and closed models
OPENROUTER_API_KEY = "..."
OPENROUTER_MODEL = "meta-llama/llama-3.1-70b-instruct"

# Together AI, useful for hosted open-weight models
TOGETHER_API_KEY = "..."
TOGETHER_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

# Local/self-hosted Ollama. This normally works locally or on your own server,
# not on Streamlit Community Cloud.
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1"

# Any OpenAI-compatible endpoint
CUSTOM_OPENAI_API_KEY = "..."
CUSTOM_OPENAI_BASE_URL = "https://your-provider.example/v1"
CUSTOM_OPENAI_MODEL = "your-model-name"
```

## Optional Search Secrets

```toml
# Optional: public web metasearch instance
SEARXNG_URL = "https://your-searxng-instance/search"
```

If no LLM key is configured, the app still runs and generates an extractive, cited brief from retrieved sources.

## Deploy To Streamlit Community Cloud

1. Push this folder to GitHub.
2. Go to Streamlit Community Cloud.
3. Create a new app pointing to `app.py`.
4. Add optional secrets from above.
5. Deploy.

## Suggested Usage

Good inputs look like:

- What is the prevalence of Rett syndrome in the USA?
- What is an antibody drug conjugate and which ones are approved in UAE?
- What regulatory challenges affect orphan drugs in South Africa?
- Compare HTA pathways for rare oncology products in France, Germany, and England.

Use `Standard` or `Deep` mode when you want broader evidence gathering.

## Notes

This is a research assistant, not a medical, legal, or regulatory authority. Always verify critical facts against the cited primary sources before client use.
