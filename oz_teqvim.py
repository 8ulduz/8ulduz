"""8ulduz-un öz xəbərləri, faza 1: təqvim xəbərləri (sahib, 2026-11-10: «Bəli, başla»). Sayta hələ qoşulmayıb.

Şəbəkə sorğusu yoxdur. Cədvəllər bir dəfə rəsmi mənbələrdən yazılıb, futbol oyunları saytın öz data/futbol/ fayllarındandır.

1. «Bu gün nə günüdür» (hər gün 07:45, yalnız bir gün düşəndə). Azərbaycanın peşə bayramları və xüsusi günləri, BMT-nin
   beynəlxalq günləri və həftələri bir xəbərdə. Yalnız dövlət bayramı düşən gün dərc olunmur: onu «Bu gün tarixdə» xəbəri
   başlıqda verir. Anım günlərində də dərc olunmur.
2. «Bu həftə neçə iş günü var» (bazar ertəsi 08:00, yalnız həftədə 5-dən az iş günü olanda) və bayram istirahətindən
   əvvəlki son iş günü (08:00). Mənbə ƏƏSMN-in istehsalat təqvimidir. Rəsmi cədvəli olmayan ildə yalnız qanunla qeyri-iş
   günü olanlar (həftə sonu, sabit tarixli bayram) bilinir, qalanı təxmin edilmir. Bir istirahət, bir xəbər: əvvəlki iş günü
   xəbəri verilən istirahət bazar ertəsi təkrarlanmır, bazar ertəsinin xəbəri bütünlüklə verdiyi istirahət də.
3. Geri sayım: IV Avropa Oyunları (İstanbul, 2027) və XXXIV Yay Olimpiya Oyunları (Los-Anceles, 2028). Yalnız açılışa
   100, 50, 30, 10, 1 gün qalanda və açılış günü (11:00).
4. «Bu həftə nə gözlənilir» (bazar ertəsi 08:30): həftənin bayramları və günləri, Azərbaycan futbolunun oyunları Bakı vaxtı
   ilə. AMB və Statistika Komitəsinin buraxılışları yazılmır: onların tarixli rəsmi cədvəli tapılmadı (yalnız dövriliyi var).

Başqa modullar üçün: gun_adlari(gün) və qeyri_is_gunu(gün).
Sınaq: python oz_teqvim.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]
"""
import datetime
import json
import pathlib
import re
import sys

import oz_xeber as ox

BAKU = ox.BAKU
D = datetime.date
DAY = datetime.timedelta(days=1)
WEEKDAYS = ("bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə", "bazar")
TITLE_MAX = 110

# --- Cədvəllər (ildə bir dəfə yoxlanır) ---------------------------------------------------------------

# Dövlət bayramları, xüsusi və anım günləri: Əmək Məcəlləsinin 105-ci (bayramlar) və 106-cı (Ümumxalq Hüzn Günü)
# maddələri, ayrıca qərarlar (Xocalı, 31 Mart, Anım Günü, Dövlət Suverenliyi Günü). Adlar AZƏRTAC-ın yazdığı kimidir.
# (ay, gün, ad, iş günü hesab edilmir, anım günü)
DOVLET = (
    (1, 1, "Yeni il bayramı", True, False),
    (1, 2, "Yeni il bayramı", True, False),
    (1, 20, "Ümumxalq Hüzn Günü", True, True),
    (2, 26, "Xocalı soyqırımı günü", False, True),
    (3, 8, "Beynəlxalq Qadınlar Günü", True, False),
    (3, 31, "Azərbaycanlıların Soyqırımı Günü", False, True),
    (5, 9, "Faşizm üzərində Qələbə Günü", True, False),
    (5, 28, "Müstəqillik Günü", True, False),
    (6, 15, "Milli Qurtuluş Günü", True, False),
    (6, 26, "Silahlı Qüvvələr Günü", True, False),
    (9, 20, "Dövlət Suverenliyi Günü", False, False),
    (9, 27, "Anım Günü", False, True),
    (10, 18, "Müstəqilliyin Bərpası Günü", False, False),
    (11, 8, "Zəfər Günü", True, False),
    (11, 9, "Dövlət Bayrağı Günü", True, False),
    (11, 12, "Konstitusiya Günü", False, False),
    (11, 17, "Milli Dirçəliş Günü", False, False),
    (12, 31, "Dünya Azərbaycanlılarının Həmrəyliyi Günü", True, False),
)

# Novruz, Ramazan və Qurban bayramlarının günlərini hər il Nazirlər Kabineti elan edir, köçürülən istirahət günləri ƏƏSMN-in
# həmin il üçün istehsalat təqvimindədir. Yalnız rəsmi elan olunan il yazılır: başqa il üçün heç nə təxmin edilmir.
# 2026: Nazirlər Kabinetinin 2025-12-02 tarixli 362 nömrəli qərarı; ƏƏSMN Kollegiyasının 2025-12-11 tarixli qərarı
# («2026-cı ilin istehsalat təqvimi»: beşgünlük iş həftəsində 241 iş günü). Google-un bayram təqvimi 10 noyabrı səhv verir.
TEQVIM = {2026: "https://sosial.gov.az/az/faydali/istehsalat-teqvimi/2026-ci-ilin-istehsalat-teqvimi"}
TEQVIM_CREDIT = "Əmək və Əhalinin Sosial Müdafiəsi Nazirliyi"
IL_BAYRAM = {
    D(2026, 3, 20): ("Novruz bayramı", "Ramazan bayramı"),
    D(2026, 3, 21): ("Novruz bayramı", "Ramazan bayramı"),
    D(2026, 3, 22): ("Novruz bayramı",),
    D(2026, 3, 23): ("Novruz bayramı",),
    D(2026, 3, 24): ("Novruz bayramı",),
    D(2026, 5, 27): ("Qurban bayramı",),
    D(2026, 5, 28): ("Qurban bayramı",),
}
# Beşgünlük iş həftəsində köçürülən istirahət günləri və səbəbi (Əmək Məcəlləsi, 105-ci maddənin 5-ci və 6-cı hissələri).
_MART = "Novruz bayramının iki günü həftə sonuna düşüb, Ramazan bayramı isə Novruz bayramı ilə üst-üstə düşüb"
KOCURME = {
    D(2026, 3, 9): "8 Mart – Beynəlxalq Qadınlar Günü bazar gününə düşüb",
    D(2026, 3, 25): _MART,
    D(2026, 3, 26): _MART,
    D(2026, 3, 27): _MART,
    D(2026, 3, 30): _MART,
    D(2026, 5, 11): "9 May – Faşizm üzərində Qələbə Günü şənbə gününə düşüb",
    D(2026, 5, 29): "Qurban bayramının ikinci günü Müstəqillik Günü ilə üst-üstə düşüb",
    D(2026, 11, 10): "8 noyabr – Zəfər Günü bazar gününə düşüb, 9 noyabr isə Dövlət Bayrağı Günüdür",
}

# Peşə bayramları və xüsusi günlər. Hər tarix 2026-11-10-da rəsmi mənbə ilə tutuşdurulub: e-qanun.az-da qərarın adı və
# qüvvədə olması, president.az (turizm və metro günləri 2022-ci ildə 29 sentyabra və 6 noyabra keçirilib), AZƏRTAC və
# qurumların öz saytları. Tarixi təsdiqlənməyənlər (maşınqayırma, qaz təsərrüfatı, kənd təsərrüfatı, 2024-cü ildə təsis
# olunan xüsusi xidmətlər) yazılmayıb. Adında rəhbərlik vəzifəsi keçən gün də yoxdur. (ay, gün, ad, e-qanun.az sənədi)
PESE = (
    (1, 30, "gömrük işçilərinin peşə bayramı", 0),
    (2, 2, "Azərbaycan Gəncləri Günü", 0),
    (2, 11, "vergi xidməti işçilərinin peşə bayramı", 7374),
    (2, 14, "Hərbi Hava Qüvvələri Günü", 7788),
    (2, 22, "avtomobil yol işçilərinin peşə bayramı", 13428),
    (3, 5, "Bədən Tərbiyəsi və İdman Günü", 9646),
    (3, 10, "Milli Teatr Günü", 25345),
    (3, 10, "Qızıl Aypara Günü", 14024),
    (3, 12, "Daxili Qoşunlar Günü", 9223),
    (3, 19, "miqrasiya orqanları işçilərinin peşə bayramı", 19389),
    (3, 27, "Elm Günü", 0),
    (3, 28, "milli təhlükəsizlik orqanları işçilərinin peşə bayramı", 0),
    (4, 10, "İnşaatçılar Günü", 18832),
    (5, 23, "Ekologiya və Təbii Sərvətlər Nazirliyi işçilərinin peşə bayramı", 13350),
    (6, 2, "mülki aviasiya işçilərinin peşə bayramı", 11726),
    (6, 5, "Su Təsərrüfatı və Meliorasiya İşçiləri Günü", 0),
    (6, 17, "tibb işçilərinin peşə bayramı", 3581),
    (6, 18, "İnsan Hüquqları Günü", 0),
    (6, 23, "dövlət qulluqçularının peşə bayramı", 11737),
    (6, 25, "Dənizçi Günü", 27881),
    (7, 2, "Azərbaycan Polisi Günü", 3685),
    (7, 9, "diplomatik xidmət orqanları əməkdaşlarının peşə bayramı", 13798),
    (7, 22, "Milli Mətbuat və Jurnalistika Günü", 6573),
    (8, 1, "Azərbaycan Əlifbası və Azərbaycan Dili Günü", 2811),
    (8, 2, "Azərbaycan Kinosu Günü", 162),
    (8, 5, "Hərbi Dəniz Qüvvələri Günü", 0),
    (8, 18, "sərhəd mühafizə orqanları əməkdaşlarının peşə bayramı", 395),
    (9, 15, "Bilik Günü", 5475),
    (9, 18, "Milli Musiqi Günü", 9409),
    (9, 20, "Neftçilər Günü", 2817),
    (9, 29, "Turizm İşçiləri Günü", 0),
    (10, 1, "prokurorluq işçilərinin peşə bayramı", 0),
    (10, 10, "yanğınsöndürənlərin peşə bayramı", 1160),
    (10, 13, "dəmir yolu işçilərinin peşə bayramı", 10747),
    (10, 20, "Energetiklər Günü", 5786),
    (11, 6, "Azərbaycan Televiziyası və Radiosu Günü", 7079),
    (11, 6, "Bakı metropoliteni işçilərinin peşə bayramı", 12080),
    (11, 22, "ədliyyə işçilərinin peşə bayramı", 387),
    (12, 6, "rabitə və informasiya texnologiyaları sahəsi işçilərinin peşə bayramı", 12622),
    (12, 16, "Fövqəladə Hallar Nazirliyi işçilərinin peşə bayramı", 12633),
    (12, 17, "Müdafiə Sənayesi Nazirliyi işçilərinin peşə bayramı", 18664),
    (12, 28, "Vəkil Günü", 43958),
    (12, 29, "«ASAN xidmət» işçilərinin peşə bayramı", 0),
)
EQANUN = "https://e-qanun.az/framework/{}"

