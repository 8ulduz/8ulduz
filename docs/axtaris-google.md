# Google axtarışı üçün xəbər səhifələri (2026-11-06)

**Problem.** Search Console (8ulduz.az@gmail.com): 28 gündə 33 göstəriş, 12 klik, yeganə sorğu «8 ulduz». Google sayta 17 səhifə kimi baxırdı: ana səhifə, bölmələr, xidmət səhifələri. Xəbərlər `#/xeber/ID` ünvanındadır, `#`-dan sonrasını isə Google ayrıca səhifə saymır. `/x/ID` paylaşma səhifələri `noindex`-dir və dərhal tətbiqə keçir.

**Həll.** `updater.write_story_pages` əsas Azərbaycan xəbərləri üçün `xeber/<id>/index.html` yazır. Əsas xəbər 4+ mənbədən gələn və ya Zuğulba xəbəridir.

Səhifədə nələr var:

- başlıq;
- Bakı vaxtı ilə tarix;
- xülasə;
- **xəbəri yazan bütün mənbələrin siyahısı**: aqreqatorun öz dəyəri budur, mətn kopyası deyil;
- bölmə keçidi;
- BreadcrumbList.

`NewsArticle` yoxdur, çünki müəllif biz deyilik.

Tətbiq bölmə səhifələrindəki kimi yüklənir və ünvan `#/xeber/ID?b=bölmə` olur. Oxucu üçün heç nə dəyişmir. `<img>` yoxdur: tətbiq açılana qədər əlavə sorğu getmir.

**Hər dövrədə nə olur**

- Yalnız yeni xəbərin və mənbə sayı dəyişən xəbərin səhifəsi yazılır. Siyahı `xeber/index.json`-dadır: `[vaxt, mənbə sayı, bölmə]`.
- Səhifə 30 gün qalır, sonra silinir. Sahibin çıxardığı xəbərin səhifəsi dərhal silinir.
- Şəbəkə sorğusu yoxdur.
- Hər xəbər `content_policy.enforce`-dan keçir, rəhbərliyə mənfi xəbər süzgəci də tətbiq olunur.

**Sitemap və keçidlər**

- `sitemap.xml`-ə son 5000 xəbər səhifəsi `lastmod` ilə əlavə olunur.
- Bölmə səhifələri səhifəsi olan xəbərə öz səhifəsi ilə keçid verir, qalan xəbərlərə mənbə ilə.

**Pipeline**

`pipeline.sh` `xeber/` qovluğunu `x/` kimi işləyir:

1. başlanğıcda repodan WORK-ə köçürür;
2. yayımda main-ə köçürür;
3. `git add xeber` edir.

**Risk.** Xülasə mənbədən gəlir. Google təkrar məzmunu aşağı sala bilər, ona görə yalnız əsas xəbərlər açılıb. Nəticəni Search Console-da «Səhifələr» və «Effektivlik» hesabatlarında yoxlayın. Hədd və ya müddət `STORY_MIN_SOURCES` və `STORY_KEEP_S` ilə dəyişir.

Testlər: `tests/test_search_discovery.py`, `StoryPagesTest`.

## Günün icmalı (2026-11-06)

Hər gün Bakı vaxtı ilə **09:00**-da və **19:00**-da `updater.write_digest` bir icmal yazır.

| Buraxılış | Ünvan | Hansı xəbərlər |
|---|---|---|
| Səhər | `icmal/<tarix>-seher/` | son 24 saatın xəbərləri |
| Axşam | `icmal/<tarix>-axsam/` | son 12 saatın xəbərləri, səhərkilər təkrarlanmır |

**Seçim qaydası:**
- 10 Azərbaycan xəbəri götürülür, ən çox mənbənin yazdığı birinci.
- Mənbə sayı bərabərdirsə, daha yenisi önə keçir.
- Eyni başlıq bir dəfə düşür.
- Xəbərlər `content_policy.enforce`-dan və rəhbərlik süzgəcindən keçir.

**Səhifə:**
- Skript və şəkil yoxdur, ölçüsü təxminən 6 KB-dır.
- Öz səhifəsi olan xəbər `xeber/<id>/`-ə aparır.
- Səhifədə Telegram çağırışı və əvvəlki buraxılışa keçid var.
- Buraxılış bir dəfə yazılır və dəyişmir.
- Pipeline buraxılış saatını keçirərsə, buraxılış ən gec 6 saat sonra yazılır.
- Buraxılışlar 90 gün qalır.

**Siyahılar:**
- `icmal/index.json`-da buraxılışlar və başlıqlar var.
- `icmal/index.html` arxivdir.
- Sitemap-də arxiv və son 60 buraxılış var.
- Bölmə və xəbər səhifələri «Günün icmalı»na keçid verir.

**Sosial şəbəkələr:**
- `social.cjs` buraxılışı Telegram-a və Facebook-a nömrəli siyahı və icmal linki ilə göndərir.
- 18 dəqiqəlik fasiləni gözləmir.
- 4 saatdan köhnə buraxılış göndərilmir.
