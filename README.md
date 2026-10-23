# 8ulduz — sayt yenilənməsi

Bu paketdəki faylları repo-nun kökünə yükləyin (köhnələri əvəz edir):

- `index.html` + `assets/` — saytın özü (video və şəkillər çıxarılıb, dizayn əvvəlki kimidir)
- `data/news.json` — xəbər lenti (avtomatik yenilənir)
- `updater.py` — xəbər toplayan skript (hər 15 dəqiqədə)
- `.github/workflows/update.yml` — avtomatlaşdırma

Quraşdırma: `github.com/8ulduz/8ulduz/upload/main` ünvanına bütün faylları sürüşdürün → Commit changes.
Sonra Actions → "Xəbərləri yenilə" → Run workflow ilə dərhal doldura bilərsiniz.