# BMT-nin beynəlxalq günləri: https://www.un.org/en/observances/list-days-weeks (2026-11-10 oxunub, ildə bir dəfə
# yenilənir). Səhifə hər günü köhnə ilin tarixi ilə saxlayır, ona görə dəyişən günlər qayda ilə yazılıb: (n, həftənin günü),
# Python-un sayı ilə (0 = bazar ertəsi). Yazılmayanlar: yerli siyasi həssas günlər (2 noyabr jurnalistlər, 3 may mətbuat
# azadlığı, 29 noyabr Fələstin, işgəncə qurbanları, birtərəfli məcburi tədbirlər, müstəmləkəçilik, müstəqil olmayan ərazilər),
# BMT dillərinin günləri, tarixi ildən-ilə dəyişən ÜST/UNEP/İMO günləri, Azərbaycan dövlət bayramı ilə eyni olan
# (8 Mart, BMT-nin dövlət qulluğu və dənizçi günü), yerli marağı az olan dar mövzular. (ay, gün, ad, sənəd)
BMT = (
    (1, 4, "Ümumdünya Brayl Günü", "A/RES/73/161"),
    (1, 24, "Beynəlxalq Təhsil Günü", "A/RES/73/25"),
    (1, 26, "Beynəlxalq Təmiz Enerji Günü", "A/RES/77/327"),
    (1, 27, "Holokost Qurbanlarını Anma Beynəlxalq Günü", "A/RES/60/7"),
    (1, 28, "Beynəlxalq Dinc Birgəyaşayış Günü", "A/RES/79/269"),
    (2, 2, "Ümumdünya Su-Bataqlıq Əraziləri Günü", "A/RES/75/317"),
    (2, 4, "Beynəlxalq İnsan Qardaşlığı Günü", "A/RES/75/200"),
    (2, 10, "Ümumdünya Paxlalılar Günü", "A/RES/73/251"),
    (2, 11, "Elmdə Qadınlar və Qızların Beynəlxalq Günü", "A/RES/70/212"),
    (2, 12, "Zorakı Ekstremizmin Qarşısının Alınması Beynəlxalq Günü", "A/RES/77/243"),
    (2, 13, "Ümumdünya Radio Günü", "A/RES/67/124"),
    (2, 17, "Qlobal Turizm Dayanıqlılığı Günü", "A/RES/77/269"),
    (2, 20, "Ümumdünya Sosial Ədalət Günü", "A/RES/62/10"),
    (2, 21, "Beynəlxalq Ana Dili Günü", "A/RES/56/262"),
    (3, 1, "Sıfır Ayrı-seçkilik Günü", ""),
    (3, 3, "Ümumdünya Vəhşi Təbiət Günü", "A/RES/68/205"),
    (3, 5, "Tərksilah və Silahların Yayılmaması Barədə Maarifləndirmə Beynəlxalq Günü", "A/RES/77/51"),
    (3, 10, "Qadın Hakimlərin Beynəlxalq Günü", "A/RES/75/274"),
    (3, 15, "İslamofobiya ilə Mübarizə Beynəlxalq Günü", "A/RES/76/254"),
    (3, 20, "Beynəlxalq Xoşbəxtlik Günü", "A/RES/66/281"),
    (3, 21, "Beynəlxalq Novruz Günü", "A/RES/64/253"),
    (3, 21, "Ümumdünya Poeziya Günü", "UNESCO 30 C/Resolution 29"),
    (3, 21, "Beynəlxalq Meşə Günü", "A/RES/67/200"),
    (3, 21, "Ümumdünya Buzlaqlar Günü", "A/RES/77/158"),
    (3, 21, "İrqi Ayrı-seçkiliyin Aradan Qaldırılması Uğrunda Beynəlxalq Mübarizə Günü", "A/RES/2142 (XXI)"),
    (3, 21, "Ümumdünya Daun Sindromu Günü", "A/RES/66/149"),
    (3, 22, "Ümumdünya Su Günü", "A/RES/47/193"),
    (3, 23, "Ümumdünya Meteorologiya Günü", ""),
    (3, 24, "Ümumdünya Vərəmlə Mübarizə Günü", ""),
    (3, 25, "Köləlik və Transatlantik Qul Ticarəti Qurbanlarını Anma Beynəlxalq Günü", "A/RES/62/122"),
    (3, 30, "Beynəlxalq Sıfır Tullantı Günü", "A/RES/77/161"),
    (4, 2, "Ümumdünya Autizm Barədə Maarifləndirmə Günü", "A/RES/62/139"),
    (4, 4, "Mina Təhlükəsi Barədə Maarifləndirmə və Minatəmizləməyə Yardım Beynəlxalq Günü", "A/RES/60/97"),
    (4, 5, "Beynəlxalq Vicdan Günü", "A/RES/73/329"),
    (4, 6, "İnkişaf və Sülh Naminə Beynəlxalq İdman Günü", "A/RES/67/296"),
    (4, 7, "Ümumdünya Səhiyyə Günü", ""),
    (4, 12, "İnsanın Kosmosa Uçuşunun Beynəlxalq Günü", "A/RES/65/271"),
    (4, 21, "Ümumdünya Yaradıcılıq və İnnovasiya Günü", "A/RES/71/284"),
    (4, 22, "Beynəlxalq Yer Ana Günü", "A/RES/63/278"),
    (4, 23, "Ümumdünya Kitab və Müəllif Hüquqları Günü", "UNESCO 28 C/Resolution 3.18"),
    (4, 24, "Sülh Naminə Multilateralizm və Diplomatiya Beynəlxalq Günü", "A/RES/73/127"),
    (4, 25, "Ümumdünya Malyariya ilə Mübarizə Günü", ""),
    (4, 26, "Çernobıl Fəlakətini Anma Beynəlxalq Günü", "A/RES/71/125"),
    (4, 26, "Ümumdünya Əqli Mülkiyyət Günü", ""),
    (4, 28, "Ümumdünya Əməyin Təhlükəsizliyi və Sağlamlığı Günü", ""),
    (4, 29, "Zəlzələ Qurbanlarını Anma Beynəlxalq Günü", "A/RES/79/285"),
    (4, 30, "Beynəlxalq Caz Günü", "UNESCO 36 C/Resolution 39"),
    (5, 12, "Beynəlxalq Bitki Sağlamlığı Günü", "A/RES/76/256"),
    (5, 15, "Beynəlxalq Ailə Günü", "A/RES/47/237"),
    (5, 16, "Sülh İçində Birgə Yaşamaq Beynəlxalq Günü", "A/RES/72/130"),
    (5, 16, "Beynəlxalq İşıq Günü", "UNESCO 39 C/Resolution 16"),
    (5, 17, "Ümumdünya Telekommunikasiya və İnformasiya Cəmiyyəti Günü", "A/RES/60/252"),
    (5, 19, "Ümumdünya Fair Play Günü", "A/RES/78/310"),
    (5, 20, "Ümumdünya Arı Günü", "A/RES/72/211"),
    (5, 21, "Beynəlxalq Çay Günü", "A/RES/74/241"),
    (5, 21, "Dialoq və İnkişaf Naminə Ümumdünya Mədəni Müxtəliflik Günü", "A/RES/57/249"),
    (5, 22, "Beynəlxalq Bioloji Müxtəliflik Günü", "A/RES/55/201"),
    (5, 25, "Ümumdünya Futbol Günü", "A/RES/78/281"),
    (5, 29, "BMT Sülhməramlılarının Beynəlxalq Günü", "A/RES/57/129"),
    (5, 30, "Beynəlxalq Kartof Günü", "A/RES/78/123"),
    (5, 31, "Ümumdünya Tütünsüz Gün", ""),
    (6, 1, "Ümumdünya Valideynlər Günü", "A/RES/66/292"),
    (6, 3, "Ümumdünya Velosiped Günü", "A/RES/72/272"),
    (6, 4, "Təcavüzün Qurbanı Olan Günahsız Uşaqların Beynəlxalq Günü", "A/RES/ES-7/8"),
    (6, 5, "Ümumdünya Ətraf Mühit Günü", "A/RES/2994 (XXVII)"),
    (6, 7, "Ümumdünya Qida Təhlükəsizliyi Günü", "A/RES/73/250"),
    (6, 8, "Ümumdünya Okeanlar Günü", "A/RES/63/111"),
    (6, 10, "Sivilizasiyalararası Dialoq Beynəlxalq Günü", "A/RES/78/286"),
    (6, 11, "Beynəlxalq Oyun Günü", "A/RES/78/268"),
    (6, 12, "Uşaq Əməyinə Qarşı Ümumdünya Mübarizə Günü", ""),
    (6, 14, "Ümumdünya Qanvermə Günü", ""),
    (6, 17, "Səhralaşma və Quraqlıqla Mübarizə Ümumdünya Günü", "A/RES/49/115"),
    (6, 18, "Nifrət Nitqinə Qarşı Mübarizə Beynəlxalq Günü", "A/RES/75/309"),
    (6, 19, "Münaqişələrdə Cinsi Zorakılığın Aradan Qaldırılması Beynəlxalq Günü", "A/RES/69/293"),
    (6, 20, "Ümumdünya Qaçqınlar Günü", "A/RES/55/76"),
    (6, 21, "Beynəlxalq Yoqa Günü", "A/RES/69/131"),
    (6, 23, "Beynəlxalq Dul Qadınlar Günü", "A/RES/65/189"),
    (6, 24, "Diplomatiyada Qadınların Beynəlxalq Günü", "A/RES/76/269"),
    (6, 26, "Narkomaniya və Narkotiklərin Qanunsuz Dövriyyəsinə Qarşı Beynəlxalq Mübarizə Günü", "A/RES/42/112"),
    (6, 27, "Mikro, Kiçik və Orta Sahibkarlıq Günü", "A/RES/71/279"),
    (6, 30, "Beynəlxalq Asteroid Günü", "A/RES/71/90"),
    (6, 30, "Beynəlxalq Parlamentarizm Günü", "A/RES/72/278"),
    (7, (1, 5), "Beynəlxalq Kooperativlər Günü", "A/RES/47/90"),  # iyulun ilk şənbəsi
    (7, 6, "Ümumdünya Kənd İnkişafı Günü", "A/RES/78/326"),
    (7, 11, "Ümumdünya Əhali Günü", "A/RES/45/216"),
    (7, 11, "Ümumdünya At Günü", "A/RES/79/291"),
    (7, 12, "Qum və Toz Fırtınaları ilə Mübarizə Beynəlxalq Günü", "A/RES/77/294"),
    (7, 15, "Ümumdünya Gənclərin Bacarıqları Günü", "A/RES/69/145"),
    (7, 18, "Nelson Mandela Beynəlxalq Günü", "A/RES/64/13"),
    (7, 20, "Ümumdünya Şahmat Günü", "A/RES/74/22"),
    (7, 20, "Beynəlxalq Ay Günü", "A/RES/76/76"),
    (7, 25, "Suda Boğulmanın Qarşısının Alınması Ümumdünya Günü", "A/RES/75/273"),
    (7, 28, "Ümumdünya Hepatitlə Mübarizə Günü", ""),
    (7, 30, "Beynəlxalq Dostluq Günü", "A/RES/65/275"),
    (7, 30, "İnsan Alverinə Qarşı Ümumdünya Mübarizə Günü", "A/RES/68/192"),
    (8, 12, "Beynəlxalq Gənclər Günü", "A/RES/54/120"),
    (8, 19, "Ümumdünya Humanitar Yardım Günü", "A/RES/63/139"),
    (8, 21, "Terror Qurbanlarını Anma və Onlara Ehtiram Beynəlxalq Günü", "A/RES/72/165"),
    (8, 22, "Din və ya Etiqad Zəminində Zorakılıq Qurbanlarını Anma Beynəlxalq Günü", "A/RES/73/296"),
    (8, 29, "Nüvə Sınaqlarına Qarşı Beynəlxalq Mübarizə Günü", "A/RES/64/35"),
    (8, 30, "Zorla Yoxa Çıxarılmış Şəxslərin Beynəlxalq Günü", "A/RES/65/209"),
    (9, 5, "Beynəlxalq Xeyriyyəçilik Günü", "A/RES/67/105"),
    (9, 7, "Mavi Səma üçün Təmiz Hava Beynəlxalq Günü", "A/RES/74/212"),
    (9, 7, "Polis Əməkdaşlığının Beynəlxalq Günü", "A/RES/77/241"),
    (9, 8, "Beynəlxalq Savadlılıq Günü", "UNESCO 14 C/Resolution 1.441"),
    (9, 9, "Təhsilin Hücumlardan Qorunması Beynəlxalq Günü", "A/RES/74/275"),
    (9, 12, "BMT-nin Cənub-Cənub Əməkdaşlığı Günü", "A/RES/58/220"),
    (9, 15, "Beynəlxalq Demokratiya Günü", "A/RES/62/7"),
    (9, 16, "Ozon Qatının Qorunması Beynəlxalq Günü", "A/RES/49/114"),
    (9, 17, "Ümumdünya Pasiyent Təhlükəsizliyi Günü", ""),
    (9, 18, "Beynəlxalq Bərabər Əmək Haqqı Günü", "A/RES/74/142"),
    (9, 20, "Ümumdünya Təmizlik Günü", "A/RES/78/122"),
    (9, 21, "Beynəlxalq Sülh Günü", "A/RES/36/67"),
    (9, 23, "Beynəlxalq İşarə Dilləri Günü", "A/RES/72/161"),
    (9, 26, "Nüvə Silahlarının Tamamilə Ləğvi Uğrunda Beynəlxalq Mübarizə Günü", "A/RES/68/32"),
    (9, 27, "Ümumdünya Turizm Günü", ""),
    (9, 28, "İnformasiyaya Ümumi Çıxış Beynəlxalq Günü", "A/RES/74/5"),
    (9, 29, "Ərzaq İtkisi və Tullantıları Barədə Maarifləndirmə Beynəlxalq Günü", "A/RES/74/209"),
    (9, 30, "Beynəlxalq Tərcümə Günü", "A/RES/71/288"),
    (10, 1, "Beynəlxalq Yaşlılar Günü", "A/RES/45/106"),
    (10, 1, "Beynəlxalq Qəhvə Günü", "A/RES/80/248"),
    (10, 2, "Beynəlxalq Zorakılıqsızlıq Günü", "A/RES/61/271"),
    (10, (1, 0), "Ümumdünya Məskunlaşma Günü", "A/RES/40/202 A"),  # oktyabrın ilk bazar ertəsi
    (10, 5, "Ümumdünya Müəllimlər Günü", ""),
    (10, 7, "Ümumdünya Pambıq Günü", "A/RES/75/318"),
    (10, 9, "Ümumdünya Poçt Günü", ""),
    (10, 10, "Ümumdünya Psixi Sağlamlıq Günü", ""),
    (10, 11, "Beynəlxalq Qız Uşaqları Günü", "A/RES/66/170"),
    (10, 13, "Fəlakət Risklərinin Azaldılması Beynəlxalq Günü", "A/RES/64/200"),
    (10, 15, "Kənd Qadınlarının Beynəlxalq Günü", "A/RES/62/136"),
    (10, 16, "Ümumdünya Ərzaq Günü", "A/RES/35/70"),
    (10, 17, "Yoxsulluğun Aradan Qaldırılması Uğrunda Beynəlxalq Mübarizə Günü", "A/RES/47/196"),
    (10, 24, "BMT Günü", "A/RES/168 (II)"),
    (10, 27, "Ümumdünya Audiovizual İrs Günü", "UNESCO 33 C/Resolution 5"),
    (10, 29, "Beynəlxalq Qayğı və Dəstək Günü", "A/RES/77/317"),
    (10, 31, "Ümumdünya Şəhərlər Günü", "A/RES/68/239"),
    (11, 5, "Ümumdünya Sunami Barədə Maarifləndirmə Günü", "A/RES/70/203"),
    (11, 6, "Müharibə və Silahlı Münaqişələrdə Ətraf Mühitin İstismarının Qarşısının Alınması Beynəlxalq Günü",
     "A/RES/56/4"),
    (11, 10, "Sülh və İnkişaf Naminə Ümumdünya Elm Günü", "UNESCO 31 C/Resolution 20"),
    (11, 14, "Ümumdünya Diabet Günü", "A/RES/61/225"),
    (11, (3, 6), "Yol-Nəqliyyat Hadisələri Qurbanlarını Anma Ümumdünya Günü", "A/RES/60/5"),  # noyabrın 3-cü bazarı
    (11, 15, "Transmilli Mütəşəkkil Cinayətkarlığa Qarşı Mübarizə Beynəlxalq Günü", "A/RES/78/267"),
    (11, 16, "Beynəlxalq Tolerantlıq Günü", "UNESCO 28 C/Resolution 5.61"),
    (11, (3, 3), "Ümumdünya Fəlsəfə Günü", "UNESCO 33 C/Resolution 37"),  # noyabrın 3-cü cümə axşamı
    (11, 19, "Ümumdünya Tualet Günü", "A/RES/67/291"),
    (11, 20, "Ümumdünya Uşaq Günü", "A/RES/836(IX)"),
    (11, 21, "Ümumdünya Televiziya Günü", "A/RES/51/205"),
    (11, 25, "Qadınlara Qarşı Zorakılığın Aradan Qaldırılması Beynəlxalq Günü", "A/RES/54/134"),
    (11, 26, "Ümumdünya Davamlı Nəqliyyat Günü", "A/RES/77/286"),
    (11, 27, "Uşaq, Erkən və Məcburi Nikahların Aradan Qaldırılması Beynəlxalq Günü", "A/RES/80/309"),
    (11, 30, "Kimyəvi Müharibənin Bütün Qurbanlarını Anma Günü", ""),
    (12, 1, "Ümumdünya QİÇS-lə Mübarizə Günü", ""),
    (12, 2, "Köləliyin Ləğvi Uğrunda Beynəlxalq Mübarizə Günü", "A/RES/317(IV)"),
    (12, 3, "Beynəlxalq Əlilliyi Olan Şəxslər Günü", "A/RES/47/3"),
    (12, 4, "Beynəlxalq Banklar Günü", "A/RES/74/245"),
    (12, 5, "İqtisadi və Sosial İnkişaf Naminə Beynəlxalq Könüllülər Günü", "A/RES/40/212"),
    (12, 5, "Ümumdünya Torpaq Günü", "A/RES/68/232"),
    (12, 7, "Beynəlxalq Mülki Aviasiya Günü", "A/RES/51/33"),
    (12, 9, "Beynəlxalq Korrupsiyaya Qarşı Mübarizə Günü", "A/RES/58/4"),
    (12, 9, "Soyqırımı Cinayəti Qurbanlarını Anma və Bu Cinayətin Qarşısının Alınması Beynəlxalq Günü", "A/RES/69/323"),
    (12, 10, "Ümumdünya İnsan Hüquqları Günü", "A/RES/423 (V)"),
    (12, 11, "Beynəlxalq Dağlar Günü", "A/RES/57/245"),
    (12, 12, "Beynəlxalq Neytrallıq Günü", "A/RES/71/275"),
    (12, 12, "Beynəlxalq Ümumi Səhiyyə Əhatəsi Günü", "A/RES/72/138"),
    (12, 15, "Dünya Türk Dili Ailəsi Günü", "UNESCO 43 C/57"),
    (12, 18, "Beynəlxalq Miqrantlar Günü", "A/RES/55/93"),
    (12, 20, "Beynəlxalq İnsan Həmrəyliyi Günü", "A/RES/60/209"),
    (12, 21, "Ümumdünya Basketbol Günü", "A/RES/77/324"),
    (12, 21, "Ümumdünya Meditasiya Günü", "A/RES/79/137"),
    (12, 27, "Epidemiyalara Hazırlıq Beynəlxalq Günü", "A/RES/75/27"),
)
# BMT-nin həftələri: (ay, gün, son ay, son gün, ad, sənəd). Həftə yalnız ilk günündə ayrıca xəbər səbəbidir.
BMT_HEFTE = (
    (2, 1, 2, 7, "Ümumdünya Dinlərarası Harmoniya Həftəsi", "A/RES/65/5"),
    (4, 24, 4, 30, "Ümumdünya İmmunizasiya Həftəsi", ""),
    (8, 1, 8, 7, "Ümumdünya Ana Südü ilə Qidalandırma Həftəsi", ""),
    (10, 4, 10, 10, "Ümumdünya Kosmos Həftəsi", "A/RES/54/68"),
    (10, 24, 10, 31, "Qlobal Media və İnformasiya Savadlılığı Həftəsi", "A/RES/75/267"),
    (11, 9, 11, 15, "Beynəlxalq Elm və Sülh Həftəsi", "A/RES/43/61"),
    (11, 18, 11, 24, "Antimikrob Müqavimət Barədə Ümumdünya Maarifləndirmə Həftəsi", ""),
)
# BMT-nin günü həmin gün Azərbaycanın dövlət bayramı ilə eyni hadisədirsə, ayrıca yazılmır (bayramı «Bu gün tarixdə» verir).
BMT_EYNI = {"Beynəlxalq Novruz Günü": "Novruz bayramı"}
BMT_URL = "https://www.un.org/en/observances/list-days-weeks"
BMT_CREDIT = "Birləşmiş Millətlər Təşkilatı"

