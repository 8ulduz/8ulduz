# Müvəqqəti: özəl regional saytların GitHub IP-sindən açılıb-açılmadığını ölçür. PR birləşməzdən əvvəl silinir.
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import updater
feeds = {f[0]: f for f in updater.FEEDS}
for name in ["Narnews.az", "Cenub.az", "Gəncəxəbər", "Qarabağ Media", "Yurd.Media", "Region Plus", "Gündəlik.az"]:
    t = time.time()
    _, items, err, used = updater.fetch_feed(feeds[name])
    dated = sum(1 for i in items if i.get("pubDate"))
    print(f"REACH {name:22} {time.time()-t:5.1f}s say={len(items):2} tarixli={dated:2} url={used} xeta={err}", flush=True)
    for i in items[:3]:
        print("   ", str(i.get("pubDate"))[:16], "|", updater.categorize(i["title"], i.get("description", ""), feeds[name][3] if len(feeds[name]) > 3 else None)[:14] if hasattr(updater, "categorize") else "", "|", i["title"][:80], flush=True)
