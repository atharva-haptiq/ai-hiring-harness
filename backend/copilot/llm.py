"""
llm.py — Async wrapper around the local Ollama API.

Exposes two functions:
    ask_llm(prompt, num_predict)    -> str
        Async, non-streaming. Waits for the full response.
        Use for structured JSON outputs (intent classification, scoring).

    stream_llm(prompt, num_predict) -> AsyncGenerator[str, None]
        Async generator. Yields text tokens as Ollama produces them.
        Use for user-facing replies so text appears in real time.

Performance notes
-----------------
* keep_alive=-1  Tells Ollama to never unload the model from RAM.
                 Without this, the default 5-minute idle timeout causes a
                 30–90 s cold-start penalty on the next request.
* Shared client  A single httpx.AsyncClient reuses the TCP connection
                 across calls, saving the ~10 ms handshake on every request.
* num_predict    Caps token generation for short structured responses
                 (e.g. JSON scoring) so the model stops early.
"""

import json
from collections.abc import AsyncGenerator

import httpx

_OLLAMA_URL = "http://localhost:11434/api/generate"
_MODEL = "qwen2.5:7b"

# keep_alive=-1  → model stays loaded in RAM indefinitely.
_KEEP_ALIVE = -1

# Shared client — created once, reused for every request.
# connect: 10 s to establish TCP; read: 180 s for slow CPU generation.
_CLIENT = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=5.0)
)


async def ask_llm(prompt: str, num_predict: int = -1) -> str:
    """
    Async non-streaming call to Ollama. Returns the full generated text.

    Args:
        prompt      -- The full prompt string to send to the model.
        num_predict -- Max tokens to generate (-1 = model default / no cap).
                       Set to a small value (e.g. 256) for JSON responses
                       to cut generation time on CPU.

    Returns:
        The model's response as a plain string.

    Raises:
        RuntimeError -- On connection failure, timeout, or non-200 response.
    """
    payload: dict = {
        "model": _MODEL,
        "prompt": prompt,
        "stream": False,        # Collect full response before returning
        "keep_alive": _KEEP_ALIVE,
    }
    if num_predict > 0:
        payload["options"] = {"num_predict": num_predict}

    try:
        response = await _CLIENT.post(_OLLAMA_URL, json=payload)
    except httpx.ConnectError:
        raise RuntimeError(
            "Could not connect to Ollama at http://localhost:11434. "
            "Make sure Ollama is running (`ollama serve`)."
        )
    except httpx.TimeoutException:
        raise RuntimeError(
            "Ollama did not respond in time. "
            "Try a shorter prompt or check server load."
        )
    except httpx.RequestError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError(f"Ollama response was not valid JSON: {exc}") from exc

    text = data.get("response", "").strip()
    if not text:
        raise RuntimeError("Ollama returned an empty response.")
    return text


async def stream_llm(prompt: str, num_predict: int = -1) -> AsyncGenerator[str, None]:
    """
    Async generator that streams text tokens from Ollama in real time.

    Yields individual text token strings as they arrive from the model.
    The first token typically arrives within 1–3 s even on CPU, giving the
    user immediate visual feedback instead of a blank screen for minutes.

    Args:
        prompt      -- The full prompt string to send to the model.
        num_predict -- Max tokens to generate (-1 = model default / no cap).

    Yields:
        Individual text token strings (typically 1–4 characters each).

    Raises:
        RuntimeError -- On connection failure, timeout, or non-200 response.
    """
    payload: dict = {
        "model": _MODEL,
        "prompt": prompt,
        "stream": True,         # Stream tokens as they are generated
        "keep_alive": _KEEP_ALIVE,
    }
    if num_predict > 0:
        payload["options"] = {"num_predict": num_predict}

    try:
        async with _CLIENT.stream("POST", _OLLAMA_URL, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise RuntimeError(
                    f"Ollama returned HTTP {response.status_code}: "
                    f"{body[:200].decode(errors='replace')}"
                )
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except httpx.ConnectError:
        raise RuntimeError(
            "Could not connect to Ollama at http://localhost:11434."
        )
    except httpx.TimeoutException:
        raise RuntimeError("Ollama stream timed out.")
    except httpx.RequestError as exc:
        raise RuntimeError(f"Ollama stream failed: {exc}") from exc
