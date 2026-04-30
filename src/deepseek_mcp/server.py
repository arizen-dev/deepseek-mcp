#!/usr/bin/env python3
"""MCP stdio server that exposes DeepSeek as a single tool."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from openai import OpenAI

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "deepseek-mcp"
SERVER_VERSION = "0.1.0"


def api_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )


TOOLS: list[dict[str, Any]] = [
    {
        "name": "deepseek",
        "title": "DeepSeek",
        "description": (
            "Delegate a bounded task to DeepSeek. Best for classification, "
            "summarization, JSON edits, table generation, template population, "
            "and pattern-copy refactors. Not for architecture decisions, "
            "security policy, or client-facing final prose. Returns result text "
            "plus latency/token metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Task prompt"},
                "system": {"type": "string", "description": "Optional system prompt"},
                "model": {
                    "type": "string",
                    "default": "deepseek-v4-flash",
                    "description": (
                        "deepseek-v4-flash (fast, default) or "
                        "deepseek-v4-pro (slower, stronger reasoning)"
                    ),
                },
            },
            "required": ["prompt"],
        },
        "annotations": {
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    }
]


def call_deepseek(args: dict[str, Any], progress_token: Any = None) -> str:
    messages: list[dict[str, str]] = []
    if args.get("system"):
        messages.append({"role": "system", "content": args["system"]})
    messages.append({"role": "user", "content": args["prompt"]})

    model = args.get("model", "deepseek-v4-flash")
    started_at = time.time()

    stream = api_client().chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    text = ""
    usage = None
    chunk_count = 0

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            delta = chunk.choices[0].delta.content
            text += delta
            chunk_count += 1
            if progress_token is not None and chunk_count % 20 == 0:
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {
                        "progressToken": progress_token,
                        "progress": chunk_count,
                        "message": f"{len(text)} chars received",
                    },
                }
                print(json.dumps(notification), flush=True)
        if getattr(chunk, "usage", None):
            usage = chunk.usage

    elapsed = round(time.time() - started_at, 2)
    metadata = [f"model={model}", f"latency={elapsed}s"]
    if usage:
        metadata.append(f"tokens={usage.prompt_tokens}+{usage.completion_tokens}")

    return f"{text}\n\n---\n_deepseek · {'  '.join(metadata)}_"


def error_text(exc: Exception) -> str:
    raw = str(exc)
    lowered = raw.lower()
    if "402" in raw or "insufficient" in lowered:
        return f"DeepSeek API: insufficient balance. Add credits at platform.deepseek.com. ({raw})"
    if "401" in raw or "authentication" in lowered:
        return f"DeepSeek API: invalid key. Check DEEPSEEK_API_KEY. ({raw})"
    if "timeout" in lowered:
        return f"DeepSeek API: request timed out. Try a shorter prompt. ({raw})"
    return raw


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS},
        }

    if method == "tools/call":
        params = request.get("params", {})
        args = params.get("arguments", {})
        progress_token = params.get("_meta", {}).get("progressToken")
        try:
            text = call_deepseek(args, progress_token)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"ERROR: {error_text(exc)}"}],
                    "isError": True,
                },
            }

    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Unknown method: {method}",
        },
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            response = handle(json.loads(line))
            if response is not None:
                print(json.dumps(response), flush=True)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32603, "message": str(exc)},
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
