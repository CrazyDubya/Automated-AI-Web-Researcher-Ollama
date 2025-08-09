"""Adapter to existing llm_wrapper (if present) or simple HTTP call to Ollama.
Future enhancement: streaming, error handling, retries, embeddings.
"""
import json, subprocess

# Simple approach: call `ollama run ` via subprocess to avoid new deps.
# For larger contexts consider using the HTTP API. This stub keeps it minimal.

def complete(cfg, prompt: str) -> str:
    model = cfg.llm.get('chat_model', 'llama3')
    try:
        result = subprocess.run([
            'ollama', 'run', model, prompt
        ], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return f"[LLM ERROR]\n{result.stderr}\nPrompt (truncated):\n{prompt[:500]}"
        return result.stdout.strip()
    except FileNotFoundError:
        return f"[LLM ERROR] ollama not found. Install Ollama or adjust configuration."
    except subprocess.TimeoutExpired:
        return f"[LLM ERROR] timeout while generating."