# Oyunların rəsmi tarixləri: Avropa Olimpiya Komitələri (sporteurope.org, «Istanbul 2027 16-27 June 2027») və LA28
# (la28.org, «Olympic Games Dates: July 14–30, 2028»). Milli Olimpiya Komitəsinin LA səhifəsindəki tarix köhnədir.
OYUNLAR = (
    {"id": "istanbul-2027", "ad": "IV Avropa Oyunları", "start": D(2027, 6, 16), "end": D(2027, 6, 27),
     "yer": "Türkiyənin İstanbul şəhərində", "seher": "İstanbul", "credit": "Avropa Olimpiya Komitələri",
     "link": "https://sporteurope.org/istanbul-2027/", "elave": ""},
    {"id": "los-anceles-2028", "ad": "XXXIV Yay Olimpiya Oyunları", "start": D(2028, 7, 14), "end": D(2028, 7, 30),
     "yer": "ABŞ-ın Los-Anceles şəhərində", "seher": "Los-Anceles", "credit": "LA28 Təşkilat Komitəsi",
     "link": "https://la28.org/en.html", "elave": "Yay Paralimpiya Oyunları 15–27 avqust 2028-ci il tarixlərində keçiriləcək."},
)
MERHELE = (100, 50, 30, 10, 1, 0)

