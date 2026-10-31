"""Dərcdən əvvəl updater.py-ın yazdığı faylları yoxlayır.

- Zədəli faylların adını çap edir: pipeline.sh onları son sağlam nüsxə ilə əvəz edir.
- QIRMIZI XƏTT 2: qaydanı pozan xəbərləri fayldan çıxarır. updater.py-ın köhnə (son işlək) versiyası
  işləsə də, yazılan lent bu qapıdan keçir.

Yarımçıq yazılmış və ya boş news.json dərc olunsa sayt açılmır, növbəti dövrə də tarixçəni itirir.
Bu skriptin özü xəta versə heç nə çap etmir və dərc davam edir: yeniləmə buna görə dayanmamalıdır.
"""
import json
import os
import pathlib
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import content_policy  # noqa: E402


def bad_outputs(root=pathlib.Path(".")):
    root = pathlib.Path(root)
    bad = []
    for path in sorted((root / "data").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            bad.append(path)
            continue
        if path.name == "news.json" and not (isinstance(data, dict) and isinstance(data.get("articles"), list) and data["articles"]):
            bad.append(path)
    for name in ("sitemap.xml", "feed.xml"):
        path = root / name
        if not path.exists():
            continue
        try:
            ET.parse(path)
        except Exception:
            bad.append(path)
    return [p.relative_to(root).as_posix() for p in bad]


def enforce_policy(root=pathlib.Path(".")):
    """Lent fayllarından qaydanı pozan xəbərləri çıxarır. {fayl: {səbəb: say}} qaytarır."""
    root = pathlib.Path(root)
    removed = {}
    archive = [f"arxiv/{p.name}" for p in sorted((root / "data" / "arxiv").glob("*.json"))]
    for name in ("news.json", "latest.json", *archive):
        path = root / "data" / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            articles = data["articles"]
        except Exception:
            continue
        clean, dropped = content_policy.enforce(articles)
        if clean == articles:
            continue
        data["articles"] = clean
        if "count" in data or name in ("news.json", "latest.json"):
            data["count"] = len(clean)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, path)
        removed[name] = dropped
    # Video və sosial bloklar da: kanal icazəli olmalıdır, xəbərdən çıxarılan paylaşımın mənbəsi siyahıda olmalıdır.
    for name, key, allowed in (("video.json", "items", lambda v: v.get("channel") in content_policy.VIDEO_CHANNELS),
                               ("social.json", "posts", lambda p: not p.get("via") or content_policy.source_registered(p["via"]))):
        path = root / "data" / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data[key]
        except Exception:
            continue
        clean = [row for row in rows if allowed(row)]
        if len(clean) == len(rows):
            continue
        data[key] = clean
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, path)
        removed[name] = {"icazəli siyahıda deyil": len(rows) - len(clean)}
    return removed


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    for name, dropped in enforce_policy(root).items():
        print(f"::warning::{name}: qaydanı pozan xəbərlər çıxarıldı: {dropped}", file=sys.stderr)
    for name in bad_outputs(root):
        print(name)
