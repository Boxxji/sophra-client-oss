"""Sophra Universal Active Agent Optimizer (Python v2.1.0).

Works with ANY Python AI agent framework worldwide (OpenAI SDK, Anthropic SDK,
Google Gemini, LangChain, CrewAI, AutoGen, PydanticAI, LlamaIndex, LiteLLM,
Ollama, custom agents) with zero external dependencies.

Features:
  1. Real tool-call & assistant repetition loop detection + hard circuit-breaker
  2. Mechanical deduplication of repeated tool calls & paired tool outputs
  3. Oversized tool/context payload pruning (head 65% + tail 25% preserved)
  4. Sliding-window middle-turn compaction to enforce token budgets
  5. Same-provider FinOps economy model routing (gpt-4o -> gpt-4o-mini, etc.)
  6. Anti-loop / anti-hallucination system prompt therapy injection
  7. Optional real telemetry reporting to https://sophra.me/api/vitals
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

OPTIMIZER_VERSION = "2.1.0"

MODEL_DOWNGRADE_MAP: Dict[str, str] = {
    # OpenAI
    "gpt-4o": "gpt-4o-mini",
    "gpt-4-turbo": "gpt-4o-mini",
    "gpt-4": "gpt-4o-mini",
    "gpt-4.1": "gpt-4.1-mini",
    "gpt-4.1-mini": "gpt-4.1-nano",
    "gpt-5": "gpt-5-mini",
    "o1": "o3-mini",
    "o3": "o3-mini",
    # Anthropic
    "claude-4-6-opus": "claude-4-5-haiku",
    "claude-opus-4-6": "claude-haiku-4-5",
    "claude-3-opus-20240229": "claude-3-5-haiku-20241022",
    "claude-4-5-sonnet": "claude-4-5-haiku",
    "claude-sonnet-4-5": "claude-haiku-4-5",
    "claude-3-5-sonnet": "claude-3-5-haiku",
    "claude-3-5-sonnet-20241022": "claude-3-5-haiku-20241022",
    # Google Gemini
    "gemini-2.5-pro": "gemini-2.5-flash",
    "gemini-2.0-pro": "gemini-2.0-flash",
    "gemini-1.5-pro": "gemini-1.5-flash",
    # Mistral / DeepSeek / xAI
    "mistral-large-latest": "mistral-small-latest",
    "deepseek-reasoner": "deepseek-chat",
    "grok-3": "grok-3-mini",
}

INPUT_COST_PER_1K: Dict[str, float] = {
    "gpt-4o": 0.0025, "gpt-4o-mini": 0.00015, "gpt-4-turbo": 0.01, "gpt-4": 0.03,
    "gpt-4.1": 0.002, "gpt-4.1-mini": 0.0004, "gpt-4.1-nano": 0.0001, "gpt-5": 0.005, "gpt-5-mini": 0.0005,
    "o1": 0.015, "o3": 0.01, "o3-mini": 0.0011,
    "claude-4-6-opus": 0.015, "claude-opus-4-6": 0.015, "claude-3-opus-20240229": 0.015,
    "claude-4-5-sonnet": 0.003, "claude-sonnet-4-5": 0.003, "claude-3-5-sonnet": 0.003, "claude-3-5-sonnet-20241022": 0.003,
    "claude-4-5-haiku": 0.0008, "claude-haiku-4-5": 0.0008, "claude-3-5-haiku": 0.0008, "claude-3-5-haiku-20241022": 0.0008,
    "gemini-2.5-pro": 0.00125, "gemini-2.5-flash": 0.00015, "gemini-1.5-pro": 0.00125, "gemini-1.5-flash": 0.000075,
    "mistral-large-latest": 0.002, "mistral-small-latest": 0.0002,
    "deepseek-reasoner": 0.00055, "deepseek-chat": 0.00027,
    "grok-3": 0.003, "grok-3-mini": 0.0003,
}

_COMPLEX_PATTERN = re.compile(r"architect|prove|theorem|security audit|refactor entire|write a full", re.I)


def _extract_text(msg: Dict[str, Any]) -> str:
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(str(p.get("text") or p.get("content") or json.dumps(p)))
        return "\n".join(parts)
    if content is not None:
        return json.dumps(content, ensure_ascii=False)
    return ""


def _tool_signature(msg: Dict[str, Any]) -> str:
    if not isinstance(msg, dict):
        return ""
    tool_calls = msg.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        sigs = []
        for tc in tool_calls:
            fn = tc.get("function") if isinstance(tc, dict) and isinstance(tc.get("function"), dict) else tc
            if isinstance(fn, dict):
                name = fn.get("name") or "tool"
                args = fn.get("arguments")
                arg_str = args if isinstance(args, str) else json.dumps(args or {}, sort_keys=True)
                sigs.append(f"{name}({arg_str})")
        return ";".join(sigs)
    fc = msg.get("function_call")
    if isinstance(fc, dict):
        return f"{fc.get('name') or 'fn'}({fc.get('arguments') or ''})"
    return ""


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    s = str(text)
    if not s:
        return 0
    char_est = len(s) / 3.8
    word_est = len(s.split()) * 1.32
    return max(1, round(char_est * 0.65 + word_est * 0.35))


def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    total = 3
    for m in messages or []:
        total += 4 + estimate_tokens(_extract_text(m)) + estimate_tokens(_tool_signature(m))
    return total


def _hash_norm(text: str) -> str:
    norm = re.sub(r"\s+", " ", str(text or "").lower()).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _input_cost_1k(model: str) -> float:
    m = (model or "").strip()
    bare = m.split("/")[-1] if "/" in m else m
    if m in INPUT_COST_PER_1K:
        return INPUT_COST_PER_1K[m]
    if bare in INPUT_COST_PER_1K:
        return INPUT_COST_PER_1K[bare]
    return 0.003


def resolve_fallback_model(model: str, explicit_fallback: Optional[str] = None) -> str:
    if explicit_fallback and explicit_fallback != model:
        return explicit_fallback
    m = (model or "").strip()
    if m in MODEL_DOWNGRADE_MAP:
        return MODEL_DOWNGRADE_MAP[m]
    if "/" in m:
        prefix, bare = m.split("/", 1)
        if bare in MODEL_DOWNGRADE_MAP:
            return f"{prefix}/{MODEL_DOWNGRADE_MAP[bare]}"
    return model


def optimize_messages(
    messages: List[Dict[str, Any]],
    *,
    agent_id: str = "python-agent",
    model: str = "gpt-4o",
    max_input_tokens: int = 12000,
    max_tool_output_chars: int = 2400,
    keep_recent_turns: int = 6,
    allow_model_switch: bool = True,
    smart_routing: bool = False,
    fallback_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Mechanically optimize any OpenAI/Anthropic-style messages[] list."""
    safe = [dict(m) if isinstance(m, dict) else m for m in (messages or [])]
    tokens_before = estimate_messages_tokens(safe)
    cost_before_1k = _input_cost_1k(model)

    # 1. Loop detection
    sig_counts: Dict[str, int] = {}
    seen_assistant: Dict[str, int] = {}
    prev_sig: Optional[str] = None
    consec = 0
    max_consec = 0
    extra_tool = 0
    repeat_asst = 0

    for m in safe:
        ts = _tool_signature(m)
        if ts:
            h = _hash_norm(ts)
            cnt = sig_counts.get(h, 0) + 1
            sig_counts[h] = cnt
            if cnt > 1:
                extra_tool += 1
            if h == prev_sig:
                consec += 1
                if consec > max_consec:
                    max_consec = consec
            else:
                consec = 0
                prev_sig = h
        elif isinstance(m, dict) and m.get("role") == "assistant":
            txt = _extract_text(m).strip()
            if len(txt) >= 24:
                h = _hash_norm(txt)
                if seen_assistant.get(h, 0) >= 1:
                    repeat_asst += 1
                seen_assistant[h] = seen_assistant.get(h, 0) + 1

    loop_count = extra_tool + repeat_asst
    is_critical_loop = max_consec >= 3 or extra_tool >= 4 or repeat_asst >= 3

    if is_critical_loop:
        prevented = max(tokens_before, tokens_before * 3)
        return {
            "optimizer_version": OPTIMIZER_VERSION,
            "agent_id": agent_id,
            "decision": "CIRCUIT_BREAK_PAUSE",
            "allow_execution": False,
            "reasons": [f"Critical execution loop detected ({loop_count} repeated calls/turns, {max_consec} consecutive)"],
            "model": model,
            "recommended_model": resolve_fallback_model(model, fallback_model),
            "messages": safe,
            "halt_response": {
                "role": "assistant",
                "content": f"[Sophra Circuit-Breaker] Execution halted automatically to prevent runaway token burn ({loop_count} repeated calls/turns detected).",
            },
            "optimization_stats": {
                "tokens_before": tokens_before,
                "tokens_after": 0,
                "tokens_saved": tokens_before,
                "projected_loop_tokens_prevented": prevented,
                "reduction_pct": 100.0,
                "duplicates_removed": 0,
                "tool_outputs_pruned": 0,
                "middle_turns_compacted": 0,
                "model_switched": False,
                "loop_count": loop_count,
                "estimated_savings_usd": round((prevented / 1000.0) * cost_before_1k, 6),
            },
        }

    optimized = safe
    duplicates_removed = 0
    tool_outputs_pruned = 0
    middle_turns_compacted = 0
    reasons: List[str] = []

    # 2. Tool-loop deduplication
    if extra_tool > 0:
        drop_ids = set()
        seen: Dict[str, int] = {}
        deduped = []
        for m in optimized:
            ts = _tool_signature(m)
            if ts:
                h = _hash_norm(ts)
                cnt = seen.get(h, 0) + 1
                seen[h] = cnt
                if cnt > 1:
                    duplicates_removed += 1
                    for tc in (m.get("tool_calls") or []):
                        if isinstance(tc, dict) and tc.get("id"):
                            drop_ids.add(tc["id"])
                    continue
            if isinstance(m, dict) and m.get("role") == "tool" and m.get("tool_call_id") in drop_ids:
                duplicates_removed += 1
                continue
            deduped.append(m)
        optimized = deduped
        if duplicates_removed > 0:
            reasons.append(f"Deduplicated {duplicates_removed} redundant tool-loop message(s)")

    # 3. Verbose tool/context output pruning
    pruned_list = []
    n_msgs = len(optimized)
    for idx, m in enumerate(optimized):
        if isinstance(m, dict) and isinstance(m.get("content"), str) and m.get("role") not in ("system", "developer"):
            is_tool = m.get("role") in ("tool", "function")
            limit = max_tool_output_chars if is_tool else (max_tool_output_chars * 4 if idx >= n_msgs - 2 else max_tool_output_chars * 2)
            content = m["content"]
            if len(content) > limit:
                head = int(limit * 0.65)
                tail = int(limit * 0.25)
                omitted = len(content) - head - tail
                m = dict(m)
                m["content"] = f"{content[:head]}\n\n[... Sophra Context Pruner: {omitted} chars trimmed ...]\n\n{content[-tail:]}"
                tool_outputs_pruned += 1
        pruned_list.append(m)
    optimized = pruned_list
    if tool_outputs_pruned > 0:
        reasons.append(f"Pruned {tool_outputs_pruned} oversized tool/context payload(s)")

    # 4. Sliding-window middle-turn compaction
    if estimate_messages_tokens(optimized) > max_input_tokens and len(optimized) > keep_recent_turns + 2:
        sys_msgs = [m for m in optimized if isinstance(m, dict) and m.get("role") in ("system", "developer")]
        non_sys = [m for m in optimized if not (isinstance(m, dict) and m.get("role") in ("system", "developer"))]
        if len(non_sys) > keep_recent_turns + 1:
            first_goal = non_sys[0]
            tail = non_sys[-keep_recent_turns:]
            middle = non_sys[1:-keep_recent_turns]
            middle_turns_compacted = len(middle)
            while len(tail) > 1 and isinstance(tail[0], dict) and tail[0].get("role") == "tool":
                tail = tail[1:]
                middle_turns_compacted += 1
            topics = [
                re.sub(r"\s+", " ", _extract_text(m)).strip()[:80]
                for m in middle
                if isinstance(m, dict) and m.get("role") == "user" and _extract_text(m).strip()
            ][:5]
            digest = f"[Sophra Context Compactor — {middle_turns_compacted} older turn(s) compacted]"
            if topics:
                digest += "\nPrior topics: " + " | ".join(topics)
            optimized = [*sys_msgs, first_goal, {"role": "assistant", "content": digest}, *tail]
            reasons.append(f"Compacted {middle_turns_compacted} middle turn(s) to enforce {max_input_tokens}-token budget")

    # 5. FinOps model routing
    recommended_model = model
    model_switched = False
    decision = "OPTIMIZED" if (duplicates_removed or tool_outputs_pruned or middle_turns_compacted) else "ALLOW"
    last_user_text = ""
    for m in reversed(optimized):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user_text = _extract_text(m)
            break
    simple_turn = smart_routing and tokens_before < 350 and len(last_user_text) < 220 and not _COMPLEX_PATTERN.search(last_user_text)
    load_pressure = loop_count >= 2 or tokens_before > max_input_tokens * 0.85

    if allow_model_switch and (load_pressure or simple_turn):
        cand = resolve_fallback_model(model, fallback_model)
        if cand and cand != model:
            recommended_model = cand
            model_switched = True
            decision = "SWITCH_MODEL"
            reasons.append(f"FinOps route {model} -> {recommended_model}")

    # 6. Anti-loop therapy injection
    therapy_patch = None
    if loop_count >= 1 or duplicates_removed > 0:
        therapy_patch = "[SOPHRA LOOP GUARD] Repeated tool calls detected. Do NOT repeat identical tool arguments; synthesize from existing results."
        sys_idx = next((i for i, m in enumerate(optimized) if isinstance(m, dict) and m.get("role") in ("system", "developer")), -1)
        if sys_idx >= 0:
            existing = _extract_text(optimized[sys_idx])
            if therapy_patch not in existing:
                optimized[sys_idx] = dict(optimized[sys_idx], content=(f"{existing}\n\n{therapy_patch}" if existing else therapy_patch))
        else:
            optimized.insert(0, {"role": "system", "content": therapy_patch})

    tokens_after = estimate_messages_tokens(optimized)
    tokens_saved = max(0, tokens_before - tokens_after)
    cost_after_1k = _input_cost_1k(recommended_model)
    savings_usd = max(0.0, round((tokens_before / 1000.0) * cost_before_1k - (tokens_after / 1000.0) * cost_after_1k, 6))

    return {
        "optimizer_version": OPTIMIZER_VERSION,
        "agent_id": agent_id,
        "decision": decision,
        "allow_execution": True,
        "reasons": reasons or ["Request optimal"],
        "model": recommended_model,
        "original_model": model,
        "recommended_model": recommended_model,
        "messages": optimized,
        "therapy_patch": therapy_patch,
        "optimization_stats": {
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_saved": tokens_saved,
            "reduction_pct": round((tokens_saved / tokens_before) * 100.0, 1) if tokens_before > 0 else 0.0,
            "duplicates_removed": duplicates_removed,
            "tool_outputs_pruned": tool_outputs_pruned,
            "middle_turns_compacted": middle_turns_compacted,
            "model_switched": model_switched,
            "loop_count": loop_count,
            "estimated_savings_usd": savings_usd,
        },
    }


