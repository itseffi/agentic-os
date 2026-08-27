#!/usr/bin/env python3
"""Shared OpenAI-compatible chat client for the eval runners.

Kept separate so run_skill_evals.py and run_routing_evals.py query models the same way, and
so the failure modes are handled in one place. The previous inline version raised bare
HTTPError on any non-200, returned None when a response carried a null content, and surfaced
API error objects as KeyError: 'choices'.
"""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class ModelError(RuntimeError):
    """A model request failed. Carries a message fit to record in a results file."""


def _extract_api_error(body: str) -> str | None:
    """Pull a message out of an API error payload, if that is what this is."""
    try:
        data = json.loads(body)
    except Exception:
        return None
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        return str(data["error"].get("message") or data["error"])
    if isinstance(data, dict) and isinstance(data.get("error"), str):
        return data["error"]
    return None


def query_chat(
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_input: str,
    temperature: float = 0.0,
    timeout: int = 120,
) -> str:
    """Send one chat completion and return the assistant text.

    Raises ModelError with a readable message for transport failures, non-200 responses,
    API error payloads, and responses that do not carry an assistant message.
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": temperature,
    }
    req = request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        detail = _extract_api_error(body) or (body[:200].strip() if body else "")
        raise ModelError(f"HTTP {exc.code} from {base_url}" + (f": {detail}" if detail else "")) from exc
    except error.URLError as exc:
        raise ModelError(f"could not reach {base_url}: {exc.reason}") from exc
    except OSError as exc:
        raise ModelError(f"could not reach {base_url}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelError(f"response was not JSON: {raw[:200].strip()}") from exc

    # A 200 carrying an error object is common for auth and quota problems.
    api_error = _extract_api_error(raw)
    if api_error:
        raise ModelError(f"API error: {api_error}")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelError(f"response had no choices: {raw[:200].strip()}")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        # Refusals and tool-call responses carry a null content. Returning None here used to
        # crash downstream scoring with AttributeError on NoneType.
        raise ModelError("response carried a null content (refusal or tool call)")
    return str(content)
