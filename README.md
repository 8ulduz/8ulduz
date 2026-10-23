# 8ulduz — quraşdırma (5 addım, ~5 dəqiqə)

1. **github.com → sağ üstdə "New repository" → ad: `8ulduz` → Public → Create repository**
   (Actions pulsuz işləyir — həm public, həm private repo-da)

2. **Faylları yükləyin:** yeni repo səhifəsində "uploading an existing file" linkinə klikləyin
   və ya "Add file → Upload files" — bu qovluqdakı faylları sürüşdürüb buraxın
   (index.html, news.json, updater.py, README.md və `.github` qovluğu — gizli fayldır, onu da yükləyin).
   Sonra "Commit changes" düyməsini basın.

3. **Səhifəni aktivləşdirin:** repo → **Settings → Pages** → Source: **Deploy from a branch**
   → Branch: **main / (root)** → **Save**. 1-2 dəqiqə gözləyin.

4. **Hazır!** Sayt: `https://SIZIN-ADINIZ.github.io/8ulduz/`
   (SIZIN-ADINIZ = GitHub istifadəçi adınız)

5. **Avtomatlaşdırma özü işə düşür:** GitHub Actions hər 15 dəqiqədə bir yoxlayır,
   yeni xəbəri `news.json`-a əlavə edir və sayt avtomatik yenilənir.
   İzləmək üçün repo → **Actions** bölməsi. Əl ilə test üçün "Xəbərləri yenilə" → "Run workflow".

## Qeydlər
- Hər şey pulsuzdur: GitHub Pages + GitHub Actions. Heç bir aylıq kvota sərfi yoxdur (aylıq limitlər xəbər saytı üçün yetərlidir).
- Kompüteriniz sönük olsa da sayt yenilənir — hər şey GitHub serverlərində işləyir.
- Yoxlama tezliyini dəyişmək üçün `.github/workflows/update.yml` faylında `*/15` hissəsini dəyişin (məs. `*/10` — 10 dəqiqə).
- Saytda yenilənmə görünmə tezliyi: `index.html`-də `REFRESH_SEC = 30` (saniyə ilə; istəsəniz 10 yazın).
- Mənbə əlavə etmək: `updater.py`-də `FEEDS` siyahısına bir sətir əlavə edin.
- Bəzi xəbər saytları RSS ünvanlarını vaxtaşırı dəyişir — `Actions` bölməsində qırmızı ❌ görünsə,
  `updater.py`-də həmin mənbənin ünvanını yeniləyin (xəta mesajında hansı mənbə olduğu yazılır).

## Öz domeniniz (sonra — istəyə bağlı)
Domen alındıqdan sonra: repo → Settings → Pages → Custom domain: `8ulduz.com` yazın,
domen provayderində CNAME qeydi: `SIZIN-ADINIZ.github.io`. SSL avtomatik verilir.
