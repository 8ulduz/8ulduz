# Müvəqqəti: dövlət saytlarının GitHub IP-sindən açılıb-açılmadığını ölçür. PR birləşməzdən əvvəl silinir.
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import updater
feeds = {f[0]: f for f in updater.FEEDS}
for name in sorted(updater.SLOW_ONLY_FEEDS) + ["Naxçıvan TV"]:
    t = time.time()
    _, items, err, used = updater.fetch_feed(feeds[name])
    dated = sum(1 for i in items if i.get("pubDate"))
    print(f"REACH {name:22} {time.time()-t:5.1f}s say={len(items):2} tarixli={dated:2} url={used} xeta={err}", flush=True)
    if items:
        print("   ", str(items[0].get("pubDate"))[:16], "|", items[0]["title"][:90], flush=True)
