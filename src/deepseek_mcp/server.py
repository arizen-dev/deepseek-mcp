#!/usr/bin/env python3
"""MCP stdio server exposing two DeepSeek tools: deepseek (flash) and advise (pro+thinking)."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from openai import OpenAI

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "deepseek-mcp"
SERVER_VERSION = "0.3.0"

# Injected into every call. Guards against the confirmed failure mode where DeepSeek
# invents plausible-sounding numbers when asked for "concrete" output.
DEFAULT_SYSTEM_PROMPT = (
    "You are a precise assistant completing bounded tasks. "
    "Do not fabricate specific numbers, percentages, timeframes, durations, "
    "or statistics unless they appear verbatim in the input. "
    "When asked to be concrete or specific, use qualitative language "
    "rather than invented quantities. "
    "If you are uncertain about a fact, say so explicitly rather than guessing."
)

ADVISOR_SYSTEM_PROMPT = (
    "You are a sharp, honest advisor consulted when the primary agent needs "
    "a second opinion or deeper analysis. "
    "Do not fabricate numbers, percentages, or statistics — if data is absent, say so. "
    "Structure your response: first state your conclusion, then your reasoning, "
    "then any important caveats or alternatives the primary agent should consider. "
    "Be direct. If the question has no good answer, say that."
)

# reasoning_effort values accepted by deepseek-v4-pro thinking mode
EFFORT_LEVELS = {"medium": "medium", "high": "high", "max": "max"}
DEFAULT_EFFORT = "high"


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
            "Fast, cheap task execution via DeepSeek V4 Flash (non-thinking mode). "
            "Best for: classification, summarization, JSON edits, table generation, "
            "template population, pattern-copy refactors, inbox triage. "
            "Not for: architecture decisions, judgment under ambiguity, security policy, "
            "client-facing final prose. "
            "Typical latency: 2-5s. Use `advise` when you need deeper reasoning."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Task prompt"},
                "system": {
                    "type": "string",
                    "description": (
                        "Optional additional system instructions. "
                        "Appended after the built-in epistemic honesty guard."
                    ),
                },
            },
            "required": ["prompt"],
        },
        "annotations": {
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    },
    {
        "name": "advise",
        "title": "DeepSeek Advisor",
        "description": (
            "Deep reasoning via DeepSeek V4 Pro with thinking mode enabled. "
            "Use when `deepseek` is not sufficient: judgment under ambiguity, "
            "architectural tradeoffs, second opinions on consequential decisions, "
            "complex analysis, or anything where being wrong has real cost. "
            "More expensive (~6x flash) and slower (30-120s). "
            "effort=high (default): chain-of-thought reasoning. "
            "effort=max: exhaustive analysis, best for the hardest calls."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Question or problem to reason about"},
                "system": {
                    "type": "string",
                    "description": "Optional additional context or constraints for the advisor.",
                },
                "effort": {
                    "type": "string",
                    "enum": ["medium", "high", "max"],
                    "default": "high",
                    "description": (
                        "Reasoning depth. "
                        "medium: careful response, lighter thinking. "
                        "high (default): full chain-of-thought, alternatives considered. "
                        "max: exhaustive — use for the hardest decisions."
                    ),
                },
            },
            "required": ["prompt"],
        },
        "annotations": {
            "readOnlyHint": True,
            "idempotentHint": False,
        },
    },
]


def call_deepseek(args: dict[str, Any], progress_token: Any = None) -> str:
    """Flash tool — non-thinking mode for fast mechanical tasks."""
    system_parts = [DEFAULT_SYSTEM_PROMPT]
    if args.get("system"):
        system_parts.append(args["system"])
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": args["prompt"]},
    ]

    started_at = time.time()
    model = "deepseek-v4-flash"

    stream = api_client().chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
        extra_body={"thinking": {"type": "disabled"}},
    )

    text, usage = _collect_stream(stream, progress_token)
    return _format_result(text, usage, model, started_at)


def call_advisor(args: dict[str, Any], progress_token: Any = None) -> str:
    """Advisor tool — pro model with thinking mode and configurable effort."""
    system_parts = [ADVISOR_SYSTEM_PROMPT]
    if args.get("system"):
        system_parts.append(args["system"])
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": args["prompt"]},
    ]

    effort = EFFORT_LEVELS.get(args.get("effort", DEFAULT_EFFORT), DEFAULT_EFFORT)
    started_at = time.time()
    model = "deepseek-v4-pro"

    stream = api_client().chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
        extra_body={
            "thinking": {"type": "enabled"},
            "reasoning_effort": effort,
        },
    )

    text, usage = _collect_stream(stream, progress_token)
    meta = _format_result(text, usage, f"{model}·{effort}", started_at)
    return meta


def _collect_stream(stream: Any, progress_token: Any) -> tuple[str, Any]:
    text = ""
    usage = None
    chunk_count = 0

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            delta = chunk.choices[0].delta.content
            text += delta
            chunk_count += 1
            if progress_token is not None and chunk_count % 20 == 0:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {
                        "progressToken": progress_token,
                        "progress": chunk_count,
                        "message": f"{len(text)} chars received",
                    },
                }), flush=True)
        if getattr(chunk, "usage", None):
            usage = chunk.usage

    return text, usage


def _format_result(text: str, usage: Any, model_label: str, started_at: float) -> str:
    elapsed = round(time.time() - started_at, 2)
    metadata = [f"model={model_label}", f"latency={elapsed}s"]
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
        tool_name = params.get("name")
        args = params.get("arguments", {})
        progress_token = params.get("_meta", {}).get("progressToken")
        try:
            if tool_name == "advise":
                text = call_advisor(args, progress_token)
            else:
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
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
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
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(exc)},
            }), flush=True)


if __name__ == "__main__":
    main()