# Futbol: saytın öz faylları. Azərbaycan klubu = Premyer Liqanın komandası; milli komanda = «azerbaycan».
LIQALAR = (("premyer-liqa", "Premyer Liqa"), ("i-liqa", "I Liqa"), ("kubok", "Azərbaycan Kuboku"))
# UEFA-nın Çempionlar, Avropa və Konfrans liqaları. avroliqa.json basketbolun Avroliqasıdır, futbol deyil.
AVROKUBOKLAR = ("cl", "al", "kl")
_ORDER = {"milli": 0, "avro": 1, "premyer-liqa": 2, "i-liqa": 3, "kubok": 4}


# --- Yazı köməkçiləri ---------------------------------------------------------------------------------

def _cop(text):
    """Xəbərlik şəkilçisi: «Günü» -> «Günüdür», «bayramı» -> «bayramıdır», «Gün» -> «Gündür», «noyabr» -> «noyabrdır»."""
    return text + ox._four(text, ("dır", "dir", "dur", "dür"))


def _join(names):
    """«A», «A və B», «A, B və C»."""
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " və " + names[-1]


def _range(a, b):
    """«9–15 noyabr», «30 noyabr – 6 dekabr», «31 dekabr – 4 yanvar»; il yalnız uzun aralıqda: «1 dekabr 2026 – 1 mart 2027».
    Qısa aralıqda il yazılmır: «31 dekabr 2026 – 4 yanvar 2027 5 gün» kimi ədədlər yan-yana düşməsin."""
    if a == b:
        return ox.day_text(a)
    if (a.year, a.month) == (b.year, b.month):
        return f"{a.day}–{b.day} {ox.MONTHS[a.month - 1]}"
    if a.year == b.year or (b - a).days < 60:
        return f"{ox.day_text(a)} – {ox.day_text(b)}"
    return f"{ox.day_text(a)} {a.year} – {ox.day_text(b)} {b.year}"


def _loc(text):
    """Ay adı ilə bitən tarixin yerlik halı: «20–22 noyabrda», «10 apreldə»."""
    return text + ("də" if text.endswith("aprel") else "da")


def _days_text(days):
    """Günlərin siyahısı: «9 noyabr», «9 və 10 noyabr», «11, 12 və 13 noyabr», «23–27 mart», «31 dekabr və 1 yanvar»."""
    days = sorted(days)
    if not days:
        return ""
    if len(days) >= 4 and (days[-1] - days[0]).days == len(days) - 1:
        return _range(days[0], days[-1])
    if all((d.year, d.month) == (days[0].year, days[0].month) for d in days):
        return f"{_join([str(d.day) for d in days])} {ox.MONTHS[days[0].month - 1]}"
    return _join([ox.day_text(d) for d in days])


def _gunleri(n):
    return "günüdür" if n == 1 else "günləridir"


def _ref(ref):
    """Sənədin qısa yazılışı: «A/RES/61/225», «UNESCO, 31 C/Resolution 20»."""
    return "UNESCO, " + ref[7:] if ref.startswith("UNESCO ") else ref


def _now(now):
    if now is None:
        return datetime.datetime.now(BAKU)
    if now.tzinfo is None:
        return now.replace(tzinfo=BAKU)
    return now.astimezone(BAKU)


def _date(d):
    return d.astimezone(BAKU).date() if isinstance(d, datetime.datetime) else d


# --- Günün qeyd olunan günləri ------------------------------------------------------------------------

def _nth_weekday(year, month, nth, weekday):
    """Ayın n-ci həftə günü: (2026, 11, 3, 3) -> 19 noyabr 2026 (üçüncü cümə axşamı)."""
    d = D(year, month, 1)
    d += datetime.timedelta(days=(weekday - d.weekday()) % 7)
    return d + datetime.timedelta(weeks=nth - 1)


def _on(d, month, day):
    if month != d.month:
        return False
    if isinstance(day, tuple):
        return _nth_weekday(d.year, month, day[0], day[1]) == d
    return day == d.day