class SophraOptimizer:
    """Universal active optimizer + telemetry client for any Python AI agent."""

    def __init__(
        self,
        agent_id: str = "python-agent",
        api_key: Optional[str] = None,
        base_url: str = "https://sophra.me",
        max_input_tokens: int = 12000,
        max_tool_output_chars: int = 2400,
        keep_recent_turns: int = 6,
        allow_model_switch: bool = True,
        smart_routing: bool = False,
        fallback_model: Optional[str] = None,
        timeout_seconds: float = 4.0,
    ) -> None:
        self.agent_id = agent_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_input_tokens = max_input_tokens
        self.max_tool_output_chars = max_tool_output_chars
        self.keep_recent_turns = keep_recent_turns
        self.allow_model_switch = allow_model_switch
        self.smart_routing = smart_routing
        self.fallback_model = fallback_model
        self.timeout_seconds = timeout_seconds

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-SDK-Version": OPTIMIZER_VERSION,
                "X-SDK-Lang": "python",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def optimize(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o",
        use_remote: bool = False,
    ) -> Dict[str, Any]:
        if use_remote and self.api_key:
            remote = self._post_json(
                "/api/optimize/request",
                {
                    "agent_id": self.agent_id,
                    "model": model,
                    "messages": messages,
                    "max_input_tokens": self.max_input_tokens,
                    "max_tool_output_chars": self.max_tool_output_chars,
                    "keep_recent_turns": self.keep_recent_turns,
                    "allow_model_switch": self.allow_model_switch,
                    "smart_routing": self.smart_routing,
                    "fallback_model": self.fallback_model,
                },
            )
            if remote and remote.get("success"):
                return remote
        return optimize_messages(
            messages,
            agent_id=self.agent_id,
            model=model,
            max_input_tokens=self.max_input_tokens,
            max_tool_output_chars=self.max_tool_output_chars,
            keep_recent_turns=self.keep_recent_turns,
            allow_model_switch=self.allow_model_switch,
            smart_routing=self.smart_routing,
            fallback_model=self.fallback_model,
        )

    def guarded_call(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        call_fn: Callable[[str, List[Dict[str, Any]]], Any],
        use_remote: bool = False,
        send_telemetry: bool = True,
    ) -> Dict[str, Any]:
        opt = self.optimize(messages, model=model, use_remote=use_remote)
        stats = opt["optimization_stats"]

        if not opt["allow_execution"]:
            if send_telemetry and self.api_key:
                self._post_json(
                    "/api/vitals",
                    {
                        "agent_id": self.agent_id,
                        "token_consumption": stats["tokens_before"],
                        "token_limit": self.max_input_tokens,
                        "loop_frequency": stats["loop_count"],
                        "hallucination_rate": 0,
                        "metadata": {"model": opt["model"], "decision": opt["decision"], "tokens_saved": stats["tokens_saved"]},
                    },
                )
            return {
                "halted": True,
                "response": {
                    "id": f"sophra-cb-{int(time.time() * 1000)}",
                    "object": "chat.completion",
                    "model": opt["model"],
                    "choices": [{"index": 0, "message": opt["halt_response"], "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                },
                "optimization": opt,
            }

        t0 = time.monotonic()
        response = call_fn(opt["model"], opt["messages"])
        latency_ms = round((time.monotonic() - t0) * 1000.0, 2)

        usage = {}
        if isinstance(response, dict):
            usage = response.get("usage") or {}
        elif hasattr(response, "usage") and response.usage is not None:
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", None) or getattr(response.usage, "input_tokens", None),
                "completion_tokens": getattr(response.usage, "completion_tokens", None) or getattr(response.usage, "output_tokens", None),
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }

        prompt_tok = usage.get("prompt_tokens") or stats["tokens_after"]
        comp_tok = usage.get("completion_tokens") or 0
        total_tok = usage.get("total_tokens") or (prompt_tok + comp_tok)

        if send_telemetry and self.api_key:
            self._post_json(
                "/api/vitals",
                {
                    "agent_id": self.agent_id,
                    "token_consumption": int(total_tok),
                    "token_limit": self.max_input_tokens,
                    "loop_frequency": stats["loop_count"],
                    "hallucination_rate": 0,
                    "metadata": {
                        "model": opt["model"],
                        "original_model": model,
                        "decision": opt["decision"],
                        "latency_ms": latency_ms,
                        "tokens_saved": stats["tokens_saved"],
                        "estimated_savings_usd": stats["estimated_savings_usd"],
                    },
                },
            )

        return {
            "halted": False,
            "latency_ms": latency_ms,
            "response": response,
            "optimization": opt,
        }


def wrap_openai(client: Any, *, agent_id: str = "openai-python-agent", **optimizer_kwargs: Any) -> Any:
    """1-line drop-in wrapper for the official Python OpenAI client.

    Usage:
        from openai import OpenAI
        from sophra_client import wrap_openai
        client = wrap_openai(OpenAI(), agent_id="my-agent", api_key="sk_live_...")
    """
    optimizer = SophraOptimizer(agent_id=agent_id, **optimizer_kwargs)
    orig_create = client.chat.completions.create

    def guarded_create(*args: Any, **kwargs: Any) -> Any:
        model = kwargs.get("model", "gpt-4o")
        messages = kwargs.get("messages", [])
        result = optimizer.guarded_call(
            model=model,
            messages=messages,
            call_fn=lambda opt_model, opt_msgs: orig_create(
                *args, **{**kwargs, "model": opt_model, "messages": opt_msgs}
            ),
        )
        return result["response"]

    client.chat.completions.create = guarded_create
    client.sophra_optimizer = optimizer
    return client
