
import requests

GCAL_API = "https://www.googleapis.com/calendar/v3"

def _auth_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

def check_conflicts(token: str, calendar_id: str, start_iso: str, end_iso: str):
    params = {
        "timeMin": start_iso,
        "timeMax": end_iso,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 10,
    }
    url = f"{GCAL_API}/calendars/{calendar_id}/events"
    r = requests.get(url, headers=_auth_headers(token), params=params, timeout=15)
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "resp": r.json() if r.headers.get("content-type","").startswith("application/json") else {"text": r.text}}
    data = r.json()
    conflicts = []
    for it in data.get("items", []):
        if it.get("status") == "cancelled":
            continue
        s = (it.get("start") or {}).get("dateTime") or (it.get("start") or {}).get("date")
        e = (it.get("end") or {}).get("dateTime") or (it.get("end") or {}).get("date")
        conflicts.append({
            "id": it.get("id"),
            "summary": it.get("summary"),
            "start": s,
            "end": e,
        })
    return {"ok": True, "conflicts": conflicts}

def create_calendar_event(token: str, calendar_id: str, summary: str, start_iso: str, end_iso: str, description: str | None = None):
    payload = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    if description:
        payload["description"] = description

    r = requests.post(
        f"{GCAL_API}/calendars/{calendar_id}/events",
        headers=_auth_headers(token),
        json=payload,
        timeout=15,
    )
    if r.status_code in (200, 201):
        return {"ok": True, "status": r.status_code, "event": r.json()}
    try:
        j = r.json()
    except Exception:
        j = {"text": r.text}

    return {"ok": False, "status": r.status_code, "error": j}