def _entries(d):
    """Günün qeyd olunan günləri. Sıra: dövlət (və həmin ilin dini bayramları), peşə, BMT günü, BMT həftəsi."""
    d = _date(d)
    out = []
    for month, day, name, off, anim in DOVLET:
        if _on(d, month, day):
            out.append({"kind": "dovlet", "name": name, "off": off, "anim": anim})
    for name in IL_BAYRAM.get(d, ()):
        out.append({"kind": "dovlet", "name": name, "off": True, "anim": False})
    for month, day, name, doc in PESE:
        if _on(d, month, day):
            out.append({"kind": "pese", "name": name, "link": EQANUN.format(doc) if doc else "https://e-qanun.az/"})
    for month, day, name, ref in BMT:
        if _on(d, month, day):
            out.append({"kind": "bmt", "name": name, "ref": ref})
    for m1, d1, m2, d2, name, ref in BMT_HEFTE:
        start, end = D(d.year, m1, d1), D(d.year, m2, d2)
        if start <= d <= end:
            out.append({"kind": "hefte", "name": name, "ref": ref, "start": start, "end": end, "first": d == start})
    return out


def _bmt_same(ents):
    """Azərbaycanın həmin gün qeyd olunan dövlət bayramı ilə eyni hadisə olan BMT günləri (2026-da Novruz)."""
    state = {e["name"] for e in ents if e["kind"] == "dovlet"}
    return {e["name"] for e in ents if e["kind"] == "bmt" and BMT_EYNI.get(e["name"]) in state}


def gun_adlari(d):
    """Günün qeyd olunan günlərinin adları (Azərbaycan dilində): dövlət bayramları (Novruz, Ramazan və Qurban yalnız rəsmi
    elan olunan il üçün), peşə bayramları, BMT-nin beynəlxalq günləri; BMT həftəsi yalnız başladığı gün. Bayramla eyni olan
    BMT günü (Beynəlxalq Novruz Günü) bayram elan olunan ildə təkrar yazılmır."""
    ents = _entries(d)
    same = _bmt_same(ents)
    out = []
    for e in ents:
        if (e["kind"] != "hefte" or e["first"]) and e["name"] not in out and e["name"] not in same:
            out.append(e["name"])
    return out


def _qanunla_qeyri_is(d):
    """Hər il qanunla iş günü olmayan gün: şənbə, bazar və ya iş günü hesab edilməyən sabit tarixli bayram (Əmək Məcəlləsi)."""
    return d.weekday() >= 5 or any(off and _on(d, month, day) for month, day, _, off, _ in DOVLET)


def qeyri_is_gunu(d):
    """Beşgünlük iş həftəsində iş günü deyilmi: həftə sonu, iş günü hesab edilməyən bayram və ya köçürülən istirahət günü.
    Rəsmi təqvimi (TEQVIM) olmayan ildə qanunla qeyri-iş günü olan gün (həftə sonu, sabit tarixli bayram) üçün True, qalan
    günlər üçün None qaytarır: o ilin Novruz, Ramazan, Qurban günləri və köçürmələri bilinmir, iş günü təxmin edilmir."""
    d = _date(d)
    if _qanunla_qeyri_is(d):
        return True
    if d.year not in TEQVIM:
        return None
    return d in KOCURME or d in IL_BAYRAM


def _off_reason(d):
    """Həftə içindəki qeyri-iş gününün səbəbi: ("bayram", adlar) və ya ("kocurme", səbəb)."""
    if d in KOCURME:
        return ("kocurme", KOCURME[d])
    names = [e["name"] for e in _entries(d) if e["kind"] == "dovlet" and e["off"]]
    return ("bayram", tuple(dict.fromkeys(names)))


def _plain_weekend(d):
    """Bayramı olmayan adi şənbə və ya bazar."""
    return d.weekday() >= 5 and d not in IL_BAYRAM and not any(e["off"] for e in _entries(d) if e["kind"] == "dovlet")


def _reason_lines(days):
    """Qeyri-iş günlərinin səbəbi, eyni səbəbli günlər bir cümlədə: «10 noyabr istirahət günüdür: ...». Aralarında yalnız adi
    həftə sonu olan eyni səbəbli günlər də birləşir: «25, 26, 27 və 30 mart istirahət günləridir: ...»."""
    groups = []
    for d in days:
        if _plain_weekend(d):
            continue
        key = _off_reason(d)
        last = groups[-1][1][-1] if groups else None
        if last and groups[-1][0] == key and all(_plain_weekend(last + DAY * i) for i in range(1, (d - last).days)):
            groups[-1][1].append(d)
        else:
            groups.append((key, [d]))
    lines = []
    for (kind, what), group in groups:
        if kind == "kocurme":
            lines.append(f"{_days_text(group)} istirahət {_gunleri(len(group))}: {what}.")
        else:
            lines.append(f"{_days_text(group)} {_cop(_join(what))}.")
    return lines


# --- 1. «Bu gün nə günüdür» ---------------------------------------------------------------------------

def _gun_title(e):
    if e["kind"] == "hefte":
        return f"Bu gün {e['name']} başlayır"
    if e["kind"] == "pese" and not e["name"].startswith("Azərbaycan"):
        return f"Bu gün Azərbaycanda {_cop(e['name'])}"
    return f"Bu gün {_cop(e['name'])}"


def _gun_lead(e, day):
    when = ox.day_text(day)
    if e["kind"] in ("pese", "dovlet"):
        where = "" if e["name"].startswith("Azərbaycan") else "Azərbaycanda "
        return f"{when} {where}{e['name']} kimi qeyd olunur."
    ref = f" ({_ref(e['ref'])})" if e.get("ref") else ""
    if e["kind"] == "hefte":
        return f"BMT-nin beynəlxalq günlər siyahısına görə, {_range(e['start'], e['end'])} {_cop(e['name'])}{ref}."
    return f"BMT-nin beynəlxalq günlər siyahısına görə, {when} {_cop(e['name'])}{ref}."


def gun_item(day):
    """«Bu gün nə günüdür». Qaytarır (xəbər və ya None, səbəb)."""
    day = _date(day)
    ents = _entries(day)
    dov = [e for e in ents if e["kind"] == "dovlet"]
    pese = [e for e in ents if e["kind"] == "pese"]
    same = _bmt_same(ents)
    bmt = [e for e in ents if e["kind"] == "bmt" and e["name"] not in same]
    new_weeks = [e for e in ents if e["kind"] == "hefte" and e["first"]]
    old_weeks = [e for e in ents if e["kind"] == "hefte" and not e["first"]]
    pool = pese + bmt + new_weeks
    if not pool and not dov:
        return None, "bu gün təqvimdə qeyd olunan gün yoxdur"
    main = next((e for e in pool if len(_gun_title(e)) <= TITLE_MAX), None) or (dov[0] if dov else pool[0])
    az_rest = [e["name"] for e in pese + dov if e is not main]
    bmt_rest = [e["name"] for e in bmt if e is not main]
    lead = _gun_lead(main, day)
    if az_rest:
        names = _cop(_join(dict.fromkeys(az_rest)))
        lead += f" Bu gün həm də {names}." if main["kind"] in ("pese", "dovlet") else f" Azərbaycanda bu gün {names}."
    body = []
    if bmt_rest:
        intro = "BMT-nin siyahısında" if main["kind"] in ("bmt", "hefte") else "BMT-nin beynəlxalq günlər siyahısına görə,"
        body.append(f"{intro} bu gün həm də {_join(bmt_rest)} qeyd olunur.")
    for e in new_weeks:
        if e is not main:
            body.append(f"{_range(e['start'], e['end'])} BMT-nin siyahısında {_cop(e['name'])}.")
    for e in old_weeks:
        body.append(f"{_range(e['start'], e['end'])} BMT-nin siyahısında {_cop(e['name'])}.")
    if main["kind"] in ("bmt", "hefte"):
        credit, link = BMT_CREDIT, BMT_URL
    else:
        credit, link = "e-qanun.az", main.get("link") or "https://e-qanun.az/"
    item = {"kind": "gun", "key": f"gun-{day.isoformat()}", "title": _gun_title(main), "lead": lead, "body": body,
            "credit": credit, "link": link, "topic": "təqvim", "slot": "07:45", "worth": True}
    anim = [e["name"] for e in dov if e["anim"]]
    if anim:
        item.update(worth=False, why=f"{_join(anim)}: anım günündə təqvim xəbəri dərc olunmur")
    elif not pool:
        item.update(worth=False, why="yalnız dövlət bayramıdır: onu «Bu gün tarixdə» xəbəri başlıqda verir")
    return item, item.get("why", "")


# --- 2. İş günləri və bayram istirahəti ---------------------------------------------------------------

def _unknown(days):
    years = sorted({d.year for d in days if qeyri_is_gunu(d) is None})
    return f"{ox.ordinal(years[0])} il üçün rəsmi istehsalat təqvimi hələ yoxdur: iş günləri təxmin edilmir" if years else ""


def _src(*years):
    """«... 2026-cı ilin istehsalat təqviminə görə»; iki ilə düşən istirahətdə «2026-cı və 2027-ci illərin ... təqvimlərinə görə»."""
    years = sorted(set(years))
    if len(years) == 1:
        return f"{TEQVIM_CREDIT}nin təsdiq etdiyi {ox.ordinal(years[0])} ilin istehsalat təqviminə görə"
    return f"{TEQVIM_CREDIT}nin təsdiq etdiyi {' və '.join(ox.ordinal(y) for y in years)} illərin istehsalat təqvimlərinə görə"


def _special(d):
    """Bayram istirahətini yaradan gün: köçürülən istirahət günü və ya iş günü hesab edilməyən bayram. Ümumxalq Hüzn Günü
    (anım günü) iş günü deyil, amma bayram istirahəti də deyil."""
    if d in KOCURME or d in IL_BAYRAM:
        return True
    return any(e["off"] and not e["anim"] for e in _entries(d) if e["kind"] == "dovlet")


