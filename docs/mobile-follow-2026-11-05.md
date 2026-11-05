# Mobil izləmə düyməsi — 5 noyabr 2026

Baza: `7b0724dbb282a85e8aa76a59d0112ce93dc8b550`.

## Davranış

- Telefonda (720 px və aşağı) lupanın yanında tam «8ULDUZ-u izlə» yazısı var. Statik HTML-də də mövcuddur; JavaScript gələndə yer dəyişmir.
- Mətn sabitdir. Ayrı kənar qatın şəffaflığı 3 saniyədə 0,25 → 0,9 → 0,25 dəyişir; işıq tam sönmür. Ölçü, kölgə radiusu və mətn animasiya olunmur. Hərəkəti azalt və saytın hərəkət düyməsi sabit parıltı seçir.
- Panel `follow.js` ilə yalnız ilk toxunuşda yüklənir. Hazırda yalnız əvvəlki Telegram ayarı var; digər platformalar rəsmi HTTPS ünvanları veriləndə görünür. Ünvanlar uydurulmur, boş seçimlər göstərilmir.
- Paneldə nativ dialog, klaviatura fokusunun saxlanması və açan düyməyə qayıdış var. Geri, Escape, × və kənara toxunma paneli bağlayır. Təkrar sürətli bağlama oxucunu saytdan çıxarmır. Tarixçəyə giriş verməyən WebView-də bağlama düyməsi işləyir.
- Altlıqdakı düymə eyni paneli kompüterdə də açır. Android keçidləri layihədəki mövcud Chrome Custom Tab mexanizmindən istifadə edir.

## Yoxlamalar

- JavaScript: 210 test keçib; 6 yeni test ünvanların yoxlanmasını, geri/Escape davranışını, təkrar bağlamanı və tarixçə xətasını əhatə edir.
- Python: 260 test keçib. Lent toplayıcısı, dəqiqəlik axın və mənbə qaydaları dəyişdirilməyib.
- Sintaksis, CSP hash-i, statik qabığın uyğunluğu və ölçü limitləri keçib.
- 320, 360, 375, 390, 430 və 720 px-də düymənin tam yazısı lupanın sətrində yerləşir. 320 px və böyük şriftdə də başlıq daşmır. Saytın əsas hissəsindəki əvvəlki 320/720 px daşması bu dəyişiklikdən yaranmır: baza və yeni versiyada başlıq eni 305 px, əsas səhifənin scroll eni 325 px idi.
- Brauzerdə açılma, Geri, Escape/bağlama, fokus və hərəkət ayarı yoxlanıb. Fiziki Android/iPhone tətbiq keçidləri cihazda yoxlanmayıb.

## Sürət

Eyni məlumat və gzip serveri, Lighthouse 12.8.2, təmiz profillər; telefon standart model, planşet 768×1024, kompüter desktop. Dəyişən canlı kanal, statistika, hava və namaz xidmətləri lokal müqayisədə bloklanıb. Şəkil ünvanları hər iki variantda eynidir. Hər profil üzrə bir əvvəl–sonra cütüdür; bal dəyişikliyi səbəb-nəticə sübutu deyil.

| Profil | Bal | FCP (s) | LCP (s) | TBT (ms) | Yük (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telefon əvvəl | 73 | 1,31 | 3,30 | 748 | 1 326 355 |
| Telefon sonra | 67 | 1,75 | 3,51 | 994 | 1 327 016 |
| Planşet əvvəl | 79 | 1,34 | 3,37 | 501 | 1 323 797 |
| Planşet sonra | 72 | 1,78 | 3,00 | 922 | 1 324 545 |
| Kompüter əvvəl | 96 | 0,36 | 1,10 | 129 | 1 385 538 |
| Kompüter sonra | 98 | 0,32 | 1,06 | 77 | 1 386 321 |

Telefonun izdə müşahidə olunmuş (modelləşdirilməmiş) FCP-si 1 215 → 1 204 ms, LCP-si 1 297 → 1 281 ms olub. Layout/stil işi 2 513 → 2 253 ms, skript işi 2 054 → 2 035 ms. Modelləşdirilmiş telefon/planşet balındakı geriləmə gizlədilmir; sabit sürət artımı iddia edilmir. Yeni parıltı kompozitləşdirilməyən animasiya xətalarına düşmür; əvvəlki karusel nöqtələrinin `width` animasiyaları hər iki variantda qalır.

İlk açılışın əlavə transferi bu ölçülərdə 661–783 B-dir və yük 1,5 MB-dan aşağı qalır. `follow.js` heç bir ilk açılış ölçüsündə istənməyib: modul 6 750 B, gzip 2 658 B və yalnız klikdə gəlir. Əsas fayllar (LF): `app.js` 219 602 / 220 000 B, `app.css` 94 527 / 95 000 B.

Rəsmi WhatsApp, Facebook, Instagram, LinkedIn və izlənə bilən Google News ünvanları sahibdən gözlənilir. Telegram üçün əvvəlki ayar saxlanılıb.

## Əsas budaqla uyğunlaşdırma

Sonradan `main`-də yayımlanmış idman səhifəsi sürət düzəlişləri (`3045d52068488d6914b136ad7949633616b3e2c3`) saxlanılıb. Yeganə birləşdirmə konflikti xidmət işçisinin versiya sətrində idi: yeni versiya `v49` oldu. Əsas JavaScript faylının ölçü limitinə sığması üçün yalnız izahlı şərhlər qısaldılıb; hazırkı LF ölçüsü 219 777 / 220 000 B-dir. CSS 94 527 / 95 000 B qalır. Yuxarıdakı Lighthouse rəqəmləri ilk variantın göstərilmiş bazasına aiddir; bu uyğunlaşdırma ayrıca sürət qazancı kimi təqdim edilmir.
