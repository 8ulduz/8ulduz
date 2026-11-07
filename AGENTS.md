# Bu repoda işləyən agentlər üçün

Saytın üç dəyişməz qırmızı xətti var: [docs/qirmizi-xetler.md](docs/qirmizi-xetler.md). Dəyişiklikdən əvvəl oxuyun.

Bu repoda xarici yazılar yalnız **8ulduz** GitHub hesabı ilə **8ulduz/8ulduz** hədəfinə edilir. Yazıdan əvvəl faktiki hesabı yoxlayın; başqa layihənin girişini və fork tarixçəsini buraya gətirməyin.

Sahibin 2026-11-05 göstərişi: sürət hər cihazda və tətbiqdə birinci prioritetdir; daimi hədəf «gözqırpımında» açılışdır. Adi oxucuya idarəetmə kodu və xarici sosial SDK yükləməyin. Əlavə ilkin yükü və telefon/planşet/kompüter ölçüsünü yoxlayın.

1. Xəbər ən geci 60 saniyədən bir yenilənir, axın dayanmır. Sürətli dövrəyə şəbəkə sorğusu və ya ağır iş əlavə etməyin; onlar `slow_cycle`-a gedir.
2. Xarici mənbələrdən Azərbaycan və rəhbərliyi haqqında, müxalifət mənbələrindən xəbər düşmür. Lentə yazan hər yol `content_policy.enforce`-dan keçməlidir.

`tests/test_red_lines.py` və ya `bir-deqiqe` işi düşürsə, testi yumşaltmayın, dəyişikliyi düzəldin. Qaydanı yalnız sayt sahibi dəyişə bilər, onun açıq göstərişi olmadan dəyişməyin.

## GitHub hesabı

Sayt **`8ulduz`** hesabınındır; `VM6666AZ` (Karvansara/Xeyirli reposunun hesabı) bu sayta toxunmur (sahibin qərarı, 2026-11-02 və 2026-11-07).

- `git push` özü `8ulduz` ilə gedir: `C:\Users\user\8ulduz` klonunun yerli `credential.https://github.com.helper` ayarı `8ulduz`-un `gh` açarına bağlıdır və bütün worktree-lərə şamildir. Bunu dəyişməyin. Commit müəllifi `8ulduz <346370484+8ulduz@users.noreply.github.com>`-dur.
- `gh` əmrləri aktiv hesabla gedir; aktiv hesab `8ulduz`-dur. Əmin olmaq üçün: `GH_TOKEN="$(gh auth token --user 8ulduz)" gh pr merge ...`
- **`gh auth switch` işlətməyin.** Başqa repoda VM6666AZ lazımdırsa, orada `GH_TOKEN="$(gh auth token --user VM6666AZ)"` ilə işlədin.
