"""Yeni iş ilk canlı yazını etdikdən sonra əvvəlki yeniləyiciləri dayandırır."""
import datetime
import json
import os
import urllib.error
import urllib.request


def previous_runs(current, runs):
    stamp = datetime.datetime.fromisoformat(current["created_at"].replace("Z", "+00:00"))
    result = []
    for row in runs:
        try:
            at = datetime.datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            if row["id"] != current["id"] and at < stamp and row.get("head_branch") == "main" and row.get("status") in ("queued", "in_progress"):
                result.append(int(row["id"]))
        except (KeyError, ValueError, TypeError):
            continue
    return result


def finish(run_id, api, published):
    if not published:
        raise ValueError("first live publish is required")
    current = api(f"actions/runs/{int(run_id)}")
    runs = api("actions/workflows/update.yml/runs?status=in_progress&branch=main&per_page=30")
    cancelled = []
    for ident in previous_runs(current, runs.get("workflow_runs", [])):
        try:
            api(f"actions/runs/{ident}/cancel", "POST")
            cancelled.append(ident)
        except urllib.error.HTTPError as error:
            if error.code != 409:
                raise
    return cancelled


def main():
    if os.environ.get("GITHUB_REPOSITORY") != "8ulduz/8ulduz":
        raise ValueError("wrong repository")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("missing workflow credential")
    def api(path, method="GET"):
        request = urllib.request.Request("https://api.github.com/repos/8ulduz/8ulduz/" + path,
            method=method, data=b"{}" if method == "POST" else None,
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "8ulduz-rollout"})
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
        return json.loads(body) if body else {}
    cancelled = finish(os.environ["GITHUB_RUN_ID"], api, os.environ.get("FIRST_LIVE_PUSH_OK") == "1")
    print("Yeni canlı yazı təsdiqləndi; əvvəlki yeniləyicilər dayandırıldı:", cancelled, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Növbə dəyişməsi tamamlanmadı:", type(error).__name__, flush=True)
        raise SystemExit(1)
