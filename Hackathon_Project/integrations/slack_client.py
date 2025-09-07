import re
import time
import requests
from typing import Optional, Dict, Any, Union, List

SLACK_API = "https://slack.com/api"
DEFAULT_TIMEOUT = 20

def _api(token: str, method: str, payload: dict, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:

    return requests.post(
        f"{SLACK_API}/{method}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        json=payload,
        timeout=timeout,
    )

def _auth_test(token: str) -> Dict[str, Any]:
    r = _api(token, "auth.test", {})
    try:
        j = r.json()
    except Exception:
        j = {}

    j["_http_status"] = r.status_code
    return j

def _normalize_channel(value: str) -> str:

    if not value:
        return value

    value = value.strip()

    m = re.search(r"/archives/([A-Z0-9]{8,})", value)
    if m:
        return m.group(1)
    if value.startswith("#"):
        return value
    return value

def _lookup_channel_id(token: str, channel: str) -> Optional[str]:

    if channel and channel.startswith("C") and len(channel) >= 9:
        return channel
    if not channel.startswith("#"):
        return channel
    name = channel[1:]
    cursor = None
    for _ in range(20):
        r = requests.get(
            f"{SLACK_API}/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"exclude_archived": "true", "limit": 1000, **({"cursor": cursor} if cursor else {})},
            timeout=DEFAULT_TIMEOUT,
        )
        data = r.json()
        for ch in data.get("channels", []):
            if ch.get("name") == name:
                return ch.get("id")
        cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
        if not cursor:
            break
    return None

def _join_if_needed(token: str, channel_id: str) -> Optional[Dict[str, Any]]:

    r = _api(token, "conversations.join", {"channel": channel_id})
    try:
        j = r.json()
    except Exception:
        j = {}

    return j

def _post_with_retry(token: str, payload: dict, retries: int = 2) -> Dict[str, Any]:
    for attempt in range(retries + 1):
        r = _api(token, "chat.postMessage", payload)
        status = r.status_code
        try:
            j = r.json()
        except Exception:
            j = {}

        if status == 429:
            wait = int(r.headers.get("Retry-After", "1"))
            time.sleep(wait)
            continue

        return {"ok": bool(j.get("ok")), "status": status, "resp": j}
    return {"ok": False, "status": 429, "resp": {"error": "rate_limited"}}

def post_summary_to_slack(
    token: str,
    channel: str,
    text: str,
    *,
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None,
    unfurl_links: bool = False,
    link_names: bool = True,
) -> Dict[str, Any]:

    if not token or not token.startswith("xox"):
        return {"ok": False, "status": 401, "resp": {"error": "invalid_auth", "message": "Missing or bad Slack token"}}

    auth = _auth_test(token)
    if not auth.get("ok"):
        return {"ok": False, "status": auth.get("_http_status", 401), "resp": auth}

    norm = _normalize_channel(channel)
    channel_id = _lookup_channel_id(token, norm) or norm

    payload = {
        "channel": channel_id,
        "text": text or "",
        "unfurl_links": bool(unfurl_links),
        "link_names": 1 if link_names else 0,
    }
    if blocks:
        payload["blocks"] = blocks

        if not payload["text"]:
            payload["text"] = " "

    if thread_ts:
        payload["thread_ts"] = thread_ts

    result = _post_with_retry(token, payload)

    if result["resp"].get("error") in ("not_in_channel", "channel_not_found", "is_archived"):
        if isinstance(channel_id, str) and channel_id.startswith("C"):
            _join_if_needed(token, channel_id)
            result = _post_with_retry(token, payload)

    result["ok"] = bool(result.get("ok"))
    return result
