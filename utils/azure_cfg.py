# utils/azure_cfg.py
import os
from dotenv import load_dotenv, find_dotenv

def llm_config_default():
    # Load .env next to main.py (does nothing if missing)
    load_dotenv(find_dotenv(filename=".env", raise_error_if_not_found=False))

    endpoint    = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
    api_key     = os.getenv("AZURE_OPENAI_API_KEY")
    deployment  = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    # Quick validation
    missing = [k for k, v in {
        "AZURE_OPENAI_ENDPOINT": endpoint,
        "AZURE_OPENAI_API_KEY": api_key,
        "AZURE_OPENAI_DEPLOYMENT": deployment,
    }.items() if not v]
    if missing:
        raise RuntimeError("Missing Azure OpenAI settings: " + ", ".join(missing))

    # OpenAI v1 SDK: base_url points at the deployment, api-version goes in default_query
    return {
        "config_list": [
            {
                "model": deployment,  # Azure expects the deployment name here
                "api_key": api_key,
                "base_url": f"{endpoint}/openai/deployments/{deployment}",
                "default_query": {"api-version": api_version},
                # DO NOT include "api_version": ... in this dict
            }
        ],
        "cache_seed": 42,
    }
