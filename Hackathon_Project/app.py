import os
import re
import time
import uuid
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

from providers.gemini_client import GeminiClient
from descope_adapter import get_token
from integrations.slack_client import post_summary_to_slack
from integrations.notion_client import append_to_page
from integrations.github_client import create_issue
from integrations.gcal_client import create_calendar_event

load_dotenv()
PORT = int(os.getenv("PORT", "5001"))

app = Flask(__name__, static_folder="static")
llm = GeminiClient()

TRUSTED_AGENTS = {
    "agent_slackbot": ["summarize", "post_slack"],
    "agent_notion":   ["update_notion"],
    "agent_github":   ["create_issue"],
    "agent_gcal":     ["create_event"],
}

NONCE_WINDOW_SECS = 300
_seen_nonces = set()

def _check_agent_scope(agent: str, action: str) -> bool:
    return action in TRUSTED_AGENTS.get(agent, [])

def _check_signature(req_body: bytes, ts: str, nonce: str) -> bool:
    try:
        now = int(time.time())
        if abs(now - int(ts)) > NONCE_WINDOW_SECS:
            return False
        if nonce in _seen_nonces:
            return False
        _seen_nonces.add(nonce)
        return True
    except Exception:
        return False

def _slack_channel_id(value: str) -> str:

    if not value:
        return value
    value = value.strip()

    m = re.search(r"/archives/([A-Z0-9]+)", value)
    if m:
        return m.group(1)

    return value

def _summarize_for_slack(raw: str) -> str:
    prompt = (
        "Convert the following raw updates into a Slack-ready daily standup. "
        "Use 2–4 concise bullet points, include blockers, and a one-line title.\n\n"
        f"{raw}"
    )

    return llm.generate(prompt)

def _summarize_for_notion(raw: str) -> str:
    prompt = (
        "Convert these raw updates into concise meeting notes for a Notion page. "
        "Start with a short title, then 3–6 bullets; include blockers and follow-ups. "
        "Keep it crisp and actionable.\n\n"
        f"{raw}"
    )

    return llm.generate(prompt)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

@app.post("/trigger-summary")
def trigger_summary():
    data = request.get_json(force=True, silent=True) or {}
    agent   = data.get("agent")
    action  = data.get("action", "summarize")
    messages = (data.get("messages") or "").strip()

    if not _check_agent_scope(agent, action):
        return jsonify({"error": "Unauthorized agent or action"}), 403

    ts = request.headers.get("X-Timestamp", str(int(time.time())))
    nonce = request.headers.get("X-Nonce", str(uuid.uuid4()))
    if not _check_signature((request.data or b"{}"), ts, nonce):
        return jsonify({"error": "Invalid or replayed request"}), 401

    if not messages:
        return jsonify({"error": "Missing 'messages' to summarize."}), 400

    try:
        summary = _summarize_for_slack(messages)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": f"Gemini summarization failed: {e}"}), 500

@app.post("/slack/post")
def slack_post():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent")
    if not _check_agent_scope(agent, "post_slack"):
        return jsonify({"error": "Unauthorized"}), 403

    token = get_token("slack", user_id=data.get("user_id","demo"), tenant_id=data.get("tenant_id"))
    if not token:
        return jsonify({"error": "No Slack token available (configure Descope Outbound App or DEMO_BEARER_TOKEN)"}), 401

    text = (data.get("text") or "").strip()
    if not text:
        msgs = (data.get("messages") or "").strip()
        if not msgs:
            return jsonify({"error": "Provide 'text' or 'messages' to summarize."}), 400
        try:
            text = _summarize_for_slack(msgs)
        except Exception as e:
            return jsonify({"error": f"Failed to summarize via Gemini: {e}"}), 500

    channel = _slack_channel_id((data.get("channel") or "").strip())
    if not channel:
        return jsonify({"error": "Missing Slack 'channel' (channel ID like C09… or paste the full channel URL)."}), 400

    res = post_summary_to_slack(token, channel, text)

    return jsonify(res), (200 if res.get("ok") else 400)

@app.post("/notion/update")
def notion_update():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent")
    if not _check_agent_scope(agent, "update_notion"):
        return jsonify({"error": "Unauthorized"}), 403

    token = get_token("notion", user_id=data.get("user_id","demo"), tenant_id=data.get("tenant_id"))
    if not token:
        return jsonify({"error": "No Notion token available (configure Descope Outbound App or DEMO_BEARER_TOKEN)"}), 401

    text = (data.get("text") or "").strip()
    if not text:
        msgs = (data.get("messages") or "").strip()
        if not msgs:
            return jsonify({"error": "Provide 'text' or 'messages' to summarize."}), 400
        try:
            text = _summarize_for_notion(msgs)
        except Exception as e:
            return jsonify({"error": f"Failed to summarize via Gemini: {e}"}), 500

    page_id = (data.get("page_id") or "").strip()
    if not page_id:
        return jsonify({"error": "Missing 'page_id' (copy the hex id from the Notion page URL)."}), 400

    res = append_to_page(token, page_id, text)
    return jsonify(res), (200 if res.get("ok") else 400)

@app.post("/github/issue")
def github_issue():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent")
    if not _check_agent_scope(agent, "create_issue"):
        return jsonify({"error": "Unauthorized"}), 403

    token = get_token("github", user_id=data.get("user_id","demo"), tenant_id=data.get("tenant_id"))
    if not token:
        return jsonify({"error": "No GitHub token available (configure Descope Outbound App or DEMO_BEARER_TOKEN)"}), 401

    repo  = (data.get("repo")  or "owner/repo").strip()
    title = (data.get("title") or "From Agent").strip()
    body  = (data.get("body")  or "").strip()

    res = create_issue(token, repo, title, body)
    return jsonify(res), (200 if res.get("ok") else 400)

@app.post("/gcal/event")
def gcal_event():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent")
    if not _check_agent_scope(agent, "create_event"):
        return jsonify({"error": "Unauthorized"}), 403

    token = get_token("gcal", user_id=data.get("user_id","demo"), tenant_id=None)
    if not token:
        return jsonify({"error": "No Google Calendar token available (configure Descope Outbound App or DEMO_BEARER_TOKEN)"}), 401

    calendar_id = (data.get("calendar_id") or "primary").strip()
    summary     = (data.get("summary")     or "").strip()
    start_iso   = (data.get("start_iso")   or "").strip()
    end_iso     = (data.get("end_iso")     or "").strip()
    description = (data.get("description") or "").strip()
    force       = bool(data.get("force"))

    if not summary:
        return jsonify({"ok": False, "error": "Missing 'summary'"}), 400
    if not start_iso or not end_iso:
        return jsonify({"ok": False, "error": "Missing 'start_iso' and/or 'end_iso' (RFC 3339)"}), 400

    from integrations.gcal_client import check_conflicts, create_calendar_event
    chk = check_conflicts(token, calendar_id, start_iso, end_iso)
    if not chk.get("ok"):
        return jsonify({"ok": False, "status": chk.get("status"), "error": chk.get("resp")}), 400

    conflicts = chk.get("conflicts", [])
    if conflicts and not force:
        return jsonify({
            "ok": False,
            "conflict": True,
            "message": "This time conflicts with existing events.",
            "conflicts": conflicts
        }), 200

    res = create_calendar_event(token, calendar_id, summary, start_iso, end_iso, description=description)
    return jsonify(res), (200 if res.get("ok") else 400)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)
