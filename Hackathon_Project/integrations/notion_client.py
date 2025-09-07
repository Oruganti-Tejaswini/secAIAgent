
import re
import requests

def _extract_page_hex(s: str) -> str | None:

    if not s:
        return None

    s = s.strip()

    m = re.search(r"([0-9a-fA-F]{32})", s)
    if m:
        return m.group(1).lower()

    m = re.fullmatch(r"([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{12})", s)
    if m:
        return "".join(m.groups()).lower()

    return None

def _to_uuid(s: str) -> str:
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"

def append_to_page(bearer_token: str, page_id: str, text: str) -> dict:

    if not bearer_token:
        return {"ok": False, "resp": {"error": "missing bearer token"}, "status": 401}

    if not page_id or not text:
        return {"ok": False, "resp": {"error": "missing page_id or text"}, "status": 400}

    hex_id = _extract_page_hex(page_id)
    if not hex_id:
        return {"ok": False, "resp": {"error": "invalid page_id format"}, "status": 400}

    block_id = _to_uuid(hex_id)
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": text[:1900]}}
                    ]
                },
            }
        ]
    }

    try:
        resp = requests.patch(url, headers=headers, json=payload, timeout=20)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"text": resp.text}
        return {"ok": resp.ok, "resp": data, "status": resp.status_code}

    except Exception as e:
        return {"ok": False, "resp": {"error": str(e)}, "status": 500}
