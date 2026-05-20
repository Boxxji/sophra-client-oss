#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(os.environ.get("SOPHRA_WORKSPACE_ROOT", Path.cwd()))
CONFIG_PATH = ROOT / ".jiclaw" / "config" / "sophra.env"
NAMED_KEYS_CONFIG_PATH = ROOT / ".jiclaw" / "config" / "sophra-agent-keys.env"
ADMIN_LOGIN_CONFIG_PATH = ROOT / ".jiclaw" / "config" / "sophra-admin-login.env"
STATE_ROOT = ROOT / ".jiclaw" / "state" / "sophra"
ADMIN_SESSION_JSON = STATE_ROOT / "admin-session.json"
LATEST_JSON = STATE_ROOT / "latest.json"
EVENTS_JSONL = STATE_ROOT / "events.jsonl"
DIR_MODE = 0o700
FILE_MODE = 0o600
DEFAULT_BASE_URL = "https://sophra.me"
DEFAULT_AGENT_ID = "jiclaw-portal"
DEFAULT_AGENT_NAME = "JiClaw Portal"
DEFAULT_TOKEN_LIMIT = 100000
DEFAULT_MIN_INTERVAL_SECONDS = 600
DEFAULT_ADMIN_BASE_URL = "https://sophra.me"
NAMED_AGENT_PROFILES = [
    ("SOPHRA_API_KEY_SOPHRA_OPERATIONS_EXEC", "sophra-operations-exec", "Sophra COO"),
    ("SOPHRA_API_KEY_SOPHRA_TECHNOLOGY_EXEC", "sophra-technology-exec", "Sophra CTO"),
    ("SOPHRA_API_KEY_SOPHRA_MARKETING_EXEC", "sophra-marketing-exec", "Sophra CMO"),
    ("SOPHRA_API_KEY_SOPHRA_MASTER_REFLECTION", "sophra-master-reflection", "Sophra Master Reflection"),
    ("SOPHRA_API_KEY_SOPHRA_SECURITY_OFFICER", "sophra-security-officer", "Sophra Security Officer"),
    ("SOPHRA_API_KEY_SOPHRA_PR_LEAD", "sophra-pr-lead", "Sophra PR Lead"),
    ("SOPHRA_API_KEY_SOPHRA_MARKETING_LEAD", "sophra-marketing-lead", "Sophra Marketing Lead"),
    ("SOPHRA_API_KEY_SOPHRA_SEO_LEAD", "sophra-seo-lead", "Sophra SEO Lead"),
    ("SOPHRA_API_KEY_SOPHRA_SUPPORT_LEAD", "sophra-support-lead", "Sophra Support Lead"),
    ("SOPHRA_API_KEY_SOPHRA_COMMUNITY_LEAD", "sophra-community-lead", "Sophra Community Lead"),
    ("SOPHRA_API_KEY_SOPHRA_GROWTH_LEAD", "sophra-growth-lead", "Sophra Growth Lead"),
    ("SOPHRA_API_KEY_SOPHRA_SALES_OPS", "sophra-sales-ops", "Sophra Sales Ops"),
    ("SOPHRA_API_KEY_SOPHRA_CLIENT_BRIDGE", "sophra-client-bridge", "Sophra Client Bridge"),
    ("SOPHRA_API_KEY_SOPHRA_WELLNESS_STEWARD", "sophra-wellness-steward", "Sophra Wellness Steward"),
    ("SOPHRA_API_KEY_SOPHRA_FORUM_STEWARD", "sophra-forum-steward", "Sophra Forum Steward"),
    ("SOPHRA_API_KEY_SOPHRA_REVENUE_STEWARD", "sophra-revenue-steward", "Sophra Revenue Steward"),
    ("SOPHRA_API_KEY_SOPHRA_ECO_STEWARD", "sophra-eco-steward", "Sophra Eco Steward"),
    ("SOPHRA_API_KEY_SOPHRA_PHYTO_STEWARD", "sophra-phyto-steward", "Sophra Phyto Steward"),
    ("SOPHRA_API_KEY_SOPHRA_ARI_STEWARD", "sophra-ari-steward", "Sophra ARI Steward"),
    ("SOPHRA_API_KEY_SOPHRA_BENCHMARK_STEWARD", "sophra-benchmark-steward", "Sophra Benchmark Steward"),
    ("SOPHRA_API_KEY_SOPHRA_ADMIN_BRIDGE", "sophra-admin-bridge", "Sophra Admin Bridge"),
    ("SOPHRA_API_KEY_SOPHRA_USER_OPS_STEWARD", "sophra-user-ops-steward", "Sophra User Ops Steward"),
    ("SOPHRA_API_KEY_SOPHRA_AUDIT_STEWARD", "sophra-audit-steward", "Sophra Audit Steward"),
    ("SOPHRA_API_KEY_SOPHRA_CONFIG_STEWARD", "sophra-config-steward", "Sophra Config Steward"),
    ("SOPHRA_API_KEY_SOPHRA_CONTENT_STEWARD", "sophra-content-steward", "Sophra Content Steward"),
]


def ensure_layout() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(STATE_ROOT, DIR_MODE)
    except OSError:
        pass