def _break_of(d):
    """d daxil olan bayram istirahəti (ən azı 3 günlük ardıcıl qeyri-iş günləri, içində bayram və ya köçürülən gün): (ilk, son).
    d iş günüdürsə, istirahət qısadırsa, bayramsızdırsa və ya sərhədi bilinmirsə None."""
    if not qeyri_is_gunu(d):
        return None
    ends = []
    for step in (-DAY, DAY):
        x = d
        for _ in range(40):
            flag = qeyri_is_gunu(x + step)
            if flag is None:
                return None
            if not flag:
                break
            x += step
        ends.append(x)
    first, last = ends
    run = [first + DAY * i for i in range((last - first).days + 1)]
    return (first, last) if len(run) >= 3 and any(_special(x) for x in run) else None


def _told_before(off, monday):
    """Bir hadisə, bir xəbər: həftənin bütün qeyri-iş günləri bazar ertəsindən əvvəl başlayan bayram istirahətinə düşürsə, o
    istirahət öncəki iş günü öz xəbərində (istirahet_item) verilib. O günü qaytarır, yoxsa None."""
    told = []
    for d in off:
        br = _break_of(d)
        if not br or br[0] >= monday or (br[0] - DAY).weekday() == 0:
            return None  # yeni gün, ya da istirahətdən əvvəlki iş günü bazar ertəsidir: o gün xəbər yoxdur
        told.append(br[0] - DAY)
    return max(told) if told else None


def is_item(day):
    """Bazar ertəsi: bu həftə neçə iş günü var. Adi beşgünlük həftə xəbər deyil (worth=False). Həftənin qeyri-iş günləri
    əvvəlki həftə başlayan və artıq xəbəri verilən bayram istirahətinə düşürsə, təkrar dərc olunmur (worth=False)."""
    day = _date(day)
    if day.weekday() != 0:
        return None, "bazar ertəsi deyil"
    week = [day + DAY * i for i in range(5)]
    why = _unknown(week)
    if why:
        return None, why
    off = [d for d in week if qeyri_is_gunu(d)]
    work = [d for d in week if not qeyri_is_gunu(d)]
    n = len(work)
    if n == 0:
        title = f"Bu həftə iş günü yoxdur: {_days_text(off)} istirahət günləridir"
        lead = f"{_src(day.year)}, bu həftə beşgünlük iş həftəsində iş günü yoxdur."
        nxt = _next_work(week[-1])
        if nxt:
            lead += f" Növbəti iş günü {_cop(ox.day_text(nxt))}."
    elif n == 5:
        title = "Bu həftə 5 iş günü var"
        lead = f"{_src(day.year)}, bu həftə beşgünlük iş həftəsinin bütün günləri iş günüdür."
    else:
        title = f"Bu həftə {n} iş günü var: {_days_text(off)} iş günü deyil"
        lead = f"{_src(day.year)}, bu həftə beşgünlük iş həftəsində {_days_text(work)} iş {_gunleri(n)}."
    item = {"kind": "is-gunleri", "key": f"is-gunleri-{day.isoformat()}", "title": title, "lead": lead,
            "body": _reason_lines(off), "credit": TEQVIM_CREDIT, "link": TEQVIM.get(day.year, "https://e-qanun.az/"),
            "topic": "təqvim", "slot": "08:00", "worth": n < 5}
    told = _told_before(off, day) if off else None
    if n == 5:
        item["why"] = "adi beşgünlük iş həftəsidir: xəbər deyil"
    elif told:
        item.update(worth=False, why=f"bu həftənin qeyri-iş günləri {ox.day_text(told)} tarixli bayram istirahəti xəbərində verilib")
    return item, item.get("why", "")


def _next_work(day):
    """day-dən sonrakı ilk iş günü; bilinməyən ilə çatanda None."""
    d = day + DAY
    for _ in range(40):
        flag = qeyri_is_gunu(d)
        if flag is None:
            return None
        if not flag:
            return d
        d += DAY
    return None


def _break_after(day):
    """Sabahdan bayram istirahəti başlayırmı. Qaytarır: ("var", ilk, son, növbəti iş günü), ("yox", səbəb) və ya
    ("bilinmir", səbəb). Bayram istirahəti: ən azı 3 günlük qeyri-iş günləri, içində bayram və ya köçürülən gün var."""
    flag = qeyri_is_gunu(day)
    if flag is None:
        return ("bilinmir", _unknown([day]))
    if flag:
        return ("yox", "bu gün iş günü deyil")
    run, d = [], day + DAY
    while len(run) < 40:
        flag = qeyri_is_gunu(d)
        if flag is None:
            return ("bilinmir", _unknown([d]))
        if not flag:
            break
        run.append(d)
        d += DAY
    if len(run) < 3 or not any(_special(x) for x in run):
        return ("yox", "sabahdan bayram istirahəti başlamır")
    return ("var", run[0], run[-1], d)


def istirahet_item(day):
    """Bayram istirahətindən əvvəlki son iş günü: istirahət neçə gündür, işə nə vaxt çıxılır. İstirahətin iş günlərinin
    hamısı bu həftədədirsə və bazar ertəsinin həftə xəbəri onları verib, təkrar dərc olunmur (worth=False)."""
    day = _date(day)
    state = _break_after(day)
    if state[0] != "var":
        return None, state[1]
    _, first, last, back = state
    if day.weekday() == 0:
        return None, "bazar ertəsidir: bunu həftənin iş günləri xəbəri deyir"
    n = (last - first).days + 1
    run = [first + DAY * i for i in range(n)]
    span = _range(first, last)
    item = {"kind": "istirahet", "key": f"istirahet-{first.isoformat()}",
            "title": f"{span} {n} gün istirahətdir, işə {ox.day_loc(back)} çıxılacaq",
            "lead": f"{_src(first.year, last.year)}, beşgünlük iş həftəsində {span} istirahət günləridir. "
                    f"Növbəti iş günü {_cop(ox.day_text(back))}.",
            "body": _reason_lines(run), "credit": TEQVIM_CREDIT,
            "link": TEQVIM.get(first.year, "https://e-qanun.az/"), "topic": "təqvim", "slot": "08:00", "worth": True}
    monday = day - DAY * day.weekday()
    if all(x <= monday + DAY * 4 for x in run if x.weekday() < 5):
        week, _ = is_item(monday)
        if week and week["worth"]:
            item.update(worth=False, why=f"bu istirahətin günləri {ox.day_text(monday)} tarixli həftənin iş günləri xəbərində verilib")
    return item, item.get("why", "")


# --- 3. Oyunlara geri sayım ---------------------------------------------------------------------------

def oyun_item(game, day):
    """Açılışa 100, 50, 30, 10, 1 gün qalanda və açılış günü."""
    day = _date(day)
    left = (game["start"] - day).days
    if left < 0:
        return None, f"{game['ad']} artıq başlayıb"
    if left not in MERHELE:
        return None, f"mərhələ günü deyil: açılışa {left} gün qalıb"
    name, place = game["ad"], ox.place_loc(game["seher"])
    if left == 0:
        title = f"{name} bu gün {place} başlayır"
    elif left == 1:
        title = f"{name} sabah {place} başlayır"
    else:
        title = f"{ox._gen_plain(name)} açılışına {left} gün qalıb"
    lead = (f"{name} {_range(game['start'], game['end'])} {ox.ordinal(game['start'].year)} il tarixlərində "
            f"{game['yer']} {'keçirilir' if left == 0 else 'keçiriləcək'}.")
    if left > 1:
        lead += f" Açılışa {left} gün qalıb."
    item = {"kind": "oyun", "key": f"oyun-{game['id']}-{left}", "title": title, "lead": lead,
            "body": [game["elave"]] if game["elave"] else [], "credit": game["credit"], "link": game["link"],
            "topic": "idman", "slot": "11:00", "worth": True}
    return item, ""


def _next_milestone(game, day):
    left = (game["start"] - _date(day)).days
    ahead = [m for m in MERHELE if m <= left]
    return game["start"] - DAY * max(ahead) if ahead else None


# --- 4. «Bu həftə nə gözlənilir» ----------------------------------------------------------------------

