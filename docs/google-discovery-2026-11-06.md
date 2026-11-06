# Google görünürlüğü — 2026-11-06

## 1. Search Console (yalnız 8ulduz.az domeni)

- Ana səhifə URL Inspection: **URL Google indeksindədir**.
- Son tarama: 3 noyabr 2026; Googlebot smartphone; tarama və indekslənmə icazəlidir, səhifənin alınması uğurludur.
- İstifadəçinin canonical ünvanı https://8ulduz.az/; Google yoxlanmış URL-i seçib.
- Sitemap: https://8ulduz.az/sitemap.xml; uğurludur; son emal 4 noyabr; 16 səhifə aşkarlanıb.
- Ümumi icmal: veb axtarışdan 21 klik; indeksləmə hesabatının məlumatları hələ emal olunur.
- Bunlar Google News-da nəşr səhifəsinin yaradılması və ya qəbul zəmanəti deyil.
- İdman bölməsi /bolme/idman/ də URL Inspection ilə indeksdə təsdiqləndi; saxlanmış HTML-də düzgün başlıq, description, canonical və RSS keçidi görünür.

## 2. Texniki görünürlük

- Mövcud robots, canonical, RSS və statik bölmə səhifələri saxlanır.
- Yeni /haqqinda/ səhifəsi JavaScript, şəkil, şrift və xarici SDK olmadan oxunur; əsas səhifəyə əlavə sorğu yaratmır.
- Altlığın Haqqımızda keçidi bu həqiqi URL-ə aparır. Köhnə #/haqqinda ünvanı işləməyə davam edir.
- /haqqinda/ və /mexfilik/ sitemap generatoruna əlavə edilir. Sabit səhifələr üçün saxta gündəlik lastmod yazılmır.
- Sürətli dövrəyə iş və şəbəkə sorğusu əlavə edilmir. Mövcud content_policy son qapısı dəyişmir.

## 3. Kimlik, mənbə və düzəliş qaydası

- Sayt açıq şəkildə aqreqator kimi təqdim olunur; xəbərlərin müəllifliyi mənbələrdə qalır, tam mətn dərc edilmir.
- Mənbə seçimi və sahibin redaksiya məhdudiyyətləri saxlanır və açıqlanır.
- Saytın mövcud ictimai əlaqə ünvanı, düzəliş/hüquq müraciətinin qaydası, məxfilik və RSS keçidləri verilir.
- Şəxsi hesab məlumatları məhsula əlavə edilmir.

## 4. İzləmə və Google News

- followLinks artıq boş WhatsApp və Google News ünvanlarını gizlədir və Google axtarış URL-ini nəşr səhifəsi kimi qəbul etmir; mövcud testlərlə qorunur.
- Mövcud rəsmi Telegram və RSS təqdim olunur. Kanal və nəşr URL-ləri uydurulmur.
- Nəşr səhifəsini əl ilə yaratmaq olmur; müddət və qəbul zəmanəti verilmir. Aqreqator xəbərlərinə 8ulduz müəllifliyi və NewsArticle işarəsi əlavə edilmir.
- Sonrakı nəzarət Search Console-un News performans hesabatı və həqiqi nəşr səhifəsi ilə aparılmalıdır; site: axtarışı tək meyar deyil.

Rəsmi istinadlar:
- https://support.google.com/news/publisher-center/answer/15898024?hl=en
- https://support.google.com/news/publisher-center/answer/9606634?hl=en
- https://developers.google.com/search/blog/2021/07/google-news-top-questions

## Yoxlama və ölçü

- Canlı robots.txt, sitemap.xml, /bolme/idman/ və feed.xml: hamısı HTTP 200; idman canonical-ı öz ünvanıdır, noindex yoxdur.
- Python: 270 test; Node: 253 test uğurludur. Windows sandbox-ın standart TEMP qovluğunda ilk Node cəhdi rename icazəsi ilə yarımçıq qaldı; layihənin test TEMP qovluğunda tam təkrar uğurludur.
- Yeni səhifə: 4259 bayt, skript/şəkil/şrift/SDK sorğusu 0. 390/768/1366 enlərində üfüqi daşma yoxdur (sənəd eni 375/753/1351).
- Əsas app.js: 223114 → 223113 bayt (−1); app.css və ana səhifə HTML-i dəyişmir; ilk açılışa əlavə sorğu/yük 0. Tam Lighthouse ölçümü bu dəyişiklik üçün aparılmayıb; sürət iddiası yükün dəyişməməsinə və yeni səhifənin ayrıca ölçüsünə aiddir.
- Mövcud boş kanal keçidlərinin gizlədilməsi testləri keçib; icazəli mənbə siyahısı, content_policy və sürətli dövrə dəyişmir.

Yayım sonrası yeni /haqqinda/ ünvanının indekslənməsi sorğusu və sitemap yenidən təqdimatı ayrıca Search Console-da yoxlanır. İndekslənmənin və Google News nəşr səhifəsinin vaxtını Google müəyyən edir.