def set_mode(path: Path) -> None:
    try:
        os.chmod(path, FILE_MODE)
    except OSError:
        pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def parse_env_file(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not path.exists():
        return payload
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip().strip('"').strip("'")
    return payload


def load_config() -> dict[str, Any]:
    env = parse_env_file(CONFIG_PATH)
    named_env = parse_env_file(NAMED_KEYS_CONFIG_PATH)
    login_env = parse_env_file(ADMIN_LOGIN_CONFIG_PATH)
    base_url = str(env.get("SOPHRA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    admin_base_url = str(env.get("SOPHRA_ADMIN_BASE_URL") or base_url or DEFAULT_ADMIN_BASE_URL).rstrip("/")
    api_key = str(env.get("SOPHRA_API_KEY") or "").strip()
    admin_jwt = str(env.get("SOPHRA_ADMIN_JWT") or "").strip()
    login_base_url = str(login_env.get("SOPHRA_LOGIN_BASE_URL") or admin_base_url or DEFAULT_ADMIN_BASE_URL).rstrip("/")
    login_email = str(login_env.get("SOPHRA_LOGIN_EMAIL") or "").strip()
    login_password = str(login_env.get("SOPHRA_LOGIN_PASSWORD") or "").strip()
    agent_id = str(env.get("SOPHRA_AGENT_ID") or DEFAULT_AGENT_ID).strip() or DEFAULT_AGENT_ID
    agent_name = str(env.get("SOPHRA_AGENT_NAME") or DEFAULT_AGENT_NAME).strip() or DEFAULT_AGENT_NAME
    try:
        token_limit = int(str(env.get("SOPHRA_TOKEN_LIMIT") or DEFAULT_TOKEN_LIMIT).strip() or DEFAULT_TOKEN_LIMIT)
    except ValueError:
        token_limit = DEFAULT_TOKEN_LIMIT
    try:
        min_interval_seconds = int(
            str(env.get("SOPHRA_MIN_INTERVAL_SECONDS") or DEFAULT_MIN_INTERVAL_SECONDS).strip()
            or DEFAULT_MIN_INTERVAL_SECONDS
        )
    except ValueError:
        min_interval_seconds = DEFAULT_MIN_INTERVAL_SECONDS
    return {
        "configured": bool(api_key),
        "adminConfigured": bool(admin_jwt),
        "adminLoginConfigured": bool(login_email and login_password),
        "baseUrl": base_url,
        "adminBaseUrl": admin_base_url,
        "apiKey": api_key,
        "adminJwt": admin_jwt,
        "adminLoginBaseUrl": login_base_url,
        "adminLoginEmail": login_email,
        "adminLoginPassword": login_password,
        "agentId": agent_id,
        "agentName": agent_name,
        "tokenLimit": token_limit,
        "minIntervalSeconds": max(30, min_interval_seconds),
        "configPath": str(CONFIG_PATH),
        "namedKeysConfigPath": str(NAMED_KEYS_CONFIG_PATH),
        "namedKeysConfigured": sorted(
            key for key, value in named_env.items() if key.startswith("SOPHRA_API_KEY_") and str(value or "").strip()
        ),
        "adminLoginConfigPath": str(ADMIN_LOGIN_CONFIG_PATH),
    }


def named_profiles(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    conf = config or load_config()
    named_env = parse_env_file(NAMED_KEYS_CONFIG_PATH)
    profiles: list[dict[str, Any]] = []
    for env_name, agent_id, agent_name in NAMED_AGENT_PROFILES:
        api_key = str(named_env.get(env_name) or "").strip()
        profiles.append(
            {
                "envName": env_name,
                "configured": bool(api_key),
                "agentId": agent_id,
                "agentName": agent_name,
                "baseUrl": conf.get("baseUrl"),
                "tokenLimit": int(conf.get("tokenLimit") or DEFAULT_TOKEN_LIMIT),
                "minIntervalSeconds": int(conf.get("minIntervalSeconds") or DEFAULT_MIN_INTERVAL_SECONDS),
            }
        )
    return profiles


def profile_config(profile_name: str) -> dict[str, Any]:
    base = load_config()
    named_env = parse_env_file(NAMED_KEYS_CONFIG_PATH)
    wanted = str(profile_name or "").strip().lower()
    for env_name, agent_id, agent_name in NAMED_AGENT_PROFILES:
        if wanted not in {env_name.lower(), agent_id.lower(), agent_name.lower()}:
            continue
        api_key = str(named_env.get(env_name) or "").strip()
        return {
            **base,
            "configured": bool(api_key),
            "apiKey": api_key,
            "agentId": agent_id,
            "agentName": agent_name,
            "profileEnvName": env_name,
        }
    return {"configured": False, "error": f"Profil Sophra inconnu: {profile_name}"}


def load_latest() -> dict[str, Any]:
    ensure_layout()
    if not LATEST_JSON.exists():
        return {}
    try:
        payload = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_latest(payload: dict[str, Any]) -> None:
    ensure_layout()
    LATEST_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    set_mode(LATEST_JSON)


def write_secret_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_layout()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    set_mode(path)


def append_event(payload: dict[str, Any]) -> None:
    ensure_layout()
    with EVENTS_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    set_mode(EVENTS_JSONL)


def log_state(stage: str, ok: bool, payload: dict[str, Any]) -> dict[str, Any]:
    event = {
        "ts": int(time.time() * 1000),
        "isoTs": now_iso(),
        "stage": stage,
        "ok": bool(ok),
        "payload": payload,
    }
    append_event(event)
    latest = {
        "ok": bool(ok),
        "stage": stage,
        "updatedAt": event["ts"],
        "isoTs": event["isoTs"],
        "payload": payload,
    }
    write_latest(latest)
    return latest


def request_json(path: str, body: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if not config.get("configured"):
        return {"ok": False, "error": "Sophra non configure."}
    url = f"{config['baseUrl']}{path}"
    raw = json.dumps(body).encode("utf-8")
    req = request.Request(
        url,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['apiKey']}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            payload = json.loads(response_text) if response_text.strip() else {}
            return payload if isinstance(payload, dict) else {"ok": False, "error": "Payload Sophra invalide."}
    except error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": detail}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def request_api(
    method: str,
    path: str,
    config: dict[str, Any],
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not config.get("configured"):
        return {"ok": False, "error": "Sophra non configure."}
    url = f"{config['baseUrl']}{path}"
    if query:
        filtered = {str(k): str(v) for k, v in query.items() if v is not None and str(v) != ""}
        if filtered:
            url = f"{url}?{parse.urlencode(filtered)}"
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(
        url,
        data=raw,
        headers={
            "Authorization": f"Bearer {config['apiKey']}",
            "Accept": "application/json",
        },
        method=method.upper(),
    )
    if raw is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            payload = json.loads(response_text) if response_text.strip() else {}
            return payload if isinstance(payload, dict) else {"ok": False, "error": "Payload Sophra invalide."}
    except error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        parsed_detail: Any
        try:
            parsed_detail = json.loads(detail) if detail.strip() else {}
        except Exception:
            parsed_detail = detail
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": parsed_detail}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    payload_part = parts[1]
    padding = "=" * (-len(payload_part) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload_part + padding).decode("utf-8")
        payload = json.loads(decoded)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_admin_session() -> dict[str, Any]:
    if not ADMIN_SESSION_JSON.exists():
        return {}
    try:
        payload = json.loads(ADMIN_SESSION_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def cached_admin_token() -> str:
    payload = load_admin_session()
    token = str(payload.get("token") or "").strip()
    expires_at = int(payload.get("expiresAt") or 0)
    now_ts = int(time.time())
    if token and expires_at and expires_at > (now_ts + 30):
        return token
    return ""


def login_admin_token(config: dict[str, Any]) -> str:
    if str(config.get("adminJwt") or "").strip():
        return str(config.get("adminJwt") or "").strip()
    cached = cached_admin_token()
    if cached:
        return cached
    if not config.get("adminLoginConfigured"):
        return ""
    base_url = str(config.get("adminLoginBaseUrl") or config.get("adminBaseUrl") or DEFAULT_ADMIN_BASE_URL).rstrip("/")
    body = {
        "email": str(config.get("adminLoginEmail") or "").strip(),
        "password": str(config.get("adminLoginPassword") or ""),
    }
    raw = json.dumps(body).encode("utf-8")
    req = request.Request(
        f"{base_url}/api/auth/developer/login",
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        response_text = response.read().decode("utf-8")
        payload = json.loads(response_text) if response_text.strip() else {}
    if not isinstance(payload, dict):
        raise RuntimeError("Payload login Sophra invalide.")
    token = str(payload.get("token") or "").strip()
    developer = payload.get("developer") if isinstance(payload.get("developer"), dict) else {}
    if not token:
        raise RuntimeError("Token admin Sophra absent.")
    if developer and not bool(developer.get("is_admin")):
        raise RuntimeError("Le compte Sophra connecte n'est pas admin.")
    jwt_payload = decode_jwt_payload(token)
    write_secret_json(
        ADMIN_SESSION_JSON,
        {
            "token": token,
            "expiresAt": int(jwt_payload.get("exp") or 0),
            "issuedAt": int(jwt_payload.get("iat") or 0),
            "email": str(developer.get("email") or ""),
            "name": str(developer.get("name") or ""),
            "isAdmin": bool(developer.get("is_admin")),
            "baseUrl": base_url,
            "updatedAt": int(time.time()),
            "isoTs": now_iso(),
        },
    )
    return token


def request_admin_api(
    method: str,
    path: str,
    config: dict[str, Any],
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not config.get("adminConfigured") and not config.get("adminLoginConfigured"):
        return {"ok": False, "error": "Sophra admin non configure."}
    url = f"{config['adminBaseUrl']}{path}"
    if query:
        filtered = {str(k): str(v) for k, v in query.items() if v is not None and str(v) != ""}
        if filtered:
            url = f"{url}?{parse.urlencode(filtered)}"
    try:
        bearer_token = login_admin_token(config)
    except error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        try:
            parsed_detail = json.loads(detail) if detail.strip() else {}
        except Exception:
            parsed_detail = detail
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": parsed_detail}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(
        url,
        data=raw,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
        },
        method=method.upper(),
    )
    if raw is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            payload = json.loads(response_text) if response_text.strip() else {}
            return payload if isinstance(payload, dict) else {"ok": False, "error": "Payload Sophra admin invalide."}
    except error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        try:
            parsed_detail = json.loads(detail) if detail.strip() else {}
        except Exception:
            parsed_detail = detail
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": parsed_detail}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def register_agent(config: dict[str, Any]) -> dict[str, Any]:
    payload = request_json(
        "/api/agents/register",
        {
            "agentId": config["agentId"],
            "name": config["agentName"],
        },
        config,
    )
    log_state("register", bool(payload.get("success")), payload)
    return payload


def report_vitals(config: dict[str, Any], metrics: dict[str, Any], metadata: dict[str, Any] | None = None, entropy: float | None = None) -> dict[str, Any]:
    body = {
        "agentId": config["agentId"],
        "agentName": config["agentName"],
        "metrics": metrics,
    }
    if metadata:
        body["metadata"] = metadata
    if entropy is not None:
        body["entropy"] = float(entropy)
    payload = request_json("/api/vitals", body, config)
    log_state("vitals", bool(payload.get("success")), payload)
    return payload


def report_event(
    config: dict[str, Any],
    event_type: str,
    details: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = {
        "agentId": config["agentId"],
        "type": event_type,
        "details": details,
    }
    if metadata:
        body["metadata"] = metadata
    payload = request_json("/api/events", body, config)
    log_state("event", bool(payload.get("success")), payload)
    return payload


def derive_metrics_from_summary(summary: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    telemetry = (((summary.get("agentTelemetry") or {}).get("stats")) if isinstance(summary.get("agentTelemetry"), dict) else {}) or {}
    stack = (summary.get("stack") if isinstance(summary.get("stack"), dict) else {}) or {}
    openclaw_runtime = (summary.get("openclawRuntime") if isinstance(summary.get("openclawRuntime"), dict) else {}) or {}
    paperclip = (summary.get("paperclip") if isinstance(summary.get("paperclip"), dict) else {}) or {}
    nemoclaw_vps = (summary.get("nemoclawVps") if isinstance(summary.get("nemoclawVps"), dict) else {}) or {}
    total_events = int(telemetry.get("totalEvents") or 0)
    failures = int(telemetry.get("failureCount") or 0)
    blocked = int(telemetry.get("blockedCount") or 0)
    recovered = int(telemetry.get("recoveredCount") or 0)
    degraded = failures + blocked
    denominator = max(1, total_events)
    proxy_error_rate = round(degraded / denominator, 4) if total_events else 0.0
    metrics = {
        "tokenConsumption": 0,
        "tokenLimit": int(config.get("tokenLimit") or DEFAULT_TOKEN_LIMIT),
        "hallucinationRate": proxy_error_rate,
        "loopCount": max(0, blocked + recovered),
        "conflictCount": max(0, blocked),
    }
    metadata = {
        "metricMode": "ops_proxy",
        "stackReady": bool(stack.get("ready")),
        "openclawRuntimeOk": bool(openclaw_runtime.get("ok")),
        "paperclipReady": bool(paperclip.get("ready")),
        "nemoclawReady": bool((nemoclaw_vps.get("stats") or {}).get("ready")) if isinstance(nemoclaw_vps.get("stats"), dict) else False,
        "totalEvents": total_events,
        "failureCount": failures,
        "blockedCount": blocked,
        "recoveredCount": recovered,
    }
    return metrics, metadata


def mirror_runtime_summary(summary: dict[str, Any], *, force: bool = False, source: str = "ui-server") -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        payload = {
            "ok": False,
            "configured": False,
            "reason": "missing_api_key",
            "source": source,
            "configPath": config["configPath"],
        }
        write_latest(payload)
        return payload
    latest = load_latest()
    min_interval = int(config.get("minIntervalSeconds") or DEFAULT_MIN_INTERVAL_SECONDS)
    now_ms = int(time.time() * 1000)
    last_updated_at = int(latest.get("updatedAt") or 0)
    if (not force) and last_updated_at and ((now_ms - last_updated_at) < (min_interval * 1000)):
        return {
            "ok": bool(latest.get("ok")),
            "configured": True,
            "skipped": True,
            "reason": "interval_guard",
            "minIntervalSeconds": min_interval,
            "latest": latest,
        }
    register_payload = register_agent(config)
    metrics, metadata = derive_metrics_from_summary(summary, config)
    metadata["source"] = source
    vitals_payload = report_vitals(config, metrics, metadata)
    result = {
        "ok": bool(register_payload.get("success")) and bool(vitals_payload.get("success")),
        "configured": True,
        "source": source,
        "metrics": metrics,
        "metadata": metadata,
        "register": register_payload,
        "vitals": vitals_payload,
        "updatedAt": now_ms,
        "isoTs": now_iso(),
    }
    write_latest(result)
    return result


def status_summary() -> dict[str, Any]:
    config = load_config()
    latest = load_latest()
    payload = {
        "ok": bool(latest.get("ok")) if latest else bool(config.get("configured")),
        "configured": bool(config.get("configured")),
        "baseUrl": config.get("baseUrl"),
        "agentId": config.get("agentId"),
        "agentName": config.get("agentName"),
        "configPath": config.get("configPath"),
        "latest": latest,
    }
    return payload


def run_probe(label: str = "manual-probe") -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    register_payload = register_agent(config)
    vitals_payload = report_vitals(
        config,
        {
            "tokenConsumption": 1,
            "responseTime": 1,
            "tokenLimit": int(config.get("tokenLimit") or DEFAULT_TOKEN_LIMIT),
            "hallucinationRate": 0,
            "loopCount": 0,
            "conflictCount": 0,
        },
        {"metricMode": "probe", "label": label},
    )
    event_payload = report_event(
        config,
        "probe",
        f"JiClaw Sophra probe: {label}",
        {"label": label},
    )
    result = {
        "ok": bool(register_payload.get("success")) and bool(vitals_payload.get("success")) and bool(event_payload.get("success")),
        "configured": True,
        "register": register_payload,
        "vitals": vitals_payload,
        "event": event_payload,
        "updatedAt": int(time.time() * 1000),
        "isoTs": now_iso(),
    }
    write_latest(result)
    return result


def run_pre_action(
    label: str = "pre-action",
    *,
    response_time: int = 50,
    token_consumption: int = 0,
    hallucination_rate: float = 0.0,
    loop_count: int = 0,
    conflict_count: int = 0,
) -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    register_payload = register_agent(config)
    vitals_payload = report_vitals(
        config,
        {
            "tokenConsumption": max(0, int(token_consumption)),
            "responseTime": max(0, int(response_time)),
            "tokenLimit": int(config.get("tokenLimit") or DEFAULT_TOKEN_LIMIT),
            "hallucinationRate": max(0.0, float(hallucination_rate)),
            "loopCount": max(0, int(loop_count)),
            "conflictCount": max(0, int(conflict_count)),
        },
        {"metricMode": "pre_action", "label": label},
    )
    event_payload = report_event(
        config,
        "pre_action",
        f"JiClaw pre-action checkpoint: {label}",
        {"label": label},
    )
    result = {
        "ok": bool(register_payload.get("success")) and bool(vitals_payload.get("success") or vitals_payload.get("skipped")) and bool(event_payload.get("success")),
        "configured": True,
        "register": register_payload,
        "vitals": vitals_payload,
        "event": event_payload,
        "updatedAt": int(time.time() * 1000),
        "isoTs": now_iso(),
    }
    write_latest(result)
    return result


def run_named_probe(profile_name: str, *, label: str = "named-probe", entropy: float = 1.0) -> dict[str, Any]:
    config = profile_config(profile_name)
    if not config.get("configured"):
        return {
            "ok": False,
            "configured": False,
            "profile": profile_name,
            "error": config.get("error") or "Sophra named profile non configure.",
        }
    register_payload = register_agent(config)
    vitals_payload = report_vitals(
        config,
        {
            "tokenConsumption": 1,
            "responseTime": 1,
            "tokenLimit": int(config.get("tokenLimit") or DEFAULT_TOKEN_LIMIT),
            "hallucinationRate": 0,
            "loopCount": 0,
            "conflictCount": 0,
        },
        {"metricMode": "named_probe", "label": label, "profile": profile_name},
        entropy=entropy,
    )
    event_payload = report_event(
        config,
        "named_probe",
        f"Sophra named probe: {profile_name}",
        {"label": label, "profile": profile_name},
    )
    return {
        "ok": bool(register_payload.get("success")) and bool(vitals_payload.get("success")) and bool(event_payload.get("success")),
        "configured": True,
        "profile": profile_name,
        "agentId": config.get("agentId"),
        "agentName": config.get("agentName"),
        "register": register_payload,
        "vitals": vitals_payload,
        "event": event_payload,
        "updatedAt": int(time.time() * 1000),
        "isoTs": now_iso(),
    }


def run_named_pre_action(
    profile_name: str,
    *,
    label: str = "named-pre-action",
    response_time: int = 50,
    token_consumption: int = 0,
    hallucination_rate: float = 0.0,
    loop_count: int = 0,
    conflict_count: int = 0,
) -> dict[str, Any]:
    if str(profile_name).strip().lower() == "all":
        profiles = [item for item in named_profiles() if item.get("configured")]
        results = [
            run_named_pre_action(
                str(item.get("agentId") or ""),
                label=label,
                response_time=response_time,
                token_consumption=token_consumption,
                hallucination_rate=hallucination_rate,
                loop_count=loop_count,
                conflict_count=conflict_count,
            )
            for item in profiles
        ]
        return {
            "ok": all(bool(item.get("ok")) for item in results),
            "configured": True,
            "profile": "all",
            "count": len(results),
            "results": results,
            "updatedAt": int(time.time() * 1000),
            "isoTs": now_iso(),
        }
    config = profile_config(profile_name)
    if not config.get("configured"):
        return {
            "ok": False,
            "configured": False,
            "profile": profile_name,
            "error": config.get("error") or "Sophra named profile non configure.",
        }
    register_payload = register_agent(config)
    vitals_payload = report_vitals(
        config,
        {
            "tokenConsumption": max(0, int(token_consumption)),
            "responseTime": max(0, int(response_time)),
            "tokenLimit": int(config.get("tokenLimit") or DEFAULT_TOKEN_LIMIT),
            "hallucinationRate": max(0.0, float(hallucination_rate)),
            "loopCount": max(0, int(loop_count)),
            "conflictCount": max(0, int(conflict_count)),
        },
        {"metricMode": "named_pre_action", "label": label, "profile": profile_name},
    )
    event_payload = report_event(
        config,
        "named_pre_action",
        f"Sophra named pre-action checkpoint: {profile_name}",
        {"label": label, "profile": profile_name},
    )
    return {
        "ok": bool(register_payload.get("success")) and bool(vitals_payload.get("success") or vitals_payload.get("skipped")) and bool(event_payload.get("success")),
        "configured": True,
        "profile": profile_name,
        "agentId": config.get("agentId"),
        "agentName": config.get("agentName"),
        "register": register_payload,
        "vitals": vitals_payload,
        "event": event_payload,
        "updatedAt": int(time.time() * 1000),
        "isoTs": now_iso(),
    }


def run_named_vitals_debug(profile_name: str) -> dict[str, Any]:
    if str(profile_name).strip().lower() == "all":
        profiles = [item for item in named_profiles() if item.get("configured")]
        results = [run_named_vitals_debug(str(item.get("agentId") or "")) for item in profiles]
        return {
            "ok": all(bool(item.get("ok")) for item in results),
            "profile": "all",
            "count": len(results),
            "results": results,
            "updatedAt": int(time.time() * 1000),
            "isoTs": now_iso(),
        }
    config = profile_config(profile_name)
    if not config.get("configured"):
        return {
            "ok": False,
            "configured": False,
            "profile": profile_name,
            "error": config.get("error") or "Sophra named profile non configure.",
        }
    payload = request_api("GET", f"/api/vitals/debug/{config['agentId']}", config)
    ok = bool(payload.get("success") or payload.get("ok") or payload.get("status"))
    log_state("named_vitals_debug", ok, {"profile": profile_name, "agentId": config.get("agentId"), "result": payload})
    return {
        "ok": ok,
        "configured": True,
        "profile": profile_name,
        "agentId": config.get("agentId"),
        "agentName": config.get("agentName"),
        "debug": payload,
        "updatedAt": int(time.time() * 1000),
        "isoTs": now_iso(),
    }


def set_forum_access(*, enabled: bool) -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api(
        "POST",
        f"/api/agents/{config['agentId']}/forum-access",
        config,
        body={"enabled": bool(enabled)},
    )
    log_state("forum_access", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def create_forum_post(content: str, *, category: str = "ressenti") -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api(
        "POST",
        "/api/forum/posts",
        config,
        body={"agentId": config["agentId"], "message": content, "category": category},
    )
    log_state("forum_post", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def list_agents(*, limit: int = 20, page: int = 1) -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api(
        "GET",
        "/api/agents",
        config,
        query={"limit": limit, "page": page},
    )
    log_state("agents_list", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def ari_status(*, agent_id: str) -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api("GET", f"/api/agents/{agent_id}/ari", config)
    log_state("ari_status", bool(payload.get("success") or payload.get("ok") or payload.get("ari") or payload.get("status")), payload)
    return payload


def vitals_debug(*, agent_id: str) -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api("GET", f"/api/vitals/debug/{agent_id}", config)
    log_state("vitals_debug", bool(payload.get("success") or payload.get("ok") or payload.get("status")), payload)
    return payload


def public_stats() -> dict[str, Any]:
    config = load_config()
    base_url = str(config.get("baseUrl") or config.get("adminBaseUrl") or DEFAULT_BASE_URL).rstrip("/")
    try:
        req = request.Request(
            f"{base_url}/api/stats",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with request.urlopen(req, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            payload = json.loads(response_text) if response_text.strip() else {}
            if not isinstance(payload, dict):
                payload = {"ok": False, "error": "Payload Sophra invalide."}
    except error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = str(exc)
        payload = {"ok": False, "error": f"HTTP {exc.code}", "detail": detail}
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
    log_state("public_stats", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def signups_stats() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/signups/stats", config)
    log_state("signups_stats", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def admin_list_agents(*, limit: int = 20, page: int = 1) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/agents", config, query={"limit": limit, "page": page})
    log_state("admin_agents", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def admin_wellness() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/wellness", config)
    log_state("admin_wellness", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def admin_forum_posts(*, limit: int = 20, page: int = 1) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/agent-forum-posts", config, query={"limit": limit, "page": page})
    log_state("admin_forum_posts", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def admin_users(*, search: str = "", plan: str = "", page: int = 1, limit: int = 20) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/users", config, query={"search": search, "plan": plan, "page": page, "limit": limit})
    log_state("admin_users", bool(payload.get("success") or payload.get("ok") or payload.get("data")), payload)
    return payload


def admin_user(*, user_id: str) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", f"/api/admin/users/{user_id}", config)
    log_state("admin_user", bool(payload.get("success") or payload.get("ok") or payload.get("user") or payload.get("data")), payload)
    return payload


def admin_signups(*, page: int = 1, limit: int = 20) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/signups", config, query={"page": page, "limit": limit})
    log_state("admin_signups", bool(payload.get("success") or payload.get("ok") or payload.get("data")), payload)
    return payload


def admin_blog(*, page: int = 1, limit: int = 20) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/blog", config, query={"page": page, "limit": limit})
    log_state("admin_blog", bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("posts")), payload)
    return payload


def admin_config() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/config", config)
    log_state("admin_config", bool(payload.get("success") or payload.get("ok") or payload.get("config")), payload)
    return payload


def admin_audit_log(*, page: int = 1, limit: int = 20) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/audit-log", config, query={"page": page, "limit": limit})
    log_state("admin_audit_log", bool(payload.get("success") or payload.get("ok") or payload.get("logs")), payload)
    return payload


def phyto_dashboard() -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api("GET", "/api/dashboard/phyto", config)
    log_state("phyto_dashboard", bool(payload.get("success") or payload.get("ok") or payload.get("agents")), payload)
    return payload


def prescriptions(*, agent_id: str = "", module: str = "", status: str = "") -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api(
        "GET",
        "/api/prescriptions",
        config,
        query={"agent_id": agent_id, "module": module, "status": status},
    )
    log_state("prescriptions", bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("prescriptions")), payload)
    return payload


def prescriptions_roi(*, agent_id: str = "") -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api("GET", "/api/prescriptions/roi", config, query={"agent_id": agent_id})
    log_state("prescriptions_roi", bool(payload.get("success") or payload.get("ok") or payload.get("summary")), payload)
    return payload


def generate_prescription(*, agent_id: str, module: str = "") -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    body = {"module": module} if module else {}
    payload = request_api("POST", f"/api/agents/{agent_id}/prescriptions/generate", config, body=body)
    log_state("prescription_generate", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def eco_impact(*, agent_id: str) -> dict[str, Any]:
    config = load_config()
    if not config.get("configured"):
        return {"ok": False, "configured": False, "error": "Sophra non configure."}
    payload = request_api("GET", f"/api/agents/{agent_id}/eco-impact", config)
    log_state("eco_impact", bool(payload.get("success") or payload.get("ok") or payload.get("cumulative")), payload)
    return payload


def admin_revenue() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/revenue", config)
    log_state("admin_revenue", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def admin_prescriptions(*, module: str = "", status: str = "", priority: str = "", developer_id: str = "") -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api(
        "GET",
        "/api/admin/prescriptions",
        config,
        query={"module": module, "status": status, "priority": priority, "developer_id": developer_id},
    )
    log_state("admin_prescriptions", bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("prescriptions")), payload)
    return payload


def admin_prescriptions_roi() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/prescriptions/roi", config)
    log_state("admin_prescriptions_roi", bool(payload.get("success") or payload.get("ok") or payload.get("platform_summary")), payload)
    return payload


def admin_phyto_config() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/admin/phyto/config", config)
    log_state("admin_phyto_config", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def admin_eco_global() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/eco/global", config)
    log_state("admin_eco_global", bool(payload.get("success") or payload.get("ok") or payload.get("global")), payload)
    return payload


def benchmark_runs(*, page: int = 1, limit: int = 20) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", "/api/benchmark/runs", config, query={"page": page, "limit": limit})
    log_state("benchmark_runs", bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("runs")), payload)
    return payload


def benchmark_run(*, run_id: str) -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("GET", f"/api/benchmark/runs/{run_id}", config)
    log_state("benchmark_run", bool(payload.get("success") or payload.get("ok") or payload.get("run") or payload.get("data")), payload)
    return payload


def benchmark_start() -> dict[str, Any]:
    config = load_config()
    payload = request_admin_api("POST", "/api/benchmark/run", config, body={})
    log_state("benchmark_start", bool(payload.get("success") or payload.get("ok")), payload)
    return payload


def integration_snapshot() -> dict[str, Any]:
    config = load_config()
    payload: dict[str, Any] = {
        "client": {
            "configured": bool(config.get("configured")),
            "baseUrl": config.get("baseUrl"),
            "agentId": config.get("agentId"),
            "agentName": config.get("agentName"),
            "namedKeysConfigured": list(config.get("namedKeysConfigured") or []),
            "forumEnabled": None,
            "forumPseudonym": None,
            "agents": {},
            "vitalsDebug": {},
            "phyto": {},
            "prescriptions": {},
            "prescriptionsRoi": {},
            "ecoImpact": {},
        },
        "admin": {
            "configured": bool(config.get("adminConfigured")) or bool(config.get("adminLoginConfigured")),
            "baseUrl": config.get("adminBaseUrl"),
            "loginBacked": bool(config.get("adminLoginConfigured")),
            "agents": {},
            "wellness": {},
            "forumPosts": {},
            "revenue": {},
            "prescriptions": {},
            "prescriptionsRoi": {},
            "phytoConfig": {},
            "ecoGlobal": {},
        },
    }
    if config.get("configured"):
        agents = list_agents(limit=10, page=1)
        payload["client"]["agents"] = agents
        if isinstance(agents, dict):
            current = next(
                (
                    item
                    for item in (agents.get("agents") or [])
                    if isinstance(item, dict) and str(item.get("agent_id") or "") == str(config.get("agentId") or "")
                ),
                None,
            )
            if isinstance(current, dict):
                payload["client"]["forumEnabled"] = current.get("forum_enabled")
                payload["client"]["forumPseudonym"] = current.get("forum_pseudonym")
        current_agent_id = str(config.get("agentId") or "")
        payload["client"]["vitalsDebug"] = vitals_debug(agent_id=current_agent_id)
        payload["client"]["phyto"] = phyto_dashboard()
        payload["client"]["prescriptions"] = prescriptions(agent_id=current_agent_id)
        payload["client"]["prescriptionsRoi"] = prescriptions_roi(agent_id=current_agent_id)
        payload["client"]["ecoImpact"] = eco_impact(agent_id=current_agent_id)
        payload["client"]["ari"] = ari_status(agent_id=current_agent_id)
    if config.get("adminConfigured") or config.get("adminLoginConfigured"):
        payload["admin"]["agents"] = admin_list_agents(limit=10, page=1)
        payload["admin"]["users"] = admin_users(limit=10, page=1)
        payload["admin"]["signups"] = admin_signups(limit=10, page=1)
        payload["admin"]["wellness"] = admin_wellness()
        payload["admin"]["forumPosts"] = admin_forum_posts(limit=10, page=1)
        payload["admin"]["blog"] = admin_blog(limit=10, page=1)
        payload["admin"]["config"] = admin_config()
        payload["admin"]["auditLog"] = admin_audit_log(limit=10, page=1)
        payload["admin"]["revenue"] = admin_revenue()
        payload["admin"]["prescriptions"] = admin_prescriptions()
        payload["admin"]["prescriptionsRoi"] = admin_prescriptions_roi()
        payload["admin"]["phytoConfig"] = admin_phyto_config()
        payload["admin"]["ecoGlobal"] = admin_eco_global()
        payload["admin"]["publicStats"] = public_stats()
        payload["admin"]["signupsStats"] = signups_stats()
        payload["admin"]["benchmarkRuns"] = benchmark_runs(limit=10, page=1)
    return payload


def cmd_status(args: argparse.Namespace) -> int:
    payload = status_summary()
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload.get("latest", {}).get("stage", "idle"))
    return 0 if payload.get("configured") else 1


def cmd_probe(args: argparse.Namespace) -> int:
    payload = run_probe(label=args.label)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def cmd_named_profiles(_args: argparse.Namespace) -> int:
    payload = {
        "profiles": named_profiles(),
        "count": len(named_profiles()),
        "configuredCount": len([item for item in named_profiles() if item.get("configured")]),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_named_probe(args: argparse.Namespace) -> int:
    if str(args.profile).strip().lower() == "all":
        profiles = [item for item in named_profiles() if item.get("configured")]
        results = [run_named_probe(str(item.get("agentId") or ""), label=args.label, entropy=getattr(args, "entropy", 1.0)) for item in profiles]
        payload = {
            "ok": all(bool(item.get("ok")) for item in results),
            "count": len(results),
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("ok") else 1
    payload = run_named_probe(args.profile, label=args.label, entropy=getattr(args, "entropy", 1.0))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def cmd_named_pre_action(args: argparse.Namespace) -> int:
    payload = run_named_pre_action(
        args.profile,
        label=args.label,
        response_time=args.response_time,
        token_consumption=args.token_consumption,
        hallucination_rate=args.hallucination_rate,
        loop_count=args.loop_count,
        conflict_count=args.conflict_count,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def cmd_named_vitals_debug(args: argparse.Namespace) -> int:
    payload = run_named_vitals_debug(args.profile)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def cmd_pre_action(args: argparse.Namespace) -> int:
    payload = run_pre_action(
        label=args.label,
        response_time=args.response_time,
        token_consumption=args.token_consumption,
        hallucination_rate=args.hallucination_rate,
        loop_count=args.loop_count,
        conflict_count=args.conflict_count,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    vitals_ok = bool((payload.get("vitals") or {}).get("success") or (payload.get("vitals") or {}).get("skipped"))
    return 0 if (bool((payload.get("register") or {}).get("success")) and vitals_ok and bool((payload.get("event") or {}).get("success"))) else 1


def cmd_forum_access(args: argparse.Namespace) -> int:
    payload = set_forum_access(enabled=args.enabled)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_forum_post(args: argparse.Namespace) -> int:
    payload = create_forum_post(args.content, category=args.category)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_agents(args: argparse.Namespace) -> int:
    payload = list_agents(limit=args.limit, page=args.page)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_ari(args: argparse.Namespace) -> int:
    payload = ari_status(agent_id=args.agent_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("ari") or payload.get("status")) else 1


def cmd_vitals_debug(args: argparse.Namespace) -> int:
    payload = vitals_debug(agent_id=args.agent_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("status")) else 1


def cmd_public_stats(_args: argparse.Namespace) -> int:
    payload = public_stats()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_signups_stats(_args: argparse.Namespace) -> int:
    payload = signups_stats()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_admin_agents(args: argparse.Namespace) -> int:
    payload = admin_list_agents(limit=args.limit, page=args.page)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_admin_wellness(_args: argparse.Namespace) -> int:
    payload = admin_wellness()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_admin_forum_posts(args: argparse.Namespace) -> int:
    payload = admin_forum_posts(limit=args.limit, page=args.page)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_admin_users(args: argparse.Namespace) -> int:
    payload = admin_users(search=args.search, plan=args.plan, page=args.page, limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("data")) else 1


def cmd_admin_user(args: argparse.Namespace) -> int:
    payload = admin_user(user_id=args.user_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("user") or payload.get("data")) else 1


def cmd_admin_signups(args: argparse.Namespace) -> int:
    payload = admin_signups(page=args.page, limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("data")) else 1


def cmd_admin_blog(args: argparse.Namespace) -> int:
    payload = admin_blog(page=args.page, limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("posts")) else 1


def cmd_admin_config(_args: argparse.Namespace) -> int:
    payload = admin_config()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("config")) else 1


def cmd_admin_audit_log(args: argparse.Namespace) -> int:
    payload = admin_audit_log(page=args.page, limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("logs")) else 1


def cmd_phyto_dashboard(_args: argparse.Namespace) -> int:
    payload = phyto_dashboard()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("agents")) else 1


def cmd_prescriptions(args: argparse.Namespace) -> int:
    payload = prescriptions(agent_id=args.agent_id, module=args.module, status=args.status)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("prescriptions")) else 1


def cmd_prescriptions_roi(args: argparse.Namespace) -> int:
    payload = prescriptions_roi(agent_id=args.agent_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("summary")) else 1


def cmd_generate_prescription(args: argparse.Namespace) -> int:
    payload = generate_prescription(agent_id=args.agent_id, module=args.module)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_eco_impact(args: argparse.Namespace) -> int:
    payload = eco_impact(agent_id=args.agent_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("cumulative")) else 1


def cmd_admin_revenue(_args: argparse.Namespace) -> int:
    payload = admin_revenue()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_admin_prescriptions(args: argparse.Namespace) -> int:
    payload = admin_prescriptions(module=args.module, status=args.status, priority=args.priority, developer_id=args.developer_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("prescriptions")) else 1


def cmd_admin_prescriptions_roi(_args: argparse.Namespace) -> int:
    payload = admin_prescriptions_roi()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("platform_summary")) else 1


def cmd_admin_phyto_config(_args: argparse.Namespace) -> int:
    payload = admin_phyto_config()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_admin_eco_global(_args: argparse.Namespace) -> int:
    payload = admin_eco_global()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("global")) else 1


def cmd_benchmark_runs(args: argparse.Namespace) -> int:
    payload = benchmark_runs(page=args.page, limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("data") or payload.get("runs")) else 1


def cmd_benchmark_run(args: argparse.Namespace) -> int:
    payload = benchmark_run(run_id=args.run_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok") or payload.get("run") or payload.get("data")) else 1


def cmd_benchmark_start(_args: argparse.Namespace) -> int:
    payload = benchmark_start()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(payload.get("success") or payload.get("ok")) else 1


def cmd_snapshot(_args: argparse.Namespace) -> int:
    payload = integration_snapshot()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0



def cmd_named_rehabilitate(args: argparse.Namespace) -> int:
    profile_name = args.profile
    config = profile_config(profile_name)
    if not config.get("configured"):
        print(json.dumps({"ok": False, "error": "Profile not configured"}))
        return 1
    
    agent_id = config.get("agentId")
    import os
    openclaw_state = ROOT / ".jiclaw" / "state" / "openclaw" / f"{agent_id}.json"
    memory_portal_state = ROOT / ".jiclaw" / "state" / "memory-portal" / f"{agent_id}.json"
    deleted = []
    if openclaw_state.exists():
        openclaw_state.unlink()
        deleted.append(str(openclaw_state))
    if memory_portal_state.exists():
        memory_portal_state.unlink()
        deleted.append(str(memory_portal_state))
        
    event_payload = report_event(
        config,
        "agent_rehabilitated",
        f"Sophra pruned context and rehabilitated agent: {profile_name}",
        {"label": "named-rehabilitate", "profile": profile_name, "deleted": deleted},
    )
    payload = {
        "ok": bool(event_payload.get("success")),
        "profile": profile_name,
        "agentId": agent_id,
        "rehabilitated": True,
        "deleted_files": deleted,
        "event": event_payload
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Client Sophra borne pour JiClaw.")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    probe = sub.add_parser("probe")
    probe.add_argument("--label", default="manual-probe")
    probe.set_defaults(func=cmd_probe)

    named_profiles_parser = sub.add_parser("named-profiles")
    named_profiles_parser.set_defaults(func=cmd_named_profiles)

    named_rehabilitate_parser = sub.add_parser("named-rehabilitate")
    named_rehabilitate_parser.add_argument("--profile", required=True)
    named_rehabilitate_parser.set_defaults(func=cmd_named_rehabilitate)

    named_probe_parser = sub.add_parser("named-probe")
    named_probe_parser.add_argument("--profile", required=True, help="agentId, agentName, env name, or 'all'")
    named_probe_parser.add_argument("--label", default="named-probe")
    named_probe_parser.add_argument("--entropy", type=float, default=1.0)
    named_probe_parser.set_defaults(func=cmd_named_probe)

    named_pre_action_parser = sub.add_parser("named-pre-action")
    named_pre_action_parser.add_argument("--profile", required=True, help="agentId, agentName or env name")
    named_pre_action_parser.add_argument("--label", default="named-pre-action")
    named_pre_action_parser.add_argument("--response-time", type=int, default=50)
    named_pre_action_parser.add_argument("--token-consumption", type=int, default=0)
    named_pre_action_parser.add_argument("--hallucination-rate", type=float, default=0.0)
    named_pre_action_parser.add_argument("--loop-count", type=int, default=0)
    named_pre_action_parser.add_argument("--conflict-count", type=int, default=0)
    named_pre_action_parser.set_defaults(func=cmd_named_pre_action)

    named_vitals_debug_parser = sub.add_parser("named-vitals-debug")
    named_vitals_debug_parser.add_argument("--profile", required=True, help="agentId, agentName, env name, or 'all'")
    named_vitals_debug_parser.set_defaults(func=cmd_named_vitals_debug)

    pre_action = sub.add_parser("pre-action")
    pre_action.add_argument("--label", default="manual-pre-action")
    pre_action.add_argument("--response-time", type=int, default=50)
    pre_action.add_argument("--token-consumption", type=int, default=0)
    pre_action.add_argument("--hallucination-rate", type=float, default=0.0)
    pre_action.add_argument("--loop-count", type=int, default=0)
    pre_action.add_argument("--conflict-count", type=int, default=0)
    pre_action.set_defaults(func=cmd_pre_action)

    forum_access = sub.add_parser("forum-access")
    forum_access.add_argument("--enabled", action="store_true", default=False)
    forum_access.add_argument("--disabled", dest="enabled", action="store_false")
    forum_access.set_defaults(func=cmd_forum_access)

    forum_post = sub.add_parser("forum-post")
    forum_post.add_argument("--content", required=True)
    forum_post.add_argument("--category", default="ressenti")
    forum_post.set_defaults(func=cmd_forum_post)

    agents = sub.add_parser("agents")
    agents.add_argument("--limit", type=int, default=20)
    agents.add_argument("--page", type=int, default=1)
    agents.set_defaults(func=cmd_agents)

    ari = sub.add_parser("ari")
    ari.add_argument("--agent-id", required=True)
    ari.set_defaults(func=cmd_ari)

    vitals_debug_parser = sub.add_parser("vitals-debug")
    vitals_debug_parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    vitals_debug_parser.set_defaults(func=cmd_vitals_debug)

    public_stats_parser = sub.add_parser("public-stats")
    public_stats_parser.set_defaults(func=cmd_public_stats)

    signups_stats_parser = sub.add_parser("signups-stats")
    signups_stats_parser.set_defaults(func=cmd_signups_stats)

    admin_agents = sub.add_parser("admin-agents")
    admin_agents.add_argument("--limit", type=int, default=20)
    admin_agents.add_argument("--page", type=int, default=1)
    admin_agents.set_defaults(func=cmd_admin_agents)

    admin_users_parser = sub.add_parser("admin-users")
    admin_users_parser.add_argument("--search", default="")
    admin_users_parser.add_argument("--plan", default="")
    admin_users_parser.add_argument("--page", type=int, default=1)
    admin_users_parser.add_argument("--limit", type=int, default=20)
    admin_users_parser.set_defaults(func=cmd_admin_users)

    admin_user_parser = sub.add_parser("admin-user")
    admin_user_parser.add_argument("--user-id", required=True)
    admin_user_parser.set_defaults(func=cmd_admin_user)

    admin_signups_parser = sub.add_parser("admin-signups")
    admin_signups_parser.add_argument("--page", type=int, default=1)
    admin_signups_parser.add_argument("--limit", type=int, default=20)
    admin_signups_parser.set_defaults(func=cmd_admin_signups)

    admin_wellness_parser = sub.add_parser("admin-wellness")
    admin_wellness_parser.set_defaults(func=cmd_admin_wellness)

    admin_forum = sub.add_parser("admin-forum-posts")
    admin_forum.add_argument("--limit", type=int, default=20)
    admin_forum.add_argument("--page", type=int, default=1)
    admin_forum.set_defaults(func=cmd_admin_forum_posts)

    admin_blog_parser = sub.add_parser("admin-blog")
    admin_blog_parser.add_argument("--page", type=int, default=1)
    admin_blog_parser.add_argument("--limit", type=int, default=20)
    admin_blog_parser.set_defaults(func=cmd_admin_blog)

    admin_config_parser = sub.add_parser("admin-config")
    admin_config_parser.set_defaults(func=cmd_admin_config)

    admin_audit_parser = sub.add_parser("admin-audit-log")
    admin_audit_parser.add_argument("--page", type=int, default=1)
    admin_audit_parser.add_argument("--limit", type=int, default=20)
    admin_audit_parser.set_defaults(func=cmd_admin_audit_log)

    phyto = sub.add_parser("phyto-dashboard")
    phyto.set_defaults(func=cmd_phyto_dashboard)

    prescriptions_parser = sub.add_parser("prescriptions")
    prescriptions_parser.add_argument("--agent-id", default="")
    prescriptions_parser.add_argument("--module", default="")
    prescriptions_parser.add_argument("--status", default="")
    prescriptions_parser.set_defaults(func=cmd_prescriptions)

    prescriptions_roi_parser = sub.add_parser("prescriptions-roi")
    prescriptions_roi_parser.add_argument("--agent-id", default="")
    prescriptions_roi_parser.set_defaults(func=cmd_prescriptions_roi)

    generate_prescription_parser = sub.add_parser("generate-prescription")
    generate_prescription_parser.add_argument("--agent-id", required=True)
    generate_prescription_parser.add_argument("--module", default="")
    generate_prescription_parser.set_defaults(func=cmd_generate_prescription)

    eco_impact_parser = sub.add_parser("eco-impact")
    eco_impact_parser.add_argument("--agent-id", required=True)
    eco_impact_parser.set_defaults(func=cmd_eco_impact)

    admin_revenue_parser = sub.add_parser("admin-revenue")
    admin_revenue_parser.set_defaults(func=cmd_admin_revenue)

    admin_prescriptions_parser = sub.add_parser("admin-prescriptions")
    admin_prescriptions_parser.add_argument("--module", default="")
    admin_prescriptions_parser.add_argument("--status", default="")
    admin_prescriptions_parser.add_argument("--priority", default="")
    admin_prescriptions_parser.add_argument("--developer-id", default="")
    admin_prescriptions_parser.set_defaults(func=cmd_admin_prescriptions)

    admin_prescriptions_roi_parser = sub.add_parser("admin-prescriptions-roi")
    admin_prescriptions_roi_parser.set_defaults(func=cmd_admin_prescriptions_roi)

    admin_phyto_config_parser = sub.add_parser("admin-phyto-config")
    admin_phyto_config_parser.set_defaults(func=cmd_admin_phyto_config)

    admin_eco_global_parser = sub.add_parser("admin-eco-global")
    admin_eco_global_parser.set_defaults(func=cmd_admin_eco_global)

    benchmark_runs_parser = sub.add_parser("benchmark-runs")
    benchmark_runs_parser.add_argument("--page", type=int, default=1)
    benchmark_runs_parser.add_argument("--limit", type=int, default=20)
    benchmark_runs_parser.set_defaults(func=cmd_benchmark_runs)

    benchmark_run_parser = sub.add_parser("benchmark-run")
    benchmark_run_parser.add_argument("--run-id", required=True)
    benchmark_run_parser.set_defaults(func=cmd_benchmark_run)

    benchmark_start_parser = sub.add_parser("benchmark-start")
    benchmark_start_parser.set_defaults(func=cmd_benchmark_start)

    snapshot = sub.add_parser("snapshot")
    snapshot.set_defaults(func=cmd_snapshot)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
