# İzləmə düyməsinin yığcamlaşdırılması — 5 noyabr 2026

Sahibin telefon rəyinə əsasən düymə 44 → 32 px, eni standart şriftdə təxminən 100 → 88 px oldu. Lupa sətrində qalır, bölmələri örtmür. Panel 360 → 260 px, beş keçidlə hündürlük 289 → 198 px oldu. Panel fonu «İdman» menyusunun `--nav-row`, keçidlərin fonu onun `--card` dəyişənidir; açıq/tünd rejimə birlikdə uyğunlaşırlar.

Kənar ikiqat 2 px sərhədlə daha aydındır. Sarı–göy dövr 6 → 2,4 saniyə, rəng fazaları arası 1,2 saniyədir. Yalnız şəffaflıq animasiya olunur; hərəkəti dayandırma ayarı saxlanır. Modul yalnız toxunmada yüklənir (`follow.js?v=4`), SW v54.

## Yoxlama

232 JavaScript testi keçdi. Brauzerdə 320 və 390 px, böyük şrift, açıq/tünd rejim, hərəkəti dayandırma və planşet ölçüsü yoxlandı. 390 px sınağında düymə y=44,7–76,7, «İdman» y=80,7–108,7 px: elementlər üst-üstə düşmür. Panel başlığın altında açılır; bütün beş keçid qalır.

Eyni məlumatlar, lokal gzip serveri və Lighthouse 12.8.2, hər profil üçün bir əvvəl/sonra cütü. Canlı lent/statistika/hava/namaz şəbəkəsi bloklanıb. Bu ölçülər sabit sürət artımı iddiası deyil.

| Profil | Bal | FCP (s) | LCP (s) | TBT (ms) | Transfer (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telefon | 71 → 73 | 1,33 → 1,30 | 3,08 → 3,08 | 993 → 915 | 724 464 → 724 480 |
| Planşet | 74 → 78 | 1,36 → 1,37 | 3,13 → 3,08 | 802 → 631 | 722 149 → 724 708 |
| Kompüter | 96 → 99 | 0,36 → 0,36 | 0,82 → 0,87 | 162 → 78 | 762 185 → 762 176 |

İlk açılışda izləmə və idarəetmə modulları istənmir. İzləmə animasiyası kompozitləşdirilməyən animasiya siyahısında yoxdur; əvvəlki karusel nöqtələrinin `width` keçidi siyahıda qalır. `app.js` LF 219 652 B olaraq qalır, CSS 94 663 → 94 710 B; eyni gzip sıxılmasında CSS fərqi +13 B-dir. Telefon üçün «gözqırpımında» hədəfinə çatıldığı iddia edilmir.