def _read(path):
    """JSON obyekt və ya None (fayl yoxdur, pozuqdur, obyekt deyil)."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _when(value):
    try:
        dt = datetime.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=BAKU)).astimezone(BAKU)


def _tur(value):
    value = str(value or "").strip()
    if value.isdigit():
        return f"{ox.ordinal(int(value))} tur"
    m = re.fullmatch(r"Qrup\s*(\d+)", value)
    return f"{ox.ordinal(int(m.group(1)))} qrup" if m else value


def _source_name(doc):
    src = str(doc.get("source") or "")
    if src == "pfl.az":
        return "Peşəkar Futbol Liqası", "https://pfl.az/"
    if src.startswith("OpenLigaDB"):
        return "OpenLigaDB", doc.get("source_url") or doc.get("url") or "https://www.openligadb.de/"
    return src, doc.get("source_url") or doc.get("url") or ""


def _team(teams, tid):
    info = teams.get(tid)
    return str(info.get("name") or tid) if isinstance(info, dict) else tid


def _games(root):
    """Azərbaycan futbolunun bütün oyunları: Premyer Liqa, I Liqa, Kubok, milli komanda (ml-*.json) və avrokuboklarda
    Azərbaycan klubları. Hər oyun: dt (Bakı vaxtı), timed (saat bəllidir), group, comp, rnd, home, away, home_id, away_id."""
    fut = pathlib.Path(root) / "data" / "futbol"
    out = []
    pl = _read(fut / "premyer-liqa.json") or {}
    clubs = set(pl.get("teams") or {}) if isinstance(pl.get("teams"), dict) else set()

    def add(doc, group, comp, quote, pfl, keep):
        if str(doc.get("sport") or "football") != "football":
            return  # basketbol və s.
        name, link = _source_name(doc)
        teams = doc.get("teams") if isinstance(doc.get("teams"), dict) else {}
        rows = doc.get("games") if isinstance(doc.get("games"), list) else []
        for g in rows:
            if not isinstance(g, dict):
                continue
            home_id, away_id = str(g.get("home") or ""), str(g.get("away") or "")
            dt = _when(g.get("date"))
            if not dt or not home_id or not away_id or not keep(home_id, away_id):
                continue
            home, away = _team(teams, home_id), _team(teams, away_id)
            if quote:
                home, away = f"«{home}»", f"«{away}»"
            iso = str(g.get("date") or "")
            timed = "T00:00" not in iso and (not pfl or bool(g.get("stadium")))
            # pfl.az cədvəli açıqlanmayan turun oyunlarını turun şərti tarixi ilə, saatsız və stadionsuz verir: günü də dəqiq deyil.
            out.append({"dt": dt, "timed": timed, "nominal": pfl and not timed, "group": group, "comp": comp, "rnd_raw": str(g.get("round") or ""),
                        "rnd": _tur(g.get("round")), "home": home, "away": away, "home_id": home_id, "away_id": away_id,
                        "stadium": g.get("stadium") or "", "source": name, "link": link})

    for fid, comp in LIQALAR:
        doc = _read(fut / f"{fid}.json")
        if doc:
            add(doc, fid, comp, True, True, lambda h, a: True)
    for path in sorted(fut.glob("ml-*.json")):
        doc = _read(path)
        if doc:
            add(doc, "milli", doc.get("name") or doc.get("short") or "", False, False,
                lambda h, a: "azerbaycan" in (h, a))
    for fid in AVROKUBOKLAR:
        doc = _read(fut / f"{fid}.json")
        if doc and clubs:
            add(doc, "avro", doc.get("name") or doc.get("short") or "", True, False,
                lambda h, a: h in clubs or a in clubs)
    out.sort(key=lambda g: (g["dt"], _ORDER.get(g["group"], 9), g["home"]))
    return out, clubs


def _in_week(g, start, end, now):
    """Həftənin hələ oynanmamış oyunu. Saatı bilinməyən oyun gün ilə müqayisə olunur (00:00 yer tutucudur);
    tarixi keçmiş, amma oynanmamış (təxirə salınmış) oyun yazılmır."""
    d = g["dt"].date()
    if not start <= d <= end:
        return False
    return g["dt"] >= now if g["timed"] else d >= now.date()


def _when_text(g):
    return f"{ox.day_text(g['dt'])} {ox.time_loc(g['dt'])}" if g["timed"] else ox.day_text(g["dt"])


def _pairs(games):
    parts = []
    for g in games:
        text = f"{g['home']} – {g['away']}"
        if g["timed"]:
            text += f", {g['dt']:%H:%M}"
        if g["group"] == "milli" and g["stadium"]:
            text += f", {g['stadium']}"
        parts.append(text)
    return "; ".join(parts)


def _round_of(games, all_games):
    """Oyunlar bir turdandırsa: (tur, tur bütünlüklə bu oyunlardır). Bir neçə turdandırsa: (None, False)."""
    rounds = list(dict.fromkeys(g["rnd_raw"] for g in games))
    if len(rounds) != 1:
        return None, False
    return rounds[0], len([g for g in all_games if g["rnd_raw"] == rounds[0]]) == len(games)


def _span(games):
    return _range(games[0]["dt"].date(), games[-1]["dt"].date())


def _league_lead(games, nominal, all_games, end):
    """Premyer Liqa cümlələri. Cədvəli açıqlanmayan turun (pfl.az-da saat və stadion yoxdur, tarix turun şərti tarixidir)
    günü yazılmır."""
    out = []
    if games:
        rnd, whole = _round_of(games, all_games)
        if rnd and rnd.isdigit() and whole:
            out.append(f"Premyer Liqanın {_tur(rnd)}u {_loc(_span(games))} keçiriləcək.")
        elif rnd and rnd.isdigit():
            out.append(f"Premyer Liqanın {_tur(rnd)}unun {len(games)} oyunu bu həftə keçiriləcək.")
        else:
            out.append(f"Premyer Liqada bu həftə {len(games)} oyun keçiriləcək.")
    if nominal:
        rnd, _ = _round_of(nominal, all_games)
        out.append(f"Premyer Liqanın {_tur(rnd)}unun oyun cədvəli hələ açıqlanmayıb." if rnd and rnd.isdigit() else
                   "Premyer Liqada bu həftəki digər oyunların cədvəli hələ açıqlanmayıb.")
    if out:
        return " ".join(out)
    later = [g for g in all_games if g["dt"].date() > end]
    if not later or later[0]["nominal"]:
        return ""
    nxt = later[0]
    rnd_games = [g for g in all_games if g["rnd_raw"] == nxt["rnd_raw"]]
    pair = f"{nxt['home']} – {nxt['away']}"
    opens = all(not g["nominal"] for g in rnd_games) and min(g["dt"] for g in rnd_games) == nxt["dt"]
    if opens and nxt["rnd_raw"].isdigit():
        return f"Premyer Liqada bu həftə oyun yoxdur: {nxt['rnd']} {ox.day_loc(nxt['dt'])} {pair} oyunu ilə başlayacaq."
    return f"Premyer Liqada bu həftə oyun yoxdur, növbəti oyun {ox.day_text(nxt['dt'])}: {pair} ({nxt['rnd']})."


def _cup_lead(games, nominal):
    if games:
        rnd, _ = _round_of(games, games)
        name = _tur(rnd) if rnd else "bu həftəki"
        return f"Azərbaycan Kubokunun {name} oyunları {_loc(_span(games))} keçiriləcək."
    if nominal:
        rnd, _ = _round_of(nominal, nominal)
        return f"Azərbaycan Kubokunun {_tur(rnd) if rnd else 'bu həftəki'} oyunlarının cədvəli hələ açıqlanmayıb."
    return ""


def _state_lead(cal):
    """Həftənin dövlət bayramları, eyni adlı günlər bir yerdə: «9 noyabr Dövlət Bayrağı Günü, 12 noyabr isə Konstitusiya Günüdür»."""
    names = {}
    for d, ents in cal:
        for e in ents:
            if e["kind"] == "dovlet":
                names.setdefault(e["name"], []).append(d)
    parts = [(_days_text(days), name) for name, days in names.items()]
    if not parts:
        return ""
    if len(parts) == 1:
        return _cop(f"{parts[0][0]} {parts[0][1]}") + "."
    head = ", ".join(f"{days} {name}" for days, name in parts[:-1])
    return f"{head}, {parts[-1][0]} isə {_cop(parts[-1][1])}."


def hefte_item(root, now):
    """«Bu həftə nə gözlənilir»: bazar ertəsi, həftənin bayramları, günləri və Azərbaycan futbolunun oyunları."""
    now = _now(now)
    day = now.date()
    if day.weekday() != 0:
        return None, "bazar ertəsi deyil"
    end = day + DAY * 6
    days = [day + DAY * i for i in range(7)]
    games, clubs = _games(root)
    week = [g for g in games if _in_week(g, day, end, now)]
    fixed = [g for g in week if not g["nominal"]]
    nominal = [g for g in week if g["nominal"]]
    every = lambda group: [g for g in games if g["group"] == group]
    by = lambda group, rows: [g for g in rows if g["group"] == group]
    milli, avro = by("milli", fixed), by("avro", fixed)
    pl, pl_nom = by("premyer-liqa", fixed), by("premyer-liqa", nominal)
    kubok, kubok_nom = by("kubok", fixed), by("kubok", nominal)
    il = by("i-liqa", fixed)
    cal = [(d, _entries(d)) for d in days]
    off = [d for d in days[:5] if qeyri_is_gunu(d)]

    lead = []
    for g in milli:
        home = g["home_id"] == "azerbaycan"
        opp = g["away"] if home else g["home"]
        lead.append(f"Azərbaycan millisi {_when_text(g)} {'doğma meydanda' if home else 'səfərdə'} {opp} ilə oynayacaq "
                    f"({g['comp']}, {g['rnd']}).")
    for g in avro:
        home = g["home_id"] in clubs
        club, opp = (g["home"], g["away"]) if home else (g["away"], g["home"])
        lead.append(f"{club} {_when_text(g)} {g['comp']} oyununda {'doğma meydanda' if home else 'səfərdə'} "
                    f"{opp} ilə qarşılaşacaq.")
    pl_line = _league_lead(pl, pl_nom, every("premyer-liqa"), end)
    lead.append(pl_line)
    lead.append(_cup_lead(kubok, kubok_nom))
    if il and not pl:
        rnd, whole = _round_of(il, every("i-liqa"))
        lead.append(f"I Liqanın {_tur(rnd)}u {_loc(_span(il))} keçiriləcək." if rnd and rnd.isdigit() and whole else
                    f"I Liqada bu həftə {len(il)} oyun keçiriləcək.")
    lead.append(_state_lead(cal))
    if off:
        lead.append(f"{_days_text(off)} iş günü deyil.")

    body = []
    for d, ents in cal:
        names = ["istirahət günü (iş günü deyil)"] if d in KOCURME else []
        for e in ents:
            if e["kind"] == "dovlet":
                names.append(e["name"] + (" (iş günü deyil)" if d.weekday() < 5 and qeyri_is_gunu(d) else ""))
            elif e["kind"] in ("pese", "bmt"):
                names.append(e["name"])
            elif e["first"]:
                names.append(f"{e['name']} başlayır ({_range(e['start'], e['end'])})")
        if names:
            body.append(f"{ox.day_text(d)} ({WEEKDAYS[d.weekday()]}): {'; '.join(names)}")
        todays = [g for g in fixed if g["dt"].date() == d]
        for key in sorted(dict.fromkeys((g["group"], g["comp"], g["rnd"]) for g in todays), key=lambda k: _ORDER.get(k[0], 9)):
            same = [g for g in todays if (g["group"], g["comp"], g["rnd"]) == key]
            body.append(f"{ox.day_text(d)} ({WEEKDAYS[d.weekday()]}): {key[1]}, {key[2]} — {_pairs(same)}")
    for key in dict.fromkeys((g["group"], g["comp"], g["rnd"]) for g in nominal):
        same = [g for g in nominal if (g["group"], g["comp"], g["rnd"]) == key]
        body.append(f"{key[1]}, {key[2]} — {_pairs(same)}: oyun cədvəli hələ açıqlanmayıb "
                    f"(pfl.az-da turun tarixi {ox.day_text(same[0]['dt'])})")

    later = [e for d, ents in cal if d > day for e in ents if e["kind"] == "dovlet" and not e["anim"]]
    hi = [f"{milli[0]['home']} – {milli[0]['away']} oyunu"] if len(milli) == 1 else (
        [f"Azərbaycan millisinin {len(milli)} oyunu"] if milli else [])
    hi += [f"{g['home']} – {g['away']} oyunu" for g in avro]
    hi += [e["name"] for e in later if e["off"]]
    for rows in (pl, pl_nom):
        if rows:
            rnd, whole = _round_of(rows, every("premyer-liqa"))
            hi.append(f"Premyer Liqanın {_tur(rnd)}u" if rnd and rnd.isdigit() and (whole or rows is pl_nom) else
                      "Premyer Liqa oyunları")
            break
    hi += [e["name"] for e in later if not e["off"]]
    hi += [e["name"] for e in cal[0][1] if e["kind"] == "dovlet" and not e["anim"]]
    for rows in (kubok, kubok_nom):
        if rows:
            rnd, _ = _round_of(rows, rows)
            hi.append(f"Azərbaycan Kubokunun {_tur(rnd)} oyunları" if rnd else "Azərbaycan Kuboku oyunları")
            break
    if il:
        rnd, _ = _round_of(il, il)
        hi.append(f"I Liqanın {_tur(rnd)}u" if rnd and rnd.isdigit() else "I Liqa oyunları")
    hi += [e["name"] for d, ents in cal for e in ents if e["kind"] == "pese"]  # «vergi xidməti ...» kiçik hərflə qalır
    hi += [e["name"] for d, ents in cal for e in ents if e["kind"] == "bmt"][:1]
    hi = list(dict.fromkeys(hi))
    title = "Bu həftə nə gözlənilir"
    if hi:
        both = f"{title}: {_join(hi[:2])}"
        title = both if len(both) <= TITLE_MAX else f"{title}: {hi[0]}"

    sources = [(g["source"], g["link"]) for g in sorted(week, key=lambda g: g["group"] != "premyer-liqa") if g["source"]]
    if pl_line:  # «Premyer Liqada bu həftə oyun yoxdur: 12-ci tur ...» da pfl.az-ın məlumatıdır
        sources += [(g["source"], g["link"]) for g in every("premyer-liqa")[:1] if g["source"]]
    if any(e["kind"] in ("bmt", "hefte") for _, ents in cal for e in ents):
        sources.append((BMT_CREDIT, BMT_URL))
    if off:  # rəsmi təqvimi olmayan ildə yalnız qanunla qeyri-iş günü olanlar (Əmək Məcəlləsi) yazılır
        url = TEQVIM.get(off[0].year)
        sources.append((TEQVIM_CREDIT, url) if url else ("e-qanun.az", "https://e-qanun.az/"))
    sources = list(dict.fromkeys(sources))
    credit = ", ".join(dict.fromkeys(s for s, _ in sources)) or BMT_CREDIT
    link = next((link for _, link in sources if link), BMT_URL)
    substance = milli or avro or pl or pl_nom or kubok or kubok_nom or il or off or any(
        e["kind"] == "dovlet" for _, ents in cal for e in ents)
    item = {"kind": "hefte", "key": f"hefte-{day.isoformat()}", "title": title, "lead": " ".join(s for s in lead if s),
            "body": body, "list": True, "credit": credit, "link": link, "topic": "icmal", "slot": "08:30",
            "worth": bool(substance)}
    if not substance and by("i-liqa", nominal):
        item["why"] = "bu həftə bayram və vaxtı bəlli futbol oyunu yoxdur: I Liqanın oyun cədvəli hələ açıqlanmayıb"
    elif not substance:
        item["why"] = "bu həftə futbol oyunu və bayram yoxdur: yalnız beynəlxalq və peşə günləri (onları gündəlik xəbər verir)"
    return item, item.get("why", "")


# --- Ümumi: istehsalın xəbərləri və sınaq -------------------------------------------------------------

def _leader(text):
    try:
        return bool(ox.needs_owner(text))
    except Exception:
        return bool(re.search(r"prezident|birinci xanım|vitse-prezident|əliyev", ox._low(text)))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər dərc olunmur (sahibin qaydası)."""
    if _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: dərc olunmur")
    return item


