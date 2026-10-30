"""Dərcdən əvvəl updater.py-ın yazdığı faylları yoxlayır; zədəli olanların adını çap edir.

Yarımçıq yazılmış (timeout 240 ortada kəsəndə) və ya boş news.json dərc olunsa, sayt açılmır,
növbəti dövrə də köhnə lenti oxuya bilmir və tarixçəni sıfırdan başlayır. update.yml belə
faylları son dərc olunmuş versiya ilə əvəz edir. Bu skriptin özü xəta versə heç nə çap etmir
və dərc əvvəlki kimi davam edir.
"""
import json
import pathlib
import xml.etree.ElementTree as ET


def bad_outputs(root=pathlib.Path(".")):
    bad = []
    for path in sorted((root / "data").glob("*.json")):
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


if __name__ == "__main__":
    for name in bad_outputs():
        print(name)
