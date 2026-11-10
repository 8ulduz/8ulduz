"""Səma xəbərləri (oz_sema.py): Ay fazaları, gündönümü və bərabərlik, meteor axınları, tutulmalar.

Müvəqqəti: bu ilk nüsxə yalnız USNO-nun istinad cədvəllərini bir dəfə GitHub-dan alır (buradan USNO bağlantını kəsir),
testlər üçün fixture kimi saxlanacaq. Modulun özü növbəti commit-dədir.
"""
import pathlib
import sys
import time

import oz_xeber as ox

USNO = "https://aa.usno.navy.mil/api"
BAKU_COORDS = "40.4093,49.8671"
REF_URLS = [
    ("phases-2026", USNO + "/moon/phases/date?date=2026-01-01&nump=50"),
    ("phases-2027", USNO + "/moon/phases/date?date=2027-01-01&nump=50"),
    ("seasons-2026", USNO + "/seasons?year=2026"),
    ("seasons-2027", USNO + "/seasons?year=2027"),
] + [
    (f"rstt-{d}", USNO + f"/rstt/oneday?date={d}&coords={BAKU_COORDS}&tz=4")
    for d in ("2026-11-10", "2026-01-15", "2026-03-20", "2026-05-01", "2026-06-21", "2026-08-12", "2026-09-23",
              "2026-12-21", "2027-02-04", "2027-05-25")
] + [
    (f"solar-{d}", USNO + f"/eclipses/solar/date?date={d}&coords={BAKU_COORDS}&height=0")
    for d in ("2026-02-17", "2026-08-12", "2027-02-06", "2027-08-02")
]


def items(root, now, fetch=None):
    return []


def sinaq(root, now=None, fetch=None):
    fetch = fetch or ox._u().fetch
    md = ["## USNO istinad cədvəlləri (bir dəfəlik)", ""]
    for n, (name, url) in enumerate(REF_URLS):
        if n:
            time.sleep(1)
        try:
            body = fetch(url, timeout=30, headers={"Accept": "application/json"}).decode("utf-8", "replace")
        except Exception as e:
            md += [f"> {name}: alınmadı: {type(e).__name__} {getattr(e, 'reason', '') or e}"[:300], ""]
            continue
        md += [f"<!-- ref {name} -->", "```json", body.strip(), "```", ""]
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    sys.stdout.write("\n".join(sinaq(root)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
