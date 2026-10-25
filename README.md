# 8ulduz — son xəbərlər saytı

Bu repo saytın hazır (build edilmiş) fayllarını və avtomatik xəbər yeniləmə sistemini saxlayır.

## Struktur

- `index.html` + `assets/` — saytın hazır faylları
- `data/news.json` — xəbər lenti (avtomatik yenilənir)
- `updater.py` — RSS mənbələrindən xəbər toplayan skript
- `.github/workflows/update.yml` — avtomatik yeniləmə işi

## Yenilənmə

GitHub Actions hər 5 dəqiqədə bir `updater.py` faylını işə salır, `data/news.json` faylını yeniləyir və dəyişikliyi repoya yazır.

Manual işə salmaq üçün:

1. GitHub-da **Actions** bölməsini açın.
2. **Xəbərləri yenilə** işini seçin.
3. **Run workflow** düyməsini basın.

## Saytı dərc etmək

1. Repoda **Settings → Pages** yolunu açın.
2. **Source** bölməsində `main` branch-ını seçin.
3. **Save** düyməsini basın.

Dərcdən sonra sayt bu ünvanda açılacaq:

`https://8ulduz.github.io/8ulduz/`
