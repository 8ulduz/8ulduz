# 8ulduz — son xəbərlər saytı

Statik xəbər aqreqatoru: GitHub Actions hər 5 dəqiqədən bir RSS lentlərini toplayır, sayt isə JSON faylları oxuyur.

## Struktur

- `index.html`, `assets/app.js`, `assets/app.css` — saytın **mənbə kodu** (build addımı yoxdur, birbaşa redaktə olunur).
  Marşrutlar: `#/` (baş səhifə), `#/bolme/<slug>` (bölmə), `#/axtar?q=...` (axtarış).
- `data/news.json` — xəbər lenti (avtomatik yenilənir, yığcam JSON).
- `data/markets.json` — valyuta (AMB, ehtiyat: ExchangeRate-API), Brent/WTI neft və bitcoin (Yahoo Finance, ehtiyat: CNBC/CoinGecko), qızıl/gümüş (gold-api.com).
- `updater.py` — RSS + bazar məlumatı toplayıcı. Mənbə siyahısı: `AZ_FEEDS`, `WORLD_FEEDS`.
- `.github/workflows/update.yml` — avtomatik yeniləmə işi.

Hava məlumatı brauzerdə birbaşa Open-Meteo-dan alınır (açar tələb etmir).

## Lokal yoxlama

```bash
python updater.py            # xəbər + bazar
python updater.py --no-markets
python -m http.server 8000   # sonra http://localhost:8000/
```

## Yenilənmə

GitHub Actions hər 5 dəqiqədə bir `updater.py` faylını işə salır; məlumat dəyişibsə commit edir
(eyni vaxtda yalnız bir iş işləyir, push-dan əvvəl `git pull --rebase`).

Manual işə salmaq üçün: **Actions → Xəbərləri yenilə → Run workflow**.

## Saytı dərc etmək

**Settings → Pages → Source: `main` branch** → Save. Ünvan: `https://8ulduz.github.io/8ulduz/`
