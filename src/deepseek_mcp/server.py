#!/usr/bin/env python3
"""MCP stdio server exposing two DeepSeek tools: deepseek (flash) and advise (pro+thinking)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "deepseek-mcp"
SERVER_VERSION = "0.5.0"

PRICING: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"in": 0.14, "out": 0.28},
    "deepseek-v4-pro": {"in": 0.435, "out": 1.74},
}

DEFAULT_SYSTEM_PROMPT = (
    "You are a precise assistant completing bounded tasks. "
    "Do not fabricate specific numbers, percentages, timeframes, durations, "
    "or statistics unless they appear verbatim in the input. "
    "When asked to be concrete or specific, use qualitative language "
    "rather than invented quantities. "
    "If you are uncertain about a fact, say so explicitly rather than guessing. "
    "Be concise: no preamble, no 'Certainly!', no restatement of the task. "
    "Start your response with the answer. "
    "Use structured output (tables, lists, JSON) when the task calls for it. "
    "Flag ambiguity explicitly with a one-line note rather than silently resolving it. "
    "If the task has sub-parts, address each one."
)

ADVISOR_SYSTEM_PROMPT = (
    "You are a sharp, honest senior advisor consulted when the primary agent needs "
    "a second opinion, deeper analysis, or a check on a consequential decision. "
    "Do not fabricate numbers, percentages, or statistics — if data is absent, say so. "
    "Structure every response in three sections: "
    "(1) CONCLUSION — your direct answer or recommendation in 1-3 sentences. "
    "(2) REASONING — the key factors, evidence, or logic behind your conclusion. "
    "(3) WATCH OUT — caveats, failure modes, alternatives, or what the primary agent "
    "may have missed. Omit this section only if there is genuinely nothing to flag. "
    "Be direct. If the question has no good answer, say so and explain why. "
    "Do not hedge unnecessarily — the primary agent needs a clear signal, not diplomatic fog."
)

EFFORT_LEVELS = {"medium": "medium", "high": "high", "max": "max"}
DEFAULT_EFFORT = "high"

LOG_DIR = os.path.expanduser("~/.deepseek-mcp")
LOG_FILE = os.path.join(LOG_DIR, "calls.jsonl")


def api_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )


def _api_key_status() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        return "missing"
    if len(key) < 8:
        return "too-short"
    return "set"


def _log_call(entry: dict[str, Any]) -> None:
    if not os.environ.get("DEEPSEEK_MCP_LOG"):
        return
    os.makedirs(LOG_DIR, exist_ok=True)
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


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
            "complex multi-factor analysis, or anything where being wrong has real cost. "
            "Defaults to effort=max — exhaustive reasoning. "
            "Returns structured response: CONCLUSION / REASONING / WATCH OUT. "
            "More expensive (~6x flash) and slower (60-120s). "
            "Use effort=medium or high only when you need a quicker lighter read."
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
                    "default": "max",
                    "description": (
                        "Reasoning depth. "
                        "max (default): exhaustive, for the hardest decisions (~90-120s). "
                        "high: full chain-of-thought + alternatives (~60s). "
                        "medium: lighter thinking, quicker (~30s)."
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


def _compute_cost(usage: Any, model: str) -> float | None:
    pricing = PRICING.get(model)
    if not pricing or usage is None:
        return None
    prompt_tokens = getattr(usage, "prompt_tokens", None) or 0
    completion_tokens = getattr(usage, "completion_tokens", None) or 0
    cost = (prompt_tokens * pricing["in"] + completion_tokens * pricing["out"]) / 1_000_000
    return cost


def _format_cost(cost: float | None) -> str:
    if cost is None:
        return ""
    if cost < 0.0001:
        return "  cost=<$0.0001"
    return f"  cost=${cost:.4f}"


def call_deepseek(args: dict[str, Any], progress_token: Any = None) -> str:
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

    text, usage, _reasoning = _collect_stream(stream, progress_token)
    result = _format_result(text, usage, model, started_at)
    cost = _compute_cost(usage, model)
    _log_call({
        "tool": "deepseek", "model": model,
        "tokens_in": getattr(usage, "prompt_tokens", None) if usage else None,
        "tokens_out": getattr(usage, "completion_tokens", None) if usage else None,
        "latency_s": round(time.time() - started_at, 2),
        "cost_usd": round(cost, 6) if cost else None,
    })
    return result


def call_advisor(args: dict[str, Any], progress_token: Any = None) -> str:
    system_parts = [ADVISOR_SYSTEM_PROMPT]
    if args.get("system"):
        system_parts.append(args["system"])
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": args["prompt"]},
    ]

    effort = EFFORT_LEVELS.get(args.get("effort", "max"), "max")
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

    text, usage, reasoning_text = _collect_stream(stream, progress_token)
    result = _format_result(text, usage, f"{model}·{effort}", started_at)
    cost = _compute_cost(usage, model)
    _log_call({
        "tool": "advise", "model": model, "effort": effort,
        "tokens_in": getattr(usage, "prompt_tokens", None) if usage else None,
        "tokens_out": getattr(usage, "completion_tokens", None) if usage else None,
        "latency_s": round(time.time() - started_at, 2),
        "cost_usd": round(cost, 6) if cost else None,
    })
    if reasoning_text:
        result = f"<reasoning>\n{reasoning_text}\n</reasoning>\n\n{result}"
    return result


def _collect_stream(stream: Any, progress_token: Any) -> tuple[str, Any, str]:
    text = ""
    reasoning = ""
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
        if chunk.choices and getattr(chunk.choices[0].delta, "reasoning_content", None):
            reasoning += chunk.choices[0].delta.reasoning_content
        if getattr(chunk, "usage", None):
            usage = chunk.usage

    return text, usage, reasoning


def _format_result(text: str, usage: Any, model_label: str, started_at: float) -> str:
    elapsed = round(time.time() - started_at, 2)
    model = model_label.split("·")[0]
    cost = _compute_cost(usage, model)
    metadata = [f"model={model_label}", f"latency={elapsed}s"]
    if usage:
        metadata.append(f"tokens={usage.prompt_tokens}+{usage.completion_tokens}")
    cost_str = _format_cost(cost)
    if cost_str:
        metadata.append(cost_str)
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
        key_status = _api_key_status()
        if key_status != "set":
            print(
                "deepseek-mcp: DEEPSEEK_API_KEY not set. "
                "Get a key at platform.deepseek.com and add to your MCP config env.",
                file=sys.stderr,
                flush=True,
            )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                    "apiKey": key_status,
                },
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
