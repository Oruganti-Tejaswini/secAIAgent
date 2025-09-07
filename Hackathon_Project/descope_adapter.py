import os
import json
import logging
from typing import Optional, Dict, Any

import requests

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

DESCOPE_API = "https://api.descope.com"
PROJECT_ID = os.getenv("DESCOPE_PROJECT_ID", "").strip()
MGMT_KEY   = os.getenv("DESCOPE_AUTH_MANAGEMENT_KEY", "").strip()

APP_IDS: Dict[str, str] = {
    "slack": "slack",
    "notion": "notion",
    "github": "github",
    "gcal": "google-calendar",
    "google-calendar": "google-calendar",
}

def _headers() -> Dict[str, str]:
    return {
        "x-descope-project-id": PROJECT_ID,
        "Authorization": f"Bearer {MGMT_KEY}",
        "Content-Type": "application/json",
    }

def healthcheck() -> Dict[str, Any]:
    ok = bool(PROJECT_ID and MGMT_KEY)
    return {"ok": ok, "project": PROJECT_ID[:6]+"…" if PROJECT_ID else None}

def start_connect(provider: str, login_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    app_id = APP_IDS.get(provider)
    if not app_id:
        return {"ok": False, "error": f"Unknown provider '{provider}'"}

    url = f"{DESCOPE_API}/v1/outbound/oauth/connect/start"
    payload = {"appId": app_id, "loginId": login_id}
    if tenant_id:
        payload["tenantId"] = tenant_id

    r = requests.post(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code != 200:
        log.debug("Descope REST: start_connect non-200 %s %s", r.status_code, r.text)
        return {"ok": False, "status": r.status_code, "resp": r.json() if r.content else {}}

    j = r.json()
    return {"ok": True, "url": j.get("url"), "resp": j}

def get_connection(provider: str, login_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    app_id = APP_IDS.get(provider)
    if not app_id:
        return {"ok": False, "error": f"Unknown provider '{provider}'"}

    url = f"{DESCOPE_API}/v1/outbound/oauth/connection/get"
    payload = {"appId": app_id, "loginId": login_id}
    if tenant_id:
        payload["tenantId"] = tenant_id

    r = requests.post(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code != 200:
        log.debug("Descope REST: get_connection non-200 %s %s", r.status_code, r.text)
        return {"ok": False, "status": r.status_code, "resp": r.json() if r.content else {}}

    j = r.json() if r.content else {}
    return {"ok": True, "resp": j}

def _demo_token(provider: str) -> Optional[str]:
    env_name = {
        "slack": "DEMO_BEARER_TOKEN_SLACK",
        "notion": "DEMO_BEARER_TOKEN_NOTION",
        "github": "DEMO_BEARER_TOKEN_GITHUB",
        "gcal": "DEMO_BEARER_TOKEN_GCAL",
        "google-calendar": "DEMO_BEARER_TOKEN_GCAL",
    }.get(provider)
    if not env_name:
        return None
    return os.getenv(env_name) or None

def get_token(provider: str, user_id: str, tenant_id: Optional[str]) -> Optional[str]:
    demo = _demo_token(provider)
    if demo:
        log.debug("get_token: using DEMO token for provider=%s", provider)
        return demo

    if not PROJECT_ID or not MGMT_KEY:
        log.debug("get_token: project or management key missing; cannot use Descope")
        return None

    conn = get_connection(provider, user_id, tenant_id)
    if not conn.get("ok"):
        log.debug("get_token: get_connection failed %s", conn)
        return None

    data = conn.get("resp") or {}

    token = (
        data.get("accessToken")
        or data.get("token")
        or data.get("botToken")
        or (data.get("credentials") or {}).get("access_token")
    )
    if not token:
        log.debug("get_token: no token in connection payload: %s", json.dumps(data)[:400])
        return None

    return token
