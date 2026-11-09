# Bu repoda işləyən agentlər üçün

Saytın üç dəyişməz qırmızı xətti var: [docs/qirmizi-xetler.md](docs/qirmizi-xetler.md). Dəyişiklikdən əvvəl oxuyun.

Bu repoda xarici yazılar yalnız **8ulduz** GitHub hesabı ilə **8ulduz/8ulduz** hədəfinə edilir. Yazıdan əvvəl faktiki hesabı yoxlayın; başqa layihənin girişini və fork tarixçəsini buraya gətirməyin.

Sahibin 2026-11-05 göstərişi: sürət hər cihazda və tətbiqdə birinci prioritetdir; daimi hədəf «gözqırpımında» açılışdır. Adi oxucuya idarəetmə kodu və xarici sosial SDK yükləməyin. Əlavə ilkin yükü və telefon/planşet/kompüter ölçüsünü yoxlayın.

1. Xəbər ən geci 60 saniyədən bir yenilənir, axın dayanmır. Sürətli dövrəyə şəbəkə sorğusu və ya ağır iş əlavə etməyin; onlar `slow_cycle`-a gedir.
2. Xarici mənbələrdən Azərbaycan və rəhbərliyi haqqında, müxalifət mənbələrindən xəbər düşmür. Lentə yazan hər yol `content_policy.enforce`-dan keçməlidir.

`tests/test_red_lines.py` və ya `bir-deqiqe` işi düşürsə, testi yumşaltmayın, dəyişikliyi düzəldin. Qaydanı yalnız sayt sahibi dəyişə bilər, onun açıq göstərişi olmadan dəyişməyin.

## app.js və app.min.js

Oxucuya `assets/app.min.js` gedir: `assets/app.js`-in kiçildilmiş nüsxəsi (sahibin qərarı, 2026-11-08). Kodu yalnız `assets/app.js`-də dəyişin, sonra nüsxəni qurun:

```
npm ci --prefix .github/kicilt --ignore-scripts   # bir dəfə
node .github/kicilt/kicilt.cjs
```

`app.min.js`-i əl ilə dəyişməyin. Köhnə qalsa və ya mənbədən fərqli HTML versə `node --test tests/*.test.cjs` düşür. Ölçü həddi (170 000 bayt) `app.min.js`-ə aiddir.

## GitHub hesabı

Sayt **`8ulduz`** hesabınındır; `VM6666AZ` (Karvansara/Xeyirli reposunun hesabı) bu sayta toxunmur (sahibin qərarı, 2026-11-02 və 2026-11-07).

- `git push` özü `8ulduz` ilə gedir: `C:\Users\user\8ulduz` klonunun yerli `credential.https://github.com.helper` ayarı `8ulduz`-un `gh` açarına bağlıdır və bütün worktree-lərə şamildir. Bunu dəyişməyin. Commit müəllifi `8ulduz <346370484+8ulduz@users.noreply.github.com>`-dur.
- `gh` əmrləri aktiv hesabla gedir; aktiv hesab `8ulduz`-dur. Əmin olmaq üçün: `GH_TOKEN="$(gh auth token --user 8ulduz)" gh pr merge ...`
- **`gh auth switch` işlətməyin.** Başqa repoda VM6666AZ lazımdırsa, orada `GH_TOKEN="$(gh auth token --user VM6666AZ)"` ilə işlədin.

## Sürət yoxlama siyahısı (hər PR; sahib, 2026-11-09)

Sahibin qərarı: sürət «gözqırpımı»dır — açılışda, keçidlərdə, mənbəyə gedib qayıdanda, paylaşımda və paylaşımdan açılanda; gələcək əlavələr onu azaltmamalıdır. Hər dəyişiklikdə:

1. Yeni xüsusiyyət = tənbəl modul (`import()`); ilk açılışa yeni fayl, yeni sorğu, yeni iş yoxdur (`tests/struktur.test.cjs`, `tests/acilis-muqavilesi.test.cjs`). Açılışdan sonrakı iş `afterNews(() => …)` içinə.
2. Xarici ünvan əlavə edirsinizsə `tests/fixtures/ucuncu-terefler.json`-a yazın; səhifə açıq olarkən soruşulan ünvan yönləndirməməlidir (3xx cavab bfcache-i söndürür: mənbədən geri qayıdış ani əvəzinə ~0,7 s).
3. Çəkiliş kodunda yerləşdirmə oxuması (`getBoundingClientRect`, `offsetTop`, `innerWidth`, `scrollY` …) əlavə etməyin — ölçünü hadisədən (resize/scroll) və ya `afterFrame`-dən sonra oxuyun (`tests/cpu-guard.test.cjs` sayır, yalnız azala bilər).
4. `node .github/kicilt/kicilt.cjs`, sonra `node --test tests/*.test.cjs`. Bütün büdcələr `tests/budce.json`-dadır; dəyişməsi yalnız sahibin qərarı ilə, eyni PR-da `docs/qirmizi-xetler.md` «Büdcə cədvəli»nə tarix və səbəblə.
5. Ölçün və PR-a yazın: `node .github/scripts/serve.cjs . 8080 &` + `SPEED_QUICK=1 SPEED_REPS=3 node .github/scripts/speed.cjs http://localhost:8080/ --budget`. Eyni kodun ölçüsü ±40% oynaya bilər: baza nüsxəsini eyni anda ölçün (A/A/B), ilk ölçüdən əvvəl brauzeri `404.html` ilə isidin (soyuq proses şrift işinə 0,3–1,6 s itirir).
