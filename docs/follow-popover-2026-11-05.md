# İzləmə panelinin görünüş yeniləməsi — 5 noyabr 2026

Sahibin istəyi ilə panel hava/namaz pəncərələri kimi başlığın altında açılır. Səhifə qaraldılmır, sürüşdürmə kilidlənmir. Panel ekran kənarlarından daşmır; altlıqdakı düymə üçün yer azdırsa yuxarı açılır, qısa landşaft ekranında mövcud sahəyə sığır. Bağlanma ekranda dərhal olur; tarixçə cavabı gec gəlsə də onu gözləmir. Geri, Escape, ×, təkrar düymə və kənar klik işləyir. Xarici bölmə keçidi itmir, başqa idarəyə fokus geri oğurlanmır. Arxa karuselin avtomatik hərəkəti paneli bağlamır.

Kənarda iki sabit rəngli qat var: sarı və göy. Yalnız şəffaflıq 6 saniyəlik dövrlə dəyişir; mətn, ölçü və kölgə radiusu dəyişmir. Hərəkəti dayandır ayarı hər iki animasiyanı saxlayır.

Sahibin təsdiqlədiyi Instagram `https://www.instagram.com/8ulduz.az/` əlavə olunub. Paneldə Telegram, Facebook, Instagram, LinkedIn və X görünür. Kod yalnız toxunanda yüklənir; xarici SDK, şrift və ayrıca ikon paketi yoxdur. Yenilənmiş modula keşdən asılı qalmamaq üçün ayrıca sorğu etiketi verilib; SW v52.

## Sürət

Lokal gzip serveri, eyni sabit məlumatlar, Lighthouse 12.8.2; hər profil üzrə bir əvvəl/sonra cütü. Canlı kanal/statistika/hava/namaz sorğuları bloklanıb, şəkil ünvanları eyni saxlanıb. Kiçik bal fərqləri sabit sürət qazancı və ya itkisi sübutu deyil.

| Profil | Bal | FCP (s) | LCP (s) | TBT (ms) | Transfer (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telefon | 74 → 76 | 1,28 → 1,23 | 3,21 → 3,20 | 778 → 669 | 732 718 → 732 516 |
| Planşet | 78 → 77 | 1,28 → 1,30 | 3,14 → 3,20 | 611 → 633 | 729 991 → 729 902 |
| Kompüter | 91 → 95 | 0,35 → 0,34 | 1,04 → 0,97 | 219 → 155 | 767 070 → 767 198 |

İlk açılışda nə izləmə modulu, nə idarəetmə kodu istənib. Kompozitləşdirilməyən animasiya auditi hər üç profildə keçib. `app.js` LF 219 652 / 220 000 B, CSS 94 663 / 95 000 B. Toxunmada yüklənən son modul gzip 3 307 B-dir; ilk açılışa daxil deyil. Telefonun «gözqırpımında» açılış hədəfinə çatıldığı iddia edilmir.

## Yoxlama

JavaScript 224 test: əvvəlki yoxlamalara əlavə olaraq dar/landşaft ekranı, ani bağlanma, kənar fokus, xarici bölmə keçidi və avtomatik karusel sınaqları. Brauzerdə 320/390 px, böyük şrift, hava panelinə keçid, Geri, iki rəngin şəffaflığı və hərəkəti dayandırma yoxlanıb. 320 px testində görünən sahə 305 px, panel 8–297 px aralığındadır; böyük şriftdə də şaquli sahəyə sığır. Arxa xəbər axını dəyişmir.
