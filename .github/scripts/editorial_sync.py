"""Redaksiya qərarlarını arxa planda alır. Xəbərin sürətli dövrəsi şəbəkə gözləmir."""
import base64
import json
import os
import pathlib
import re
import sys
import time
import urllib.request


def validate(records):
    if not isinstance(records, dict):
        raise ValueError("invalid removal list")
    for key, row in records.items():
        if not isinstance(key, str) or not isinstance(row, dict):
            raise ValueError("invalid removal")
        for name in ("urls", "ids", "keys"):
            if not isinstance(row.get(name, []), list) or not all(isinstance(s, str) for s in row.get(name, [])):
                raise ValueError("invalid removal fields")
        if not row.get("urls") or not all(u.startswith("https://") for u in row["urls"]):
            raise ValueError("invalid removal URLs")
    return records


def sync_once(root, repo, token, opener=urllib.request.urlopen):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("invalid repository")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/assets/content-policy.js?ref=main",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                 "User-Agent": "8ulduz-editorial-sync", "X-GitHub-Api-Version": "2022-11-28"})
    with opener(request, timeout=10) as response:
        data = json.load(response)
    if data.get("encoding") != "base64":
        raise ValueError("invalid policy response")
    text = base64.b64decode(data["content"], validate=False).decode("utf-8")
    policy = json.loads(text[text.index("{"):text.rindex("}") + 1])
    records = validate(policy.get("removedArticles", {}))
    dest = pathlib.Path(root) / ".cache" / "editorial-removals.json"
    # Siyahı əlavə olunur: köhnə cavab və ya boş siyahı silinmiş xəbəri geri gətirməsin.
    try:
        previous = validate(json.loads(dest.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        previous = {}
    records = {**previous, **records}
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    if dest.exists() and dest.read_text(encoding="utf-8") == encoded:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(".tmp")
    temp.write_text(encoded, encoding="utf-8")
    os.replace(temp, dest)
    return True


def main():
    root = os.environ.get("UPDATER_ROOT", ".")
    repo = os.environ.get("GITHUB_REPOSITORY", "8ulduz/8ulduz")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Redaksiya sinxronu: giriş açarı yoxdur", flush=True)
        return 1
    while True:
        try:
            if sync_once(root, repo, token):
                print("Redaksiya silinmə siyahısı yeniləndi", flush=True)
        except Exception as error:
            # Sorğunun/istifadəçinin açarı və cavab mətni loqa çıxmır; son sağlam siyahı qalır.
            print("Redaksiya sinxronu alınmadı:", type(error).__name__, flush=True)
        if "--watch" not in sys.argv:
            return 0
        time.sleep(15)


if __name__ == "__main__":
    raise SystemExit(main())
