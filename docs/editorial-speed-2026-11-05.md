# Redaksiya paneli və izləmə keçidləri — sürət yoxlaması

Eyni məlumatla lokal gzip serverində əvvəl/sonra Lighthouse 12.8.2. Baza `21ac279443addb07c1fc9dd5be6a7f0de1006c7e`. Telefon standart profil, planşet 768×1024, kompüter desktop. Hər profil üzrə bir cüt ölçüdür; kiçik bal fərqi sabit sürət qazancı sübutu deyil. Dəyişən canlı kanal, statistika, hava və namaz üçüncü tərəf sorğuları bloklanıb, şəkil ünvanları eyni saxlanıb.

| Profil | Bal əvvəl → sonra | FCP (s) | LCP (s) | TBT (ms) | Transfer (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telefon | 75 → 76 | 1,37 → 1,26 | 3,08 → 3,07 | 749 → 710 | 731 642 → 731 765 |
| Planşet | 79 → 79 | 1,45 → 1,32 | 3,09 → 3,07 | 542 → 583 | 728 793 → 729 199 |
| Kompüter | 93 → 94 | 0,32 → 0,35 | 1,22 → 1,15 | 167 → 165 | 805 449 → 805 814 |

İdarəetmə səhifəsi və `editorial-store.js` heç bir adi səhifə ölçüsündə istənməyib. İzləmə modulu da klikdən əvvəl istənməyib. Yeni sosial SDK və şrift yoxdur. `app.js` LF 219 648 / 220 000 B, CSS 94 527 / 95 000 B. Əsas JavaScript-in gzip ölçüsü 74 540 → 74 108 B; CSS 21 348 → 21 576 B, məzmun qaydası 3 713 → 4 010 B, hesab ayarları 489 → 721 B. Yer üçün yalnız izahlı şərhlər qısaldılıb.

Nəticə: bu cütlərdə ümumi açılış balında geriləmə görünmür, yük 1,5 MB həddindən aşağıdır. Telefon LCP-si hələ təxminən 3 saniyədir; «gözqırpımında» hədəfə çatıldığı iddia edilmir. Sürət sahibin birinci prioriteti olaraq AGENTS və qırmızı xətlərdə qeyd olunub. Canlı nəticə sahibin yayımından sonra ayrıca yoxlanmalıdır.

Yoxlama: 218 JavaScript + 264 Python testi. Mobil brauzerdə dörd hesabın düzgün ünvanları, panelin açılıb-bağlanması; 320 px-də idarəetmə girişinin daşmaması yoxlanıb. Real sahib açarı ilə GitHub-a istehsal yazısı bu mühitdə mümkün olmayıb.
