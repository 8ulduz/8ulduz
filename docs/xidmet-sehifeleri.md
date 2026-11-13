# Namaz, hava və məzənnə səhifələri (2026-11-13)

Sahibin qərarı (2026-11-13, «Bəli, qur»): Google-da hər gün axtarılan sorğuların öz ünvanı olsun. Əvvəl namaz və hava yalnız başlıqdakı göstərici idi, məzənnə isə bir ümumi səhifə (`/bolme/valyuta/`): axtarış sistemi «Bakı namaz vaxtları», «Gəncədə hava», «dollar məzənnəsi» sorğularına verə biləcəyi səhifə görmürdü.

## Ünvanlar

| Ünvan | Nə göstərir | Sayı |
|---|---|---|
| `/bolme/namaz/` | bütün şəhərlərin bugünkü vaxtları | 1 |
| `/bolme/namaz/<şəhər>/` | bugünkü vaxtlar və ayın tam təqvimi | 46 |
| `/bolme/hava/` | bütün şəhərlərdə son ölçü və bugünkü proqnoz | 1 |
| `/bolme/hava/<şəhər>/` | son ölçü və 7 günlük proqnoz | 46 |
| `/bolme/mezenne/<dollar, avro, rubl, lire, yuan>/` | AMB məzənnəsi və çevirmə cədvəli | 5 |

Şəhər siyahısı saytdakı göstəricinin siyahısıdır (`assets/app.js` `CITIES`); `tests/xidmet-sehifeleri.test.cjs` iki siyahının, namaz üsulunun və hava adlarının eyni qalmasını yoxlayır.

## Necə işləyir

- Kod `updater.py`-dadır («namaz, hava və məzənnə səhifələri» bloku). Səhifələr `bolme/` altındadır, çünki `pipeline.sh` main-ə bu qovluğu yazır: pipeline dəyişməyib.
- Şəbəkə sorğusu yalnız yavaş dövrədədir (`update_city_data`, qırmızı xətt 1):
  - namaz: Aladhan `/calendar`, `method=13` (göstərici ilə eyni). Şəhər başına ayda bir sorğu, bir dövrədə ən çoxu 8; ilk xətada dövrə dayanır. Cədvəl `data/namaz.json`-da qalır (ayda bir dəfə dəyişir), ayın 25-dən sonra növbəti ay da alınır.
  - hava: Open-Meteo, 46 şəhər bir sorğuda, saatda bir dəfə (`.cache/hava.json`). Yarıdan az şəhər gəlsə əvvəlki məlumat qalır.
  - məzənnə: sorğu yoxdur, `data/markets.json`-dan.
- Səhifələri `write_public` → `write_subpages` saxlanmış məlumatdan yazır; dəyişməyən səhifə yenidən yazılmır. Yazılmış səhifələr `sitemap.xml`-ə düşür (`subpage_locs`).
- Səhifə tətbiqi yükləmir: bir HTML, daxili CSS, xarici sorğu yoxdur (CSP `default-src 'none'`). Baş səhifənin ilk açılışına heç nə əlavə olunmur.
- Namaz səhifəsində bir kiçik daxili skript var (CSP-də hash ilə): xidmət işçisi səhifənin saxlanmış nüsxəsini dərhal verdiyi üçün dünənki nüsxədə «bu gün» köhnə qalardı; skript ayın cədvəlindən Bakı vaxtı ilə bugünkü sətri seçir. Şəbəkəyə getmir.
- Keçidlər: bölmə səhifələrinin altlığı, `/bolme/valyuta/` (valyuta səhifələrinə), şəhərin namaz və hava səhifələri bir-birinə.
- Rayon səhifələri (`rayon/<ad>/`, `.github/scripts/topics.cjs`) öz şəhərinin namaz və hava səhifəsinə «Xidmətlər» sətri ilə keçid verir — yalnız həmin səhifə artıq yazılıbsa. Keçid yarananda rayon səhifəsi bir dəfə, bir saatlıq fasiləni gözləmədən yazılır (`svc` səhifənin içindəki JSON-da saxlanır).

## Məlum hədlər

- Namaz vaxtları Diyanət üsulu ilə hesablanır; Qafqaz Müsəlmanları İdarəsinin təqvimindən fərqlənə bilər (səhifədə yazılıb). QMİ-nin rəsmi cədvəli mənbə kimi qoşulmayıb.
- Hava model proqnozudur, rəsmi xəbərdarlıq deyil (səhifədə yazılıb). Open-Meteo cavab verməsə səhifə son ölçünü öz tarixi ilə göstərir; proqnozun bütün günləri keçmişdə qalanda səhifə yenilənmir.
- Hava səhifələri saatda bir dəyişir: main-ə saatda 47 kiçik fayl dəyişikliyi gedir.
- Baş səhifədən (tətbiqdən) bu səhifələrə keçid hələ yoxdur; `app.js` dəyişməyib. Rayon səhifələri (`rayon/<ad>/`) də hələ keçid vermir.
- Ziyarət sayğacı bu səhifələrdə yoxdur (xarici skript yüklənmir); nəticə Search Console-da ünvan üzrə ölçülür.