def items(root, now, fetch=None):
    """now-un Bakı tarixi üçün bütün xəbərlər, hər birinin «slot» saatı ilə. worth=False olanlar da qaytarılır (səbəbi «why»-dadır):
    dərc edən onları buraxır. Sorğu yoxdur: fetch işlənmir."""
    now = _now(now)
    day = now.date()
    found = [gun_item(day), is_item(day), istirahet_item(day)]
    found += [oyun_item(g, day) for g in OYUNLAR]
    found.append(hefte_item(root, now))
    return [_guard(item) for item, _ in found if item]


def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'səbəb yazılmayıb'}"


def _label(d, today):
    rel = {0: "bu gün", -1: "dünən", 1: "sabah"}.get((d - today).days, "")
    return f"{ox.day_text(d)} {d.year}, {WEEKDAYS[d.weekday()]}" + (f" ({rel})" if rel else "")


def _show(label, item, why):
    if not item:
        return [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    return [f"**{label}, saat {item['slot']}:**", ""] + ox.render(_guard(item)) + [_verdict(_guard(item)), ""]


def _search(build, start, step, limit, stop_unknown=True):
    """build(d) xəbər verən ilk günü axtarır (step = 1 irəli, -1 geri). Bilinməyən ilə çatanda (d, None, səbəb)."""
    d = start
    for _ in range(limit):
        item, why = build(d)
        if item and item.get("worth"):
            return d, item, why
        if stop_unknown and why.endswith("təxmin edilmir"):
            return d, None, why
        d += DAY * step
    return None, None, ""


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown). Bugünkü hallardan başqa ən son real halları da göstərir, adı ilə. Heç nə yazmır, sorğu yoxdur."""
    root = pathlib.Path(root)
    now = _now(now)
    today = now.date()
    monday = today - DAY * today.weekday()
    md = ["# Təqvim xəbərləri (oz_teqvim.py): sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Sayta heç nə yazılmır, şəbəkə sorğusu yoxdur.", "",
          "## Bu gün dərc olunacaqlar", ""]
    todays = items(root, now)
    md += [f"- {i['slot']} · {i['key']} · {'✅' if i['worth'] else '⏭ ' + str(i.get('why') or '')}" for i in todays] or ["- yoxdur"]
    md += ["", "## 1. «Bu gün nə günüdür» (hər gün 07:45)", ""]
    for i in range(-1, 7):
        d = today + DAY * i
        item, why = gun_item(d)
        md += _show(_label(d, today), item, why)

    md += ["## 2. «Bu həftə neçə iş günü var» (bazar ertəsi 08:00)", ""]
    item, why = is_item(monday)
    md += _show(_label(monday, today) + " — bu həftə", item, why)
    if not (item and item.get("worth")):
        d, item, why = _search(is_item, monday - DAY * 7, -7, 60)
        if d:
            md += _show(_label(d, today) + " — ən son real hal", item, why)
    item, why = is_item(monday + DAY * 7)
    md += _show(_label(monday + DAY * 7, today) + " — gələn həftə", item, why)
    md += ["## 3. Bayram istirahətindən əvvəlki son iş günü (08:00)", ""]
    d, item, why = _search(istirahet_item, today, -1, 400)
    if d:
        md += _show(_label(d, today) + " — ən son real hal", item, why)
    d, item, why = _search(istirahet_item, today + DAY, 1, 400)
    if d:
        md += _show(_label(d, today) + " — növbəti", item, why)

    md += ["## 4. Oyunlara geri sayım (11:00)", ""]
    for game in OYUNLAR:
        item, why = oyun_item(game, today)
        md += _show(f"{game['ad']}, {_label(today, today)}", item, why)
        nxt = _next_milestone(game, today + DAY)
        if nxt:
            item, why = oyun_item(game, nxt)
            md += _show(f"{game['ad']}, növbəti mərhələ: {_label(nxt, today)}", item, why)

    md += ["## 5. «Bu həftə nə gözlənilir» (bazar ertəsi 08:30)", ""]
    at = datetime.datetime.combine(monday, datetime.time(8, 30), tzinfo=BAKU)
    item, why = hefte_item(root, at)
    md += _show(_label(monday, today) + " — bu həftə (oyunlar indiki məlumatla)", item, why)
    item, why = hefte_item(root, at + DAY * 7)
    md += _show(_label(monday + DAY * 7, today) + " — gələn həftə (bugünkü məlumatla)", item, why)
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    when = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(when) if when else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
