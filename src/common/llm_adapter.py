"""LLM adapter for content analysis and report generation."""
from __future__ import annotations
import sys
import pathlib
from typing import Dict, Any

# Add parent directory to path to access existing LLM modules
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT))

try:
    from llm_wrapper import llm_prompt
    from llm_config import LLM_CONFIG_OLLAMA
except ImportError:
    # Fallback if modules not available
    def llm_prompt(prompt: str, config: Dict[str, Any] = None) -> str:
        return f"[MOCK LLM RESPONSE] Analysis for: {prompt[:100]}..."
    
    LLM_CONFIG_OLLAMA = {
        "model_name": "llama3.1:8b-instruct-q4_0",
        "temperature": 0.2,
        "n_ctx": 8000
    }

def complete(cfg, prompt: str) -> str:
    """Complete a prompt using the configured LLM."""
    # Use the radar config to override LLM settings if provided
    llm_config = LLM_CONFIG_OLLAMA.copy()
    if hasattr(cfg, 'llm') and cfg.llm:
        if 'chat_model' in cfg.llm:
            llm_config['model_name'] = cfg.llm['chat_model']
        if 'temperature' in cfg.llm:
            llm_config['temperature'] = cfg.llm['temperature']
        if 'max_tokens' in cfg.llm:
            llm_config['n_ctx'] = cfg.llm['max_tokens']
    
    try:
        return llm_prompt(prompt, llm_config)
    except Exception as e:
        return f"[LLM ERROR] {str(e)}"