import requests

def create_issue(token: str, repo_full_name: str, title: str, body: str) -> dict:

    url = f"https://api.github.com/repos/{repo_full_name}/issues"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    payload = {"title": title, "body": body}
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    return {"ok": r.ok, "status": r.status_code, "resp": r.json() if r.content else {}}
