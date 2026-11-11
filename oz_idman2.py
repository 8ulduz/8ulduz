"""Formula 1, cüdo və UEFA ölkə əmsalları üzrə 8ulduz-un öz xəbərləri (mərhələ 2: açarsız açıq API-lər, şablon).

Sahibin qərarı (2026-11-10): «Mərhələ 2-ni qur». Sınaq budağında qurulur, sayta qoşulmur: updater.py və pipeline.sh bu
faylı çağırmır. Nümunələri `python oz_idman2.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]` çıxarır.

Xəbər növləri:
1. Formula 1 (Jolpica, Ergast ilə uyğun API: api.jolpi.ca).
   - Yarış həftəsinin cümə axşamı 11:00-da qısa ön baxış: mərhələ, pist, Bakı vaxtı ilə start, çempionatın ilk üçlüyü.
   - Kvalifikasiyanın nəticəsi (Avropa yarışlarında şənbə axşamı), yarışın nəticəsi və çempionatın ilk beşliyi (bazar axşamı).
     Amerika yarışları Bakıda gecəyə düşür: onların xəbəri səhər 09:30-dadır.
   - Azərbaycan Qran-prisi (Bakı Şəhər Halqası) başlıqda və girişdə ayrıca deyilir.
   - Pilot və komanda adları mənbədəki kimi latınca qalır, şəkilçi oxunuşa görədir: «Norris»in, «Verstappen»ə, «Leclerc»ə.
2. Cüdo (Beynəlxalq Cüdo Federasiyası, data.ijf.org): Dünya turunun hər turnirindən (Böyük Dəbilqə, Qran-pri, Masters,
   dünya çempionatı) sonra Azərbaycan cüdoçularının medalları, turnir başına bir xəbər. Ad-soyadlar Azərbaycan Cüdo
   Federasiyasının yazılışı ilədir (judo.az/az/team); orada olmayan idmançının adı IJF-in latın yazılışı ilə qalır.
3. UEFA ölkə əmsalları (comp.uefa.com): avrokubok həftəsindən sonrakı gün 11:00-da. Xəbər yalnız iki halda var:
   Azərbaycanın yeri dəyişib (UEFA-nın öz «trend» sahəsi UP/DOWN) və ya Azərbaycan klubları həmin həftə qələbə və ya
   heç-heçə ilə xal qazanıb (saytın data/futbol/cl|al|kl.json nəticələri). Dəyişməyən cədvəl xəbər deyil.

Təqvim. F1 2026 və IJF 2026–2027 təqvimləri modulun içindədir (yalnız vaxt üçün; mətnin hər faktı sorğunun cavabındandır).
Testlər onları API-nin saxlanmış cavabları ilə tutuşdurur, sınaq isə canlı API ilə. F1-in 2027 təqvimi API-də hələ yoxdur
(2026-11-10): o çıxanda F1_CAL-a əlavə olunmalıdır, yoxsa 2027-də F1 xəbəri çıxmır (sınaq bunu xəbərdar edir).

Sorğular. Hamısı yalnız fetch parametri ilə gedir və yalnız xəbərin cəhd pəncərəsində (bir cəhd = 40 dəqiqə; F1-də iki cəhd,
2 saat ara ilə, cüdo və UEFA-da bir cəhd). Mövsümdən kənar heç bir sorğu yoxdur.
Bir pəncərədə bir dəfə sorğu gedir: nəticə xəbər olmasa da (məlumat gecikir, mənbə alınmır, «xəbər deyil») items() onun
açarını worth=False və «why» ilə qaytarır. F1-in birinci cəhdi alınmayanda açar «…-cehd1»-dir ki, ikinci cəhd bağlanmasın.
Canlı sistem items()-in qaytardığı HƏR açarı (worth=False olanı da) done-a yazmalıdır: done-dakı açar üçün sorğu yoxdur.
Bir xəbərin ən çox sorğusu: ön baxış 2 (Bakı həftəsində 3: pistin tarixçəsi), kvalifikasiya 1, yarış 2 (nəticə + cədvəl),
cüdo 1, UEFA 1; birinci cəhd alınmayanda +1. Təqvimdəki ən ağır gün 4–5 sorğudur (hədd 6; testlər hər planlı günü sayır).
"""
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.parse

import oz_xeber as ox
import oz_futbol_dunya as fd

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)
TRY = datetime.timedelta(minutes=40)            # bir cəhdin pəncərəsi: 10–30 dəqiqəlik dövrə gecikəndə də onu bir dəfə görür
TRY_GAP = datetime.timedelta(hours=2)           # F1-in ikinci cəhdi (Jolpica nəticəni bir neçə saat gec yaza bilir)
EARLY = datetime.time(9, 30)                    # gecə hazır olan nəticə səhər 09:30-da
LATE = datetime.time(22, 30)                    # bundan gec slot ertəsi gün 10:00-a keçir
NEXT_MORNING = datetime.time(10, 0)
LAST_TRY = datetime.time(23, 30)
QUALI_READY = datetime.timedelta(hours=3)       # kvalifikasiya ~1 saat + Jolpica-nın gecikməsi
RACE_READY = datetime.timedelta(hours=4)        # yarış ~1 saat 40 dəqiqə + gecikmə
PREVIEW_AT = datetime.time(11, 0)
UEFA_AT = datetime.time(11, 0)
UEFA_LAG = datetime.timedelta(hours=3)          # həftənin son oyunundan UEFA cədvəlinin yenilənməsinədək ehtiyat
JUDO_LOCAL_READY = datetime.time(21, 0)         # final bloku yerli vaxtla ~18:00–19:30-da bitir
TIMEOUT = 15
TITLE_MAX = 110
MIN_CLASSIFIED = 10                             # yarış və kvalifikasiya cədvəlində ən azı 10 pilot olmalıdır
JUDO_CATS = 14                                  # Dünya turunun fərdi yarışında 7 kişi + 7 qadın çəkisi
DAILY_CAP = 4                                   # bir çağırışda ən çox bu qədər xəbər (təqvimdə bir günə 3-dən çox düşmür)
STALE = datetime.timedelta(days=2)              # yarışın nəticəsi bundan köhnədirsə xəbər deyil (təqvim dəyişib)
PREVIEW_AHEAD = datetime.timedelta(days=4)      # ön baxış: yarış cümə axşamından ən çox 4 gün sonra olmalıdır
SEC_PAUSE = 1.0                                 # sınaqda eyni hosta sorğular arasında fasilə

F1_API = "https://api.jolpi.ca/ergast/f1"
F1_CREDIT = "Jolpica F1 API (Ergast)"
IJF_API = "https://data.ijf.org/api/get_json?"
IJF_CREDIT = "Beynəlxalq Cüdo Federasiyası (IJF)"
IJF_PAGE = "https://www.ijf.org/competition/{}/results"
UEFA_API = ("https://comp.uefa.com/v2/coefficients?coefficientRange=OVERALL&coefficientType=MEN_ASSOCIATION"
            "&language=EN&page=1&pagesize=40&seasonYear={}")
UEFA_PAGE = "https://www.uefa.com/nationalassociations/uefarankings/country/?year={}"
UEFA_CREDIT = "UEFA"
JSON_HEADERS = {"Accept": "application/json"}

LABEL = {"f1-onbaxis": "F1 · ön baxış", "f1-siralama": "F1 · kvalifikasiya", "f1-yaris": "F1 · yarış",
         "cudo": "Cüdo · IJF turniri", "uefa-emsal": "UEFA · ölkə əmsalları"}
PRIO = {"f1-yaris": 1, "f1-siralama": 2, "cudo": 2, "uefa-emsal": 3, "f1-onbaxis": 4}

# --- Formula 1 təqvimi (Jolpica, /ergast/f1/2026.json, 2026-11-10): mərhələ|ad|kvalifikasiya UTC|yarış UTC -----------
_F1_2026 = """
1|Australian Grand Prix|2026-03-07 05:00|2026-03-08 04:00
2|Chinese Grand Prix|2026-03-14 07:00|2026-03-15 07:00
3|Japanese Grand Prix|2026-03-28 06:00|2026-03-29 05:00
4|Miami Grand Prix|2026-05-02 20:00|2026-05-03 20:00
5|Canadian Grand Prix|2026-05-23 20:00|2026-05-24 20:00
6|Monaco Grand Prix|2026-06-06 14:00|2026-06-07 13:00
7|Barcelona Grand Prix|2026-06-13 14:00|2026-06-14 13:00
8|Austrian Grand Prix|2026-06-27 14:00|2026-06-28 13:00
9|British Grand Prix|2026-07-04 15:00|2026-07-05 14:00
10|Belgian Grand Prix|2026-07-18 14:00|2026-07-19 13:00
11|Hungarian Grand Prix|2026-07-25 14:00|2026-07-26 13:00
12|Dutch Grand Prix|2026-08-22 14:00|2026-08-23 13:00
13|Italian Grand Prix|2026-09-05 14:00|2026-09-06 13:00
14|Spanish Grand Prix|2026-09-12 14:00|2026-09-13 13:00
15|Azerbaijan Grand Prix|2026-09-25 12:00|2026-09-26 11:00
16|Bahrain Grand Prix in Malaysia|2026-10-03 08:00|2026-10-04 07:00
17|Singapore Grand Prix|2026-10-10 13:00|2026-10-11 12:00
18|United States Grand Prix|2026-10-24 21:00|2026-10-25 20:00
19|Mexico City Grand Prix|2026-10-31 21:00|2026-11-01 20:00
20|Brazilian Grand Prix|2026-11-07 18:00|2026-11-08 17:00
21|Las Vegas Grand Prix|2026-11-21 04:00|2026-11-22 04:00
22|Qatar Grand Prix|2026-11-28 18:00|2026-11-29 16:00
23|Abu Dhabi Grand Prix|2026-12-05 14:00|2026-12-06 13:00
"""

GP_AZ = {
    "Australian Grand Prix": "Avstraliya Qran-prisi", "Chinese Grand Prix": "Çin Qran-prisi",
    "Japanese Grand Prix": "Yaponiya Qran-prisi", "Bahrain Grand Prix": "Bəhreyn Qran-prisi",
    "Saudi Arabian Grand Prix": "Səudiyyə Ərəbistanı Qran-prisi", "Miami Grand Prix": "Mayami Qran-prisi",
    "Emilia Romagna Grand Prix": "Emilia-Romanya Qran-prisi", "Canadian Grand Prix": "Kanada Qran-prisi",
    "Monaco Grand Prix": "Monako Qran-prisi", "Barcelona Grand Prix": "Barselona Qran-prisi",
    "Spanish Grand Prix": "İspaniya Qran-prisi", "Austrian Grand Prix": "Avstriya Qran-prisi",
    "British Grand Prix": "Britaniya Qran-prisi", "Belgian Grand Prix": "Belçika Qran-prisi",
    "Hungarian Grand Prix": "Macarıstan Qran-prisi", "Dutch Grand Prix": "Niderland Qran-prisi",
    "Italian Grand Prix": "İtaliya Qran-prisi", "Azerbaijan Grand Prix": "Azərbaycan Qran-prisi",
    "Bahrain Grand Prix in Malaysia": "Bəhreyn Qran-prisi (Malayziyada)", "Singapore Grand Prix": "Sinqapur Qran-prisi",
    "United States Grand Prix": "ABŞ Qran-prisi", "Mexico City Grand Prix": "Mexiko Qran-prisi",
    "Brazilian Grand Prix": "Braziliya Qran-prisi", "São Paulo Grand Prix": "San-Paulu Qran-prisi",
    "Las Vegas Grand Prix": "Las-Veqas Qran-prisi", "Qatar Grand Prix": "Qətər Qran-prisi",
    "Abu Dhabi Grand Prix": "Əbu-Dabi Qran-prisi", "Portuguese Grand Prix": "Portuqaliya Qran-prisi",
}
CITY_AZ = {
    "Melbourne": "Melburn", "Shanghai": "Şanxay", "Suzuka": "Suzuka", "Sakhir": "Səxir", "Jeddah": "Ciddə",
    "Miami": "Mayami", "Imola": "İmola", "Montreal": "Monreal", "Monte Carlo": "Monte-Karlo", "Monte-Carlo": "Monte-Karlo",
    "Barcelona": "Barselona", "Montmeló": "Barselona", "Spielberg": "Şpilberq", "Silverstone": "Silverstoun",
    "Spa": "Spa", "Budapest": "Budapeşt", "Zandvoort": "Zandvort", "Monza": "Monza", "Madrid": "Madrid",
    "Baku": "Bakı", "Kuala Lumpur": "Kuala-Lumpur", "Marina Bay": "Sinqapur", "Singapore": "Sinqapur",
    "Austin": "Ostin", "Mexico City": "Mexiko", "São Paulo": "San-Paulu", "Las Vegas": "Las-Veqas",
    "Lusail": "Lusail", "Abu Dhabi": "Əbu-Dabi", "Yas Marina": "Əbu-Dabi", "Portimão": "Portimao",
}
BAKU_CIRCUIT = "Bakı Şəhər Halqası"
# Soyadın oxunuşunun sonu (Azərbaycan hərfləri ilə): şəkilçi buna görə seçilir. Xəritədə olmayan ad yazılışına görə dəyişir.
F1_PRON = {
    "Norris": "noris", "Verstappen": "ferstappen", "Leclerc": "leklerk", "Hamilton": "hemilton", "Russell": "rasel",
    "Antonelli": "antonelli", "Piastri": "piastri", "Hadjar": "adjar", "Lawson": "losn", "Gasly": "qasli",
    "Lindblad": "lindblad", "Colapinto": "kolapinto", "Bearman": "birmen", "Bortoleto": "bortoleto",
    "Hülkenberg": "hülkenberq", "Ocon": "okon", "Alonso": "alonso", "Sainz": "sayns", "Albon": "albon",
    "Tsunoda": "tsunoda", "Hirakawa": "hirakava", "Stroll": "strol", "Bottas": "bottas", "Pérez": "peres",
    "Camara": "kamara", "Doohan": "duhan",
}

# --- Cüdo: Dünya turunun fərdi böyüklər yarışları (IJF competition.get_list, 2026 və 2027, 2026-11-10) -------------
# id|növ|şəhər (IJF)|başlanğıc|son gün|yerli vaxt UTC-dən fərq (saat; 2026-nın siyahısındakı saat qurşağından)
_CUDO = """
3131|Grand Slam|Paris|2026-02-07|2026-02-08|1
3132|Grand Slam|Tashkent|2026-02-27|2026-03-01|5
3135|Grand Prix|Linz|2026-03-06|2026-03-08|1
3134|Grand Slam|Tbilisi|2026-03-20|2026-03-22|4
3138|Grand Slam|Dushanbe|2026-05-01|2026-05-03|5
3139|Grand Slam|Astana|2026-05-08|2026-05-10|5
3149|Grand Slam|Ulaanbaatar|2026-06-19|2026-06-21|8
3204|Grand Prix|Qingdao|2026-06-26|2026-06-28|8
3205|Grand Prix|Lima|2026-08-14|2026-08-16|-5
3225|Grand Slam|Lausanne|2026-08-28|2026-08-30|2
3155|Grand Slam|Budapest|2026-09-11|2026-09-13|2
3151|World Championships|Baku|2026-10-04|2026-10-10|4
3157|Grand Slam|Abu Dhabi|2026-10-29|2026-10-31|4
3159|Grand Prix|Zagreb|2026-11-13|2026-11-15|1
3160|Grand Slam|Tokyo|2026-12-05|2026-12-06|9
3343|Masters|Dushanbe|2026-12-18|2026-12-20|5
3376|Grand Slam|Paris|2027-02-05|2027-02-07|1
3378|Grand Slam|Baku|2027-02-19|2027-02-21|4
3377|Grand Slam|Tashkent|2027-03-05|2027-03-07|5
3379|Grand Prix|Linz|2027-03-12|2027-03-14|1
3380|Grand Slam|Tbilisi|2027-03-26|2027-03-28|4
3381|Grand Slam|Dushanbe|2027-04-30|2027-05-02|5
3390|World Championships|Astana|2027-06-07|2027-06-13|5
3382|Grand Slam|Ulaanbaatar|2027-06-25|2027-06-27|8
3383|Grand Prix|Qingdao|2027-07-02|2027-07-04|8
3384|Grand Slam|Lausanne|2027-08-27|2027-08-29|2
3386|Grand Prix|Lima|2027-09-17|2027-09-19|-5
3385|Grand Slam|Budapest|2027-10-01|2027-10-03|2
3387|Grand Slam|Abu Dhabi|2027-10-22|2027-10-24|4
3388|Grand Prix|Zagreb|2027-11-12|2027-11-14|1
3389|Grand Slam|Tokyo|2027-12-04|2027-12-05|9
"""
JUDO_CITY = {"Paris": "Paris", "Tashkent": "Daşkənd", "Linz": "Linz", "Tbilisi": "Tbilisi", "Dushanbe": "Düşənbə",
             "Astana": "Astana", "Ulaanbaatar": "Ulan-Bator", "Qingdao": "Tsindao", "Lima": "Lima",
             "Lausanne": "Lozanna", "Budapest": "Budapeşt", "Baku": "Bakı", "Abu Dhabi": "Əbu-Dabi", "Zagreb": "Zaqreb",
             "Tokyo": "Tokio"}
JUDO_RANK = {"Grand Slam": "Böyük Dəbilqə turniri", "Grand Prix": "Qran-pri turniri", "Masters": "Masters turniri",
             "World Championships": "dünya çempionatı"}
# IJF şəxs id-si -> Azərbaycan Cüdo Federasiyasının yazılışı (judo.az/az/team, 2026-11-10). 2026-da Dünya turunda yer
# tutan bütün Azərbaycan idmançıları; IJF-in latın yazılışı bəzən fərqlidir (TCKAEV, KOTSOIEV, GALANDARZADE, Dzhamal).
AZ_JUDOKA = {
    "20144": "Balabəy Ağayev", "29091": "Əhməd Yusifov", "74709": "Murad Muradlı", "45154": "Ruslan Paşayev",
    "43672": "Turan Bayramov", "30150": "Rəşad Yelkiyev", "60787": "Nizami İmranov", "60111": "İslam Rəhimov",
    "13028": "Hidayət Heydərov", "30188": "Rəşid Məmmədəliyev", "51301": "Zelim Tçkayev", "60560": "Ömər Rəcəbli",
    "60113": "Vüsal Qələndərzadə", "20741": "Murad Fətiyev", "25741": "Zelim Kotsoyev", "13278": "Uşanqi Kokauri",
    "64022": "Kənan Nəsibov", "70960": "Camal Qamzatxanov", "73473": "Aslan Kotsoyev", "51220": "Könül Əliyeva",
    "20752": "Şəfəq Həmidova", "20760": "Gültac Məmmədəliyeva", "96596": "Madina Kaisinova",
}
# Federasiyanın böyüklər və gənclər yığması (judo.az/az/team): id-si xəritədə olmayan idmançı IJF yazılışının
# Azərbaycan hərflərindən çevrilməsi ilə tapılır (Ağayev -> aghayev). Uyğun gəlməyən ad IJF-in yazılışı ilə qalır.
_ROSTER = """Balabəy Ağayev, Əhməd Yusifov, Murad Muradlı, Babarəhim Mirzəyev, Ruslan Paşayev, Turan Bayramov, Rəşad Yelkiyev,
Nizami İmranov, Elşən Əsədov, İslam Rəhimov, Yaşar Nəcəfov, Nazir Talıbov, Hüseyn Allahyarov, Hidayət Heydərov,
Rəşid Məmmədəliyev, Kamran Süleymanov, Rüfət Şövlətov, Nəriman Mirzəyev, Zelim Tçkayev, Ömər Rəcəbli, Vüsal Qələndərzadə,
Elcan Hacıyev, Murad Fətiyev, Vüqar Talıbov, Xəyyam Əliyev, Məmmədrza Hacızadə, Zelim Kotsoyev, Elmar Qasımov,
Əjdər Bağırov, Uşanqi Kokauri, Kənan Nəsibov, Camal Qamzatxanov, Könül Əliyeva, Şəfəq Həmidova, Diana Tçkayeva,
Gültac Məmmədəliyeva, Aydan Vəliyeva, Leyla Əliyeva, Ülviyyə Bayramova, Gülnarə Bayramova, Nərgiz Hacıyeva,
Südabə Ağayeva, Aytac Qardaşxanlı, Alina Kugayeva, Madina Kaisinova, Ayxan Mirzəzadə, Rəsul Əlizadə, Nihad Məmişov,
Məhəmməd Musayev, Sadiq İskəndərli, Mehdi Abbasov, Əbil Yusubov, Əli Hümbətov, Mehdi Cəfərov, Cəsur İbadli,
Roman Qarayev, Aslan Kotsoyev, Süleyman Şükürov, Davud Namazlı, Canpolad Əliyev, Ramazan Əhmədov, Sübhan Axundov,
Eldar Əliyev, Nərgiz Əhmədova, Gülgəz Musayeva, Gülşən Hüseynova, Nuranə Hacızadə, Aysun Məmmədova, Fəridə Mirzəyeva,
Çinarə Sadıqova, Xədicə Qədəşova, Vüsalə Hacıyeva, Aytən Verdiyeva, Ayan Əliyeva, Nilgün Rzayeva"""
_TRANSLIT = str.maketrans({"ə": "a", "ı": "i", "ö": "o", "ü": "u", "ğ": "gh", "ş": "sh", "ç": "ch", "c": "j", "x": "kh",
                           "q": "g", "j": "zh"})

# --- UEFA: assosiasiyaların Azərbaycan adları (.github/scripts/milli.cjs ilə eyni yazılış) -----------------------------
UEFA_AZ = {
    "ENG": "İngiltərə", "ITA": "İtaliya", "ESP": "İspaniya", "GER": "Almaniya", "FRA": "Fransa", "POR": "Portuqaliya",
    "BEL": "Belçika", "NED": "Hollandiya", "TUR": "Türkiyə", "GRE": "Yunanıstan", "CZE": "Çexiya", "POL": "Polşa",
    "NOR": "Norveç", "DEN": "Danimarka", "CYP": "Kipr", "SUI": "İsveçrə", "AUT": "Avstriya", "HUN": "Macarıstan",
    "CRO": "Xorvatiya", "SWE": "İsveç", "SCO": "Şotlandiya", "ROU": "Rumıniya", "UKR": "Ukrayna", "AZE": "Azərbaycan",
    "ISR": "İsrail", "SVN": "Sloveniya", "SVK": "Slovakiya", "BUL": "Bolqarıstan", "SRB": "Serbiya", "RUS": "Rusiya",
    "ISL": "İslandiya", "IRL": "İrlandiya", "ARM": "Ermənistan", "LVA": "Latviya", "BIH": "Bosniya və Herseqovina",
    "KOS": "Kosovo", "FIN": "Finlandiya", "KAZ": "Qazaxıstan", "LIE": "Lixtenşteyn", "MDA": "Moldova",
    "FRO": "Farer adaları", "ALB": "Albaniya", "MKD": "Şimali Makedoniya", "BLR": "Belarus", "LTU": "Litva",
    "GIB": "Cəbəllütariq", "AND": "Andorra", "MLT": "Malta", "EST": "Estoniya", "GEO": "Gürcüstan",
    "NIR": "Şimali İrlandiya", "LUX": "Lüksemburq", "MNE": "Monteneqro", "WAL": "Uels", "SMR": "San-Marino",
}
EURO_FILES = ("cl", "al", "kl")
CUP_AZ = {"cl": "Çempionlar Liqası", "al": "Avropa Liqası", "kl": "Konfrans Liqası"}


# --- Ümumi köməkçilər -------------------------------------------------------------------------------------------------

def _aware(now):
    return (now if now.tzinfo else now.replace(tzinfo=BAKU)).astimezone(BAKU)


def _iso(s):
    """ISO vaxt -> aware datetime («+0000» və «Z» də oxunur); oxunmursa None."""
    s = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", str(s or "").strip().replace("Z", "+00:00"))
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _ergast_dt(day, hms):
    """Ergast tarix və vaxtı («2026-11-08», «17:00:00Z») -> UTC datetime."""
    try:
        d = datetime.date.fromisoformat(str(day))
        t = datetime.time.fromisoformat(str(hms or "").strip().rstrip("Z")[:8])
    except (TypeError, ValueError):
        return None
    return datetime.datetime.combine(d, t, UTC)


def _int(v, default=None):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _pts(v):
    """Xal: tam ədəd olduqda «390», yarım xal olduqda «12,5»."""
    v = _num(v) or 0.0
    return str(int(v)) if v == int(v) else ox.az_num(v, 1)


def _decimal(s):
    return str(s).replace(".", ",")


def _slot(ready):
    """Hazır olma anı -> dərc vaxtı (Bakı): yarım saata qədər yuxarı; gecədən səhərə (09:30), 22:30-dan sonra ertəsi 10:00."""
    t = ready.astimezone(BAKU).replace(second=0, microsecond=0)
    if t.minute % 30:
        t += datetime.timedelta(minutes=30 - t.minute % 30)
    if t.time() < EARLY:
        return datetime.datetime.combine(t.date(), EARLY, BAKU)
    if t.time() > LATE:
        return datetime.datetime.combine(t.date() + DAY, NEXT_MORNING, BAKU)
    return t


def _tries(first, n):
    """Cəhdlərin başlanğıcı: hamısı eyni Bakı günündə (done günlükdür: günü keçən təkrar ikinci xəbər yarada bilərdi)."""
    out = [first]
    for k in range(1, n):
        t = first + TRY_GAP * k
        if t.date() != first.date() or t.time() > LAST_TRY:
            break
        out.append(t)
    return out


def _try_no(now, tries):
    """now hansı cəhdin pəncərəsindədir (0-dan); heç birində deyilsə None."""
    for k, t in enumerate(tries):
        if t <= now < t + TRY:
            return k
    return None


def _mark(e, k):
    """Cəhdin açarı: son cəhddə xəbərin öz açarı, əvvəlki cəhd alınmayanda «…-cehd1» (ikinci cəhd açıq qalsın)."""
    return e["key"] if k >= len(e["tries"]) - 1 else f"{e['key']}-cehd{k + 1}"


def _skip(e, key, slot, why):
    """Sorğudan sonra dərc olunmayan nəticə: açar done-a düşsün, həmin pəncərədə yenə sorğu getməsin."""
    why = why or "xəbər qurulmadı"
    return {"kind": e["kind"], "key": key, "title": f"{LABEL[e['kind']]}: {e['label']}", "lead": why[:1].upper() + why[1:] + ".",
            "body": [], "list": False, "credit": e["credit"], "link": e["link"], "topic": "idman", "slot": f"{slot:%H:%M}",
            "date": slot.date().isoformat(), "worth": False, "why": why}


def _get(fetch, url, headers=None):
    """JSON sorğusu yalnız fetch ilə; xəta yuxarı ötürülür, onu xəbərin qurucusu tutur."""
    raw = fetch(url, timeout=TIMEOUT, headers=dict(headers or JSON_HEADERS))
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    return json.loads(raw)


def _finish(item):
    text = "\n".join([item["title"], item["lead"], *item["body"]])
    if not fd.leader_free(text):
        return None, "mətndə rəhbərliyin adı keçir"
    if not item["title"] or len(item["title"]) > TITLE_MAX:
        return None, "başlıq çox uzundur"
    return item, ""


def _item(kind, key, title, lead, body, credit, link, slot, listed=False, worth=True, why=""):
    item = {"kind": kind, "key": key, "title": title, "lead": lead, "body": [b for b in body if b], "list": listed,
            "credit": credit, "link": link, "topic": "idman", "slot": f"{slot:%H:%M}", "date": slot.date().isoformat(),
            "worth": worth}
    if not worth:
        item["why"] = why
    return item


def _pick_title(cands):
    for t in cands:
        if t and len(t) <= TITLE_MAX:
            return t
    return ""


def _and(parts):
    parts = [p for p in parts if p]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " və " + parts[-1] if parts else ""


def _range_loc(a, b):
    """Turnirin günləri: «29–31 oktyabrda», «27 fevral – 1 martda», «7 fevralda»."""
    if a == b:
        return ox.day_loc(a)
    if a.month == b.month:
        return f"{a.day}–{ox.day_loc(b)}"
    return f"{ox.day_text(a)} – {ox.day_loc(b)}"


def _back(word):
    return ox._last_vowel(word) in "aıou"


def _abl_az(name):
    """Azərbaycan adının çıxışlıq halı: Ukraynadan, İsraildən, Farer adalarından."""
    poss = " " in name.strip() and ox._low(name)[-1:] in "ıiuü"
    return f"{name}{'n' if poss else ''}{'dan' if _back(name) else 'dən'}"


# --- Formula 1 ----------------------------------------------------------------------------------------------------------

def _utc(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


def _f1_cal(text):
    out = []
    for line in text.strip().splitlines():
        rnd, name, quali, race = line.split("|")
        out.append({"round": int(rnd), "name": name, "quali": _utc(quali), "race": _utc(race)})
    return out


F1_CAL = {2026: _f1_cal(_F1_2026)}


def gp_az(name):
    return GP_AZ.get(name) or ""


def _gp_forms(name):
    """(adlıq, yiyəlik, yerlik): «Braziliya Qran-prisi», «-nin», «-ndə». Lüğətdə olmayan ad dırnaqda, latınca qalır."""
    az = gp_az(name)
    if az.endswith(")"):                       # «Bəhreyn Qran-prisi (Malayziyada)»: şəkilçi mötərizədən əvvəl
        head, tail = az.split(" (", 1)
        return az, f"{head}nin ({tail}", f"{head}ndə ({tail}"
    if az:
        return az, az + "nin", az + "ndə"
    return f"«{name}»", f"«{name}»nin", f"«{name}»də"


def city_az(locality):
    return CITY_AZ.get(locality) or locality


def _team(name):
    return re.sub(r"\s+F1 Team$", "", str(name or "").strip())


def _f1_snd(name):
    tail = F1_PRON.get(name)
    if tail:
        return tail
    words = str(name).split()
    word = ox._low(words[-1] if words else "").translate(fd._FOLD)
    if len(word) > 1 and word[-1] == "y" and word[-2] not in ox._VOWELS:
        word = word[:-1] + "i"
    return word or "a"


def f1_gen(name):
    """Yiyəlik hal, oxunuşa görə: «Norris»in, «Antonelli»nin, «Russell»in (Rassel), «Lawson»un."""
    s = _f1_snd(name)
    return f"«{name}»{'n' if ox._vowel_end(s) else ''}{ox._four(s, ('ın', 'in', 'un', 'ün'))}"


def f1_dat(name):
    """Yönlük hal: «Verstappen»ə, «Leclerc»ə (Leklerk samitlə bitir), «Antonelli»yə, «Hamilton»a."""
    s = _f1_snd(name)
    return f"«{name}»{'y' if ox._vowel_end(s) else ''}{'a' if _back(s) else 'ə'}"


def f1_abl(name):
    """Çıxışlıq hal: «Verstappen»dən, «Norris»dən, «Hamilton»dan."""
    return f"«{name}»{'dan' if _back(_f1_snd(name)) else 'dən'}"


def _race_of(doc, season, rnd):
    """Ergast cavabı -> həmin mövsümün həmin mərhələsi (başqa mərhələ gəlibsə None: köhnə və ya səhv cavab)."""
    if not isinstance(doc, dict):
        return None
    races = ((doc.get("MRData") or {}).get("RaceTable") or {}).get("Races") or []
    for r in races:
        if isinstance(r, dict) and str(r.get("season")) == str(season) and str(r.get("round")) == str(rnd):
            return r
    return None


def _place(r):
    circuit = r.get("Circuit") or {}
    loc = circuit.get("Location") or {}
    baku = circuit.get("circuitId") == "baku" or r.get("raceName") == "Azerbaijan Grand Prix"
    return {"circuit": BAKU_CIRCUIT if baku else str(circuit.get("circuitName") or ""),
            "city": city_az(str(loc.get("locality") or "")), "baku": baku}


def _driver(d):
    d = d or {}
    name = " ".join(p for p in (d.get("givenName"), d.get("familyName")) if p).strip()
    return name, str(d.get("familyName") or name), str(d.get("driverId") or name)


def race_facts(doc, season, rnd):
    """Yarışın nəticəsi -> ({...}, "") və ya (None, səbəb)."""
    r = _race_of(doc, season, rnd)
    if not r:
        return None, "yarışın nəticəsi API-də hələ yoxdur"
    rows = []
    for x in r.get("Results") or []:
        if not isinstance(x, dict):
            continue
        pos = _int(x.get("position"))
        name, family, did = _driver(x.get("Driver"))
        if pos is None or not name:
            continue
        rows.append({"pos": pos, "text": str(x.get("positionText") or ""), "name": name, "family": family, "id": did,
                     "team": _team((x.get("Constructor") or {}).get("name")), "grid": _int(x.get("grid")),
                     "laps": _int(x.get("laps")), "status": str(x.get("status") or ""),
                     "time": str((x.get("Time") or {}).get("time") or ""), "fl": x.get("FastestLap") or {}})
    rows.sort(key=lambda z: z["pos"])
    if len(rows) < MIN_CLASSIFIED or [z["pos"] for z in rows[:3]] != [1, 2, 3]:
        return None, f"yarışın nəticəsi natamamdır ({len(rows)} pilot)"
    if not re.fullmatch(r"\d+:\d\d:\d\d(?:\.\d+)?", rows[0]["time"]) or not rows[0]["laps"] or not rows[0]["team"]:
        return None, "qalibin vaxtı, dövrə sayı və ya komandası yoxdur"
    when = _ergast_dt(r.get("date"), r.get("time"))
    if not when:
        return None, "yarışın tarixi yoxdur"
    f = {"season": int(season), "round": int(rnd), "name": str(r.get("raceName") or ""), "when": when, "rows": rows}
    f.update(_place(r))
    return f, ""


def quali_facts(doc, season, rnd):
    """Kvalifikasiyanın nəticəsi -> ({...}, "") və ya (None, səbəb). Yarışın vaxtı da cavabdadır."""
    r = _race_of(doc, season, rnd)
    if not r:
        return None, "kvalifikasiyanın nəticəsi API-də hələ yoxdur"
    rows = []
    for x in r.get("QualifyingResults") or []:
        if not isinstance(x, dict):
            continue
        pos = _int(x.get("position"))
        name, family, did = _driver(x.get("Driver"))
        if pos is None or not name:
            continue
        times = [str(x.get(k) or "") for k in ("Q1", "Q2", "Q3")]
        rows.append({"pos": pos, "name": name, "family": family, "id": did,
                     "team": _team((x.get("Constructor") or {}).get("name")), "q": times})
    rows.sort(key=lambda z: z["pos"])
    if len(rows) < MIN_CLASSIFIED or [z["pos"] for z in rows[:3]] != [1, 2, 3] or not _best(rows[0]):
        return None, f"kvalifikasiyanın nəticəsi natamamdır ({len(rows)} pilot)"
    f = {"season": int(season), "round": int(rnd), "name": str(r.get("raceName") or ""), "rows": rows,
         "when": _ergast_dt(r.get("date"), r.get("time"))}
    f.update(_place(r))
    return f, ""


def _lap_s(s):
    """«1:27.470» -> 87.47 saniyə; oxunmursa None."""
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", str(s or "").strip())
    if not m:
        return None
    return int(m.group(1) or 0) * 60 + float(m.group(2))


def _best(row):
    """Pilotun son keçdiyi mərhələdəki vaxtı (Q3, yoxsa Q2, yoxsa Q1)."""
    for t in reversed(row["q"]):
        if _lap_s(t) is not None:
            return t
    return ""


def standings(doc, season, rnd, teams=None):
    """Pilotlar cədvəli (həmin mərhələdən sonra) -> [{pos, name, family, team, pts, wins}] və ya None.
    Komanda bu yarışın nəticəsindən götürülür; yoxdursa və pilot mövsümdə bir komandada çıxış edibsə, ondan."""
    if not isinstance(doc, dict):
        return None
    lists = ((doc.get("MRData") or {}).get("StandingsTable") or {}).get("StandingsLists") or []
    for s in lists:
        if not isinstance(s, dict) or str(s.get("season")) != str(season) or str(s.get("round")) != str(rnd):
            continue
        rows = []
        for x in s.get("DriverStandings") or []:
            pos = _int((x or {}).get("position"))
            name, family, did = _driver((x or {}).get("Driver"))
            if pos is None or not name:
                continue
            cons = [_team(c.get("name")) for c in x.get("Constructors") or [] if isinstance(c, dict) and c.get("name")]
            team = (teams or {}).get(did) or (cons[0] if len(cons) == 1 else "")
            rows.append({"pos": pos, "name": name, "family": family, "team": team, "pts": _num(x.get("points")) or 0.0,
                         "wins": _int(x.get("wins"), 0)})
        rows.sort(key=lambda z: z["pos"])
        return rows if len(rows) >= 5 and rows[0]["pos"] == 1 else None
    return None


def _who(row):
    return f"{row['name']} ({row['team']})" if row.get("team") else row["name"]


def _behind(row, win):
    """Qalibdən fərq: «14,602 saniyə», «1 dəqiqə 15,402 saniyə», «1 dövrə»."""
    m = re.fullmatch(r"\+(?:(\d+):)?(\d+(?:\.\d+)?)", row.get("time") or "")
    if m and row.get("laps") == win.get("laps"):
        return (f"{int(m.group(1))} dəqiqə " if m.group(1) else "") + f"{_decimal(m.group(2))} saniyə"
    if row.get("laps") is not None and win.get("laps") and row["laps"] < win["laps"]:
        return f"{win['laps'] - row['laps']} dövrə"
    return ""


def _grid_clause(row):
    g = row.get("grid")
    if g == 1:
        return "birinci yerdən start götürüb "
    if g == 0:
        return "pit-zolaqdan start götürüb "
    return f"{ox.ordinal(g)} yerdən start götürüb " if g else ""


def _table_lines(table, n):
    top = ", ".join(f"{s['pos']}. {_who(s)} – {_pts(s['pts'])} xal" for s in table[:n])
    lines = [f"Çempionatda ilk {'beşlik' if n == 5 else 'üçlük'}: {top}."]
    gap = table[0]["pts"] - table[1]["pts"]
    if gap > 0:
        lines.append(f"Lider {table[0]['name']} ikinci yerdəki {f1_abl(table[1]['family'])} {_pts(gap)} xal öndədir.")
    return lines


def race_item(f, table, slot):
    """Yarışın nəticəsi və çempionatın ilk beşliyi."""
    gp, gp_gen, gp_loc = _gp_forms(f["name"])
    rows = f["rows"]
    win, p2, p3 = rows[0], rows[1], rows[2]
    day = f["when"].astimezone(BAKU)
    where = f["circuit"] + "nda" if f["baku"] else ox.place_loc(f["city"]) if f["city"] else ""
    lead = (f"Formula 1 mövsümünün {ox.ordinal(f['round'])} mərhələsi — {gp} {ox.day_loc(day)} {where} keçirilib. "
            f"{win['team']} pilotu {win['name']} {_grid_clause(win)}{win['laps']} dövrəni {_decimal(win['time'])} vaxtla "
            f"başa vuraraq qalib gəlib.").replace("  ", " ")
    others = []
    for row, place in ((p2, "ikinci"), (p3, "üçüncü")):
        g = row.get("grid")
        start = f"{ox.ordinal(g)} yerdən start götürən " if g and g >= 10 else ""
        gap = _behind(row, win)
        others.append(f"{start}{_who(row)} {('qalibdən ' + gap + ' geri qalaraq ') if gap else ''}{place}")
    lead += " " + others[0][0].upper() + others[0][1:] + ", " + others[1] + " olub."
    body = []
    rest = [r for r in rows if 4 <= r["pos"] <= 10]
    if rest:
        body.append("İlk onluqdakı digər pilotlar: " + ", ".join(f"{r['pos']}. {_who(r)}" for r in rest) + ".")
    fl = next((r for r in rows if str((r["fl"] or {}).get("rank")) == "1"), None)
    fl_time = ((fl or {}).get("fl") or {}).get("Time", {}).get("time") if fl else ""
    if fl and fl_time:
        body.append(f"Ən sürətli dövrəni {_who(fl)} {_decimal(fl_time)} vaxtla keçib.")
    out = {"R": [], "N": [], "W": [], "D": []}
    for r in rows:
        code = "D" if r["text"] in ("D", "E") else r["text"]
        if code in out:
            out[code].append(_who(r))
    stop = []
    if out["R"] or out["N"]:
        stop.append("Yarışı başa vurmayıb: " + ", ".join(out["R"] + out["N"]) + ".")
    if out["W"]:
        stop.append("Start götürməyib: " + ", ".join(out["W"]) + ".")
    if out["D"]:
        stop.append("Diskvalifikasiya olunub: " + ", ".join(out["D"]) + ".")
    if stop:
        body.append(" ".join(stop))
    first_win = False
    if table:
        body += _table_lines(table, 5)
        me = next((s for s in table if s["name"] == win["name"]), None)
        if me and me["wins"]:
            first_win = me["wins"] == 1
            body.append(f"Bu, {f1_gen(win['family'])} mövsümdəki " +
                        ("ilk qələbəsidir." if first_win else f"{ox.ordinal(me['wins'])} qələbəsidir."))
    title = _pick_title([
        f"{win['name']} Bakıda keçirilən {gp_gen} qalibi olub" if f["baku"] else "",
        f"{win['name']} {gp_loc} mövsümdə ilk dəfə qalib gəlib" if first_win else "",
        f"{win['name']} {gp_loc} birinci yerdən start götürüb qalib gəlib" if win.get("grid") == 1 else "",
        f"{win['name']} {gp_gen} qalibi olub",
        f"{win['name']} {gp} qalibi olub",
    ])
    if not title:
        return None, "başlıq çox uzundur"
    key = f"f1-{f['season']}-r{f['round']}-yaris"
    link = f"{F1_API}/{f['season']}/{f['round']}/results.json"
    return _finish(_item("f1-yaris", key, title, lead, body, F1_CREDIT, link, slot, listed=True))


def quali_item(f, slot):
    """Kvalifikasiyanın nəticəsi: ilk üçlük fərqi ilə, ilk onluq, yarışın Bakı vaxtı."""
    gp, gp_gen, gp_loc = _gp_forms(f["name"])
    rows = f["rows"]
    pole, p2, p3 = rows[0], rows[1], rows[2]
    t1 = _best(pole)
    lead = (f"Formula 1 mövsümünün {ox.ordinal(f['round'])} mərhələsi olan {gp_gen} kvalifikasiyasında "
            f"{pole['team']} pilotu {pole['name']} {_decimal(t1)} vaxtla birinci olub.")
    parts = []
    for row, place in ((p2, "ikinci"), (p3, "üçüncü")):
        gap = None
        if pole["q"][2] and row["q"][2]:
            a, b = _lap_s(pole["q"][2]), _lap_s(row["q"][2])
            gap = round(b - a, 3) if a is not None and b is not None and b >= a else None
        if gap is not None:      # fərq hər iki pilot üçün birincinin vaxtından sayılır: bunu mətn də deyir
            parts.append(f"{_who(row)} {f1_abl(pole['family'])} {ox.az_num(gap, 3)} saniyə geri qalaraq {place}")
        else:
            parts.append(f"{_who(row)} {place}")
    lead += f" {parts[0]}, {parts[1]} yeri tutub."
    body = []
    rest = [r for r in rows if 4 <= r["pos"] <= 10]
    if rest:
        body.append("İlk onluqdakı digər pilotlar: " + ", ".join(f"{r['pos']}. {_who(r)}" for r in rest) + ".")
    if f.get("when") and f["when"] > slot:
        race = f["when"].astimezone(BAKU)
        body.append(f"Yarış {ox.day_loc(race)} Bakı vaxtı ilə {ox.time_loc(race)} başlayacaq.")
    title = _pick_title([
        f"{pole['name']} Bakıda {gp_gen} kvalifikasiyasında birinci olub" if f["baku"] else "",
        f"{pole['name']} {gp_gen} kvalifikasiyasında birinci olub",
        f"{pole['name']} kvalifikasiyada birinci olub",
    ])
    key = f"f1-{f['season']}-r{f['round']}-siralama"
    link = f"{F1_API}/{f['season']}/{f['round']}/qualifying.json"
    return _finish(_item("f1-siralama", key, title, lead, body, F1_CREDIT, link, slot))


def preview_ready(doc, slot, season, rnd):
    """Təqvim cavabı ön baxışa yarayır? -> (mərhələ, yarışın vaxtı, "") və ya (None, None, səbəb)."""
    r = _race_of(doc, season, rnd)
    if not r:
        return None, None, "mərhələnin təqvimi API-də yoxdur"
    race = _ergast_dt(r.get("date"), r.get("time"))
    if not race:
        return None, None, "yarışın vaxtı yoxdur"
    if race <= slot:
        return None, None, "yarış artıq keçib"
    if race - slot > PREVIEW_AHEAD:
        return None, None, "təqvim dəyişib: yarış bu həftə sonu deyil"
    return r, race, ""


def preview_item(doc, table, slot, season, rnd, laps_count=None, last_round=None):
    """Yarış həftəsinin ön baxışı: mərhələ, pist, Bakı vaxtı ilə sessiyalar, çempionatın ilk üçlüyü."""
    r, race, why = preview_ready(doc, slot, season, rnd)
    if not r:
        return None, why
    p = _place(r)
    gp, gp_gen, gp_loc = _gp_forms(str(r.get("raceName") or ""))
    rb = race.astimezone(BAKU)
    where = f"{BAKU_CIRCUIT}nda" if p["baku"] else (
        f"{ox.place_loc(p['city'])} ({p['circuit']})" if p["city"] and p["circuit"] else ox.place_loc(p["city"]) if p["city"] else "")
    lead = (f"Formula 1 mövsümünün {ox.ordinal(rnd)} mərhələsi — {gp} {ox.day_loc(rb)} {where} keçiriləcək. "
            f"Yarış Bakı vaxtı ilə {ox.time_loc(rb)} başlayacaq.").replace("  ", " ")
    body = []
    q = _ergast_dt((r.get("Qualifying") or {}).get("date"), (r.get("Qualifying") or {}).get("time"))
    if q:
        qb = q.astimezone(BAKU)
        body.append(f"Kvalifikasiya {ox.day_loc(qb)} Bakı vaxtı ilə {ox.time_loc(qb)} başlayacaq.")
    s = _ergast_dt((r.get("Sprint") or {}).get("date"), (r.get("Sprint") or {}).get("time"))
    if s:
        sb = s.astimezone(BAKU)
        body.append(f"Bu həftə sonu sprint yarışı da keçiriləcək: {ox.day_loc(sb)}, Bakı vaxtı ilə {ox.time_loc(sb)}.")
    if p["baku"] and laps_count:
        body.append(f"Bu, {BAKU_CIRCUIT}nda keçirilən {ox.ordinal(laps_count)} Formula 1 yarışı olacaq.")
    if table:
        lead_row, r2, r3 = table[0], table[1], table[2]
        body.append(f"Çempionatda {_who(lead_row)} {_pts(lead_row['pts'])} xalla liderdir, {_who(r2)} "
                    f"{_pts(r2['pts'])}, {_who(r3)} {_pts(r3['pts'])} xal toplayıb.")
        gap = lead_row["pts"] - r2["pts"]
        if gap > 0:
            body.append(f"Lider ikinci yerdəki {f1_abl(r2['family'])} {_pts(gap)} xal öndədir.")
    # «Las-Veqas Qran-prisi ... Las-Veqasda» təkrarı başlıqda yazılmır
    city_loc = ox.place_loc(p["city"]) if p["city"] and not gp.startswith(p["city"]) else ""
    title = _pick_title([
        f"Formula 1: {gp} bu həftə sonu Bakıda keçiriləcək" if p["baku"] else "",
        f"Formula 1 mövsümünün son mərhələsi — {gp} bu həftə sonu keçiriləcək" if last_round and rnd == last_round else "",
        f"Formula 1: {gp} bu həftə sonu {city_loc} keçiriləcək" if city_loc else "",
        f"Formula 1: {gp} bu həftə sonu keçiriləcək",
    ])
    key = f"f1-{season}-r{rnd}-onbaxis"
    link = f"{F1_API}/{season}/{rnd}.json"
    return _finish(_item("f1-onbaxis", key, title, lead, body, F1_CREDIT, link, slot))


def _baku_count(doc, season, rnd):
    """Bakı Şəhər Halqasında bu yarış daxil neçə Formula 1 yarışı olub (Ergast circuits/baku/races)."""
    races = (((doc or {}).get("MRData") or {}).get("RaceTable") or {}).get("Races") or []
    n = sum(1 for x in races if isinstance(x, dict) and (_int(x.get("season"), 0), _int(x.get("round"), 0)) <= (season, rnd))
    known = any(_int(x.get("season")) == season and _int(x.get("round")) == rnd for x in races if isinstance(x, dict))
    return n if known else None


def f1_make_preview(season, rnd, last_round):
    def make(fetch, at):
        try:
            sched = _get(fetch, f"{F1_API}/{season}/{rnd}.json")
        except Exception as e:
            return None, f"Jolpica alınmadı: {type(e).__name__}"
        r, _, why = preview_ready(sched, at, season, rnd)
        if not r:                 # təqvim yaramırsa əlavə sorğu getmir
            return None, why
        table = None
        if rnd > 1:
            try:
                table = standings(_get(fetch, f"{F1_API}/{season}/{rnd - 1}/driverStandings.json"), season, rnd - 1)
            except Exception:
                table = None
        count = None
        if _place(r)["baku"]:
            try:
                count = _baku_count(_get(fetch, f"{F1_API}/circuits/baku/races.json?limit=100"), season, rnd)
            except Exception:
                count = None
        return preview_item(sched, table, at, season, rnd, count, last_round)
    return make


def f1_make_quali(season, rnd):
    def make(fetch, at):
        try:
            doc = _get(fetch, f"{F1_API}/{season}/{rnd}/qualifying.json")
        except Exception as e:
            return None, f"Jolpica alınmadı: {type(e).__name__}"
        f, why = quali_facts(doc, season, rnd)
        if not f:
            return None, why
        when = f.get("when")
        if when and not (at - DAY < when < at + PREVIEW_AHEAD):
            return None, "kvalifikasiyanın nəticəsi bu həftə sonuna aid deyil (təqvim dəyişib)"
        return quali_item(f, at)
    return make


def f1_make_race(season, rnd):
    def make(fetch, at):
        try:
            doc = _get(fetch, f"{F1_API}/{season}/{rnd}/results.json")
        except Exception as e:
            return None, f"Jolpica alınmadı: {type(e).__name__}"
        f, why = race_facts(doc, season, rnd)
        if not f:
            return None, why
        if f["when"] > at:
            return None, "yarış hələ keçirilməyib (cavab köhnə və ya səhvdir)"
        if at - f["when"] > STALE:
            return None, "yarışın nəticəsi köhnədir (təqvim dəyişib)"
        teams ={r["id"]: r["team"] for r in f["rows"]}
        try:
            table = standings(_get(fetch, f"{F1_API}/{season}/{rnd}/driverStandings.json"), season, rnd, teams)
        except Exception:
            table = None   # cədvəl gecikəndə nəticə onsuz da xəbərdir
        return race_item(f, table, at)
    return make


def f1_events(year):
    """Mövsümün F1 hadisələri: ön baxış (cümə axşamı 11:00), kvalifikasiya və yarış (hazır olandan sonra)."""
    cal = F1_CAL.get(year) or []
    last = max((c["round"] for c in cal), default=None)
    evs = []
    for c in cal:
        rnd, race = c["round"], c["race"]
        thursday = race.date() - DAY * ((race.weekday() - 3) % 7)
        pv = datetime.datetime.combine(thursday, PREVIEW_AT, BAKU)
        label = gp_az(c["name"]) or c["name"]
        src = {"label": label, "credit": F1_CREDIT, "link": f"{F1_API}/{year}/{rnd}.json"}
        evs.append(dict(src, kind="f1-onbaxis", key=f"f1-{year}-r{rnd}-onbaxis", tries=_tries(pv, 2),
                        make=f1_make_preview(year, rnd, last)))
        evs.append(dict(src, kind="f1-siralama", key=f"f1-{year}-r{rnd}-siralama",
                        tries=_tries(_slot(c["quali"] + QUALI_READY), 2), make=f1_make_quali(year, rnd)))
        evs.append(dict(src, kind="f1-yaris", key=f"f1-{year}-r{rnd}-yaris", tries=_tries(_slot(race + RACE_READY), 2),
                        make=f1_make_race(year, rnd)))
    return evs


# --- Cüdo ---------------------------------------------------------------------------------------------------------------

def _cudo_cal(text):
    out = []
    for line in text.strip().splitlines():
        cid, rank, city, a, b, off = line.split("|")
        out.append({"id": cid, "rank": rank, "city": city, "from": datetime.date.fromisoformat(a),
                    "to": datetime.date.fromisoformat(b), "tz": datetime.timezone(datetime.timedelta(hours=int(off)))})
    return out


CUDO_CAL = _cudo_cal(_CUDO)


def _key(k):
    return (0, int(k)) if str(k).isdigit() else (1, str(k))


def judo_cats(doc):
    """IJF competition.results -> ([{cat, persons}] çəki sırası ilə, "") və ya (None, səbəb). Hər çəkidə 1, 2 və 3-cü yer
    bəlli olmalıdır: turnir hələ gedirsə, xəbər gözləyir."""
    bc = doc.get("by_categories") if isinstance(doc, dict) else None
    if not isinstance(bc, dict) or not bc:
        return None, "IJF nəticələri hələ yoxdur"
    cats = []
    for g in sorted(bc, key=_key):
        group = bc[g]
        if not isinstance(group, dict):
            continue
        for c in sorted(group, key=_key):
            cat = group[c] if isinstance(group[c], dict) else {}
            persons = [p for p in cat.get("persons") or [] if isinstance(p, dict)]
            cats.append({"cat": str(cat.get("category") or ""), "persons": persons})
    if len(cats) < JUDO_CATS:
        return None, f"IJF nəticələri natamamdır ({len(cats)} çəki)"
    for c in cats:
        places = {str(p.get("place")) for p in c["persons"]}
        if not {"1", "2", "3"} <= places:
            return None, f"{c['cat']} kq çəkisində medallar hələ bəlli deyil"
    return cats, ""


def _roster():
    out = {}
    for name in _ROSTER.replace("\n", " ").split(","):
        name = " ".join(name.split())
        if name:
            out[ox._low(name).translate(_TRANSLIT)] = name
    return out


ROSTER = _roster()


def judoka_name(p):
    """Azərbaycan cüdoçusunun adı: federasiyanın yazılışı (id ilə, sonra çevrilmiş adla), yoxsa IJF-in latın yazılışı."""
    pid = str(p.get("id_person") or "")
    if pid in AZ_JUDOKA:
        return AZ_JUDOKA[pid]
    given = " ".join(str(p.get("given_name") or "").split())
    family = " ".join(str(p.get("family_name") or "").split())
    key = ox._low(f"{given} {family}").strip()
    if key in ROSTER:
        return ROSTER[key]
    return " ".join(x for x in (given, family.title()) if x)


def medal_table(cats):
    t = {}
    for c in cats:
        for p in c["persons"]:
            code, place = str(p.get("country_short") or ""), str(p.get("place"))
            if code and place in ("1", "2", "3"):
                t.setdefault(code, [0, 0, 0])[int(place) - 1] += 1
    return t


def medal_rank(table, code="AZE"):
    """Medal sıralamasında yer (qızıl, gümüş, bürünc sırası ilə). Başqa ölkə ilə tam bərabərdirsə None: yer yazılmır."""
    me = tuple(table.get(code) or (0, 0, 0))
    if me == (0, 0, 0) or any(tuple(v) == me for k, v in table.items() if k != code):
        return None
    return 1 + sum(1 for k, v in table.items() if k != code and tuple(v) > me)


_PLACE_WORD = {1: "birinci", 2: "ikinci", 3: "üçüncü"}


def judo_item(ev, cats, slot):
    """Turnirdə Azərbaycan cüdoçularının medalları; medal yoxdursa xəbər deyil."""
    groups = {}
    for c in cats:
        for p in c["persons"]:
            if p.get("country_short") == "AZE":
                place = _int(p.get("place"))
                if place in (1, 2, 3, 5, 7):
                    groups.setdefault(place, []).append(f"{judoka_name(p)} ({c['cat']} kq)")
    gold, silver, bronze = (len(groups.get(k) or []) for k in (1, 2, 3))
    total = gold + silver + bronze
    city = JUDO_CITY.get(ev["city"]) or ev["city"]
    rank_name = JUDO_RANK.get(ev["rank"]) or ev["rank"]
    worlds = ev["rank"] == "World Championships"
    event = f"Cüdo üzrə dünya çempionatı ({city})" if worlds else f"{city} {rank_name}"
    key = f"cudo-ijf-{ev['id']}"
    link = IJF_PAGE.format(ev["id"])
    if not total:
        return None, "Azərbaycan cüdoçuları medal qazanmayıb"
    counts = _and([f"{n} {w}" for n, w in ((gold, "qızıl"), (silver, "gümüş"), (bronze, "bürünc")) if n])
    lead = (f"{_range_loc(ev['from'], ev['to'])} {ox.place_loc(city)} keçirilən {rank_name}nda" if worlds else
            f"{_range_loc(ev['from'], ev['to'])} {ox.place_loc(city)} keçirilən {rank_name}ndə")
    lead += f" Azərbaycan cüdoçuları {total} medal qazanıb: {counts}."
    said = []
    if groups.get(1):
        said.append(f"{_and(groups[1])} qalib gəlib")
    rest = [f"{_and(groups[k])} {_PLACE_WORD[k]}" for k in (2, 3) if groups.get(k)]
    if rest:
        said.append(", ".join(rest) + " olub")
    lead += " " + ", ".join(said) + "."
    body = []
    low = [f"{_and(groups[k])} {w}" for k, w in ((5, "beşinci"), (7, "yeddinci")) if groups.get(k)]
    if low:
        body.append(", ".join(low) + " yeri tutub.")
    rank = medal_rank(medal_table(cats))
    # dünya çempionatında komanda yarışı da olur: buradakı sıralama yalnız fərdi çəkilərdəndir, mətn də bunu deyir
    table_name = "fərdi yarışların medal sıralamasında" if worlds else "medal sıralamasında"
    if rank:
        body.append(f"Azərbaycan yığması {table_name} " +
                    (f"{_PLACE_WORD[rank]} olub." if rank in _PLACE_WORD else f"{ox.ordinal(rank)} yeri tutub."))
    single = next(iter(groups.get(1) or groups.get(2) or groups.get(3) or []), "")
    medal = "qızıl" if gold else "gümüş" if silver else "bürünc"
    title = _pick_title([
        f"{event}: Azərbaycan yığması {table_name} birinci olub" if rank == 1 and total >= 2 else "",
        f"{event}: {single} {medal} medal qazanıb" if total == 1 else "",
        f"{event}: Azərbaycan cüdoçuları {counts} medal qazanıb",
        f"{event}: Azərbaycan cüdoçuları {total} medal qazanıb",
    ])
    if not title:
        return None, "başlıq çox uzundur"
    return _finish(_item("cudo", key, title, lead[0].upper() + lead[1:], body, IJF_CREDIT, link, slot))


def judo_url(cid):
    q = urllib.parse.urlencode({"params[action]": "competition.results", "params[id_competition]": cid})
    return IJF_API + q


def judo_list_url(year):
    return IJF_API + urllib.parse.urlencode({"params[action]": "competition.get_list", "params[year]": year})


def judo_make(ev):
    def make(fetch, at):
        try:
            doc = _get(fetch, judo_url(ev["id"]))
        except Exception as e:
            return None, f"IJF alınmadı: {type(e).__name__}"
        cats, why = judo_cats(doc)
        if not cats:
            return None, why
        return judo_item(ev, cats, at)
    return make


def judo_slot(ev):
    """Son günün yerli 21:00-ı Bakı vaxtı ilə, gecəyə düşürsə səhərə keçir (Avropa və Amerika turnirləri: ertəsi gün 09:30)."""
    return _slot(datetime.datetime.combine(ev["to"], JUDO_LOCAL_READY, ev["tz"]))


def judo_events(cal=None):
    evs = []
    for ev in CUDO_CAL if cal is None else cal:     # boş siyahı boş qalır: «or» bütün təqvimi qaytarırdı
        city = JUDO_CITY.get(ev["city"]) or ev["city"]
        evs.append({"kind": "cudo", "key": f"cudo-ijf-{ev['id']}", "tries": _tries(judo_slot(ev), 1),
                    "label": f"{city} {JUDO_RANK.get(ev['rank']) or ev['rank']}", "make": judo_make(ev), "event": ev,
                    "credit": IJF_CREDIT, "link": IJF_PAGE.format(ev["id"])})
    return evs


# --- UEFA ölkə əmsalları --------------------------------------------------------------------------------------------------

def euro_weeks(root):
    """Saytın avrokubok fayllarından həftələr: {"check": yoxlama vaxtı (Bakı 11:00), "last": son oyunun başlanğıcı,
    "az": Azərbaycan klublarının həftədəki nəticəsi {w, d, l} və ya None (nəticə hələ yoxdursa)}."""
    weeks = {}
    for name in EURO_FILES:
        try:
            doc = json.loads((pathlib.Path(root) / "data" / "futbol" / f"{name}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for g in (doc.get("games") if isinstance(doc, dict) else None) or []:
            if not isinstance(g, dict):
                continue
            t = _iso(g.get("date"))
            if not t:
                continue
            wk = weeks.setdefault(t.isocalendar()[:2], {"last": t, "games": []})
            wk["last"] = max(wk["last"], t)
            wk["games"].append(g)
    out = []
    for _, wk in sorted(weeks.items()):
        ready = (wk["last"] + UEFA_LAG).astimezone(BAKU)
        check = datetime.datetime.combine(ready.date(), UEFA_AT, BAKU)
        if check < ready:
            check += DAY
        res, known = {"w": 0, "d": 0, "l": 0}, True
        for g in wk["games"]:
            home, away = g.get("home") in fd.AZ_CLUBS, g.get("away") in fd.AZ_CLUBS
            if not home and not away:
                continue
            hs, as_ = _int(g.get("hs")), _int(g.get("as"))
            if not g.get("played") or hs is None or as_ is None:
                known = False
                continue
            mine, theirs = (hs, as_) if home else (as_, hs)
            res["w" if mine > theirs else "d" if mine == theirs else "l"] += 1
        out.append({"check": check, "last": wk["last"], "az": res if known else None})
    return out


def _uefa_year(day):
    """UEFA-nın «seasonYear»-i mövsümün bitdiyi ildir: 2026/27 -> 2027 (yeni mövsüm iyulda başlayır)."""
    return day.year + 1 if day.month >= 7 else day.year


def uefa_checks(root, year):
    """İlin yoxlama günləri: saytın avrokubok həftələri və iyul–avqustun cümələri (seçmə mərhələlər saytda yoxdur)."""
    seen = {}
    for wk in euro_weeks(root):
        if wk["check"].year == year:
            seen[wk["check"].date()] = wk
    d = datetime.date(year, 7, 1)
    while d.month in (7, 8):
        if d.weekday() == 4 and d not in seen:
            seen[d] = {"check": datetime.datetime.combine(d, UEFA_AT, BAKU), "last": None, "az": None}
        d += DAY
    return [seen[k] for k in sorted(seen)]


def uefa_facts(doc, code="AZE"):
    """UEFA cavabı -> ({...}, "") və ya (None, səbəb)."""
    data = doc.get("data") if isinstance(doc, dict) else None
    members = (data or {}).get("members") if isinstance(data, dict) else None
    if not isinstance(members, list) or not members:
        return None, "UEFA cədvəli boşdur"
    rows = []
    for m in members:
        if not isinstance(m, dict):
            continue
        mem, ov = m.get("member") or {}, m.get("overallRanking") or {}
        pos, pts = _int(ov.get("position")), _num(ov.get("totalPoints"))
        if pos is None or pts is None:
            continue
        season = next((s for s in m.get("seasonRankings") or [] if isinstance(s, dict)
                       and _int(s.get("seasonYear")) == _int(ov.get("targetSeasonYear"))), None)
        rows.append({"code": str(mem.get("countryCode") or ""), "pos": pos, "pts": pts,
                     "trend": str(ov.get("trend") or "STABLE").upper(), "teams": _int(ov.get("numberOfTeams")),
                     "still": _int(ov.get("numberOfTeamsStillInPlaying")), "year": _int(ov.get("targetSeasonYear")),
                     "season": season})
    me = next((r for r in rows if r["code"] == code), None)
    if not me:
        return None, "Azərbaycan cədvəlin bu səhifəsində yoxdur"
    upd = _iso(data.get("lastUpdateDate"))
    if not upd:
        return None, "cədvəlin yenilənmə tarixi yoxdur"
    by_pos = {r["pos"]: r for r in rows}
    return {"me": me, "up": by_pos.get(me["pos"] - 1), "down": by_pos.get(me["pos"] + 1), "updated": upd}, ""


def _still_text(teams, still):
    words = {1: "biri", 2: "ikisi", 3: "üçü", 4: "dördü"}
    if teams and still == 0:
        return "Avrokuboklarda mübarizəni davam etdirən Azərbaycan klubu qalmayıb."
    if teams and still and still in words:
        return f"{teams} klubdan {words[still]} avrokuboklarda mübarizəni davam etdirir."
    return ""


def uefa_item(facts, week, slot, year):
    """Azərbaycanın yeri dəyişibsə (UEFA-nın trend sahəsi) və ya klublar həftədə xal qazanıbsa xəbər; yoxsa worth=False."""
    me, up, down, upd = facts["me"], facts["up"], facts["down"], facts["updated"].astimezone(BAKU)
    total, pos = ox.az_num(me["pts"], 3), ox.ordinal(me["pos"])
    moved = me["trend"] in ("UP", "DOWN")
    az = week.get("az") if week else None
    scored = bool(az and (az["w"] or az["d"]))
    # UEFA cədvəli gecə yeniləyir: 5 noyabr 21:57 UTC Bakıda 6 noyabrdır. «tarixli» yox, «yenilənmiş»: gün Bakı vaxtı ilədir
    head = f"UEFA-nın {ox.day_loc(upd)} yenilənmiş ölkə əmsalları cədvəlində Azərbaycan {total} xalla"
    if moved:
        verb = "yüksəlib" if me["trend"] == "UP" else "düşüb"
        title = f"UEFA reytinqi: Azərbaycan {pos} pilləyə {verb}"
        lead = f"{head} {pos} yerə {verb}."
    else:
        title = f"UEFA reytinqi: Azərbaycan {total} xalla {pos} yerdədir"
        lead = f"{head} {pos} yeri tutur."
    if scored:
        did = _and([f"{az['w']} qələbə qazanıb" if az["w"] else "", f"{az['d']} dəfə heç-heçə edib" if az["d"] else ""])
        lead += f" Azərbaycan klubları bu həftə avrokuboklarda {did}."
    body = []
    s = me.get("season")
    if s and _num(s.get("totalPoints")) is not None and me.get("year"):
        y = me["year"]
        spos = _int(s.get("position"))
        body.append(f"Azərbaycan klubları {y - 1}/{str(y)[2:]} mövsümündə {ox.az_num(_num(s.get('totalPoints')), 3)} xal "
                    f"toplayıb" + (f" (mövsüm cədvəlində {ox.ordinal(spos)} yer)." if spos else "."))
    body.append(_still_text(me.get("teams"), me.get("still")))
    near = []
    if up:
        near.append(f"bir pillə yuxarıda {UEFA_AZ.get(up['code'], up['code'])} ({ox.az_num(up['pts'], 3)} xal)")
    if down:
        near.append(f"bir pillə aşağıda {UEFA_AZ.get(down['code'], down['code'])} ({ox.az_num(down['pts'], 3)} xal)")
    if near:
        text = _and(near) + " qərarlaşıb."
        body.append(text[0].upper() + text[1:])
    gaps = []
    if up and up["pts"] > me["pts"]:
        gaps.append(f"{_abl_az(UEFA_AZ.get(up['code'], up['code']))} {ox.az_num(up['pts'] - me['pts'], 3)} xal geri qalır")
    if down and down["pts"] < me["pts"]:
        gaps.append(f"{_abl_az(UEFA_AZ.get(down['code'], down['code']))} {ox.az_num(me['pts'] - down['pts'], 3)} xal öndədir")
    if gaps:
        body.append("Azərbaycan " + ", ".join(gaps) + ".")
    key = f"uefa-emsal-{slot.date().isoformat()}"
    worth = moved or scored
    why = "" if worth else ("Azərbaycanın yeri dəyişməyib və klublar bu həftə xal qazanmayıb" if az else
                            "Azərbaycanın yeri dəyişməyib (klubların həftəlik nəticəsi saytda yoxdur)")
    item = _item("uefa-emsal", key, title, lead, body, UEFA_CREDIT, UEFA_PAGE.format(year), slot, worth=worth, why=why)
    out, bad = _finish(item)
    return (out, why) if out else (None, bad)


def uefa_make(week, year):
    def make(fetch, at):
        try:
            doc = _get(fetch, UEFA_API.format(year))
        except Exception as e:
            return None, f"UEFA alınmadı: {type(e).__name__}"
        facts, why = uefa_facts(doc)
        if not facts:
            return None, why
        upd = facts["updated"]
        if upd > at:
            return None, "cədvəlin tarixi gələcəkdədir"
        if week.get("last") is not None and upd < week["last"] + HOUR:
            return None, "UEFA cədvəli bu həftənin oyunlarından sonra hələ yenilənməyib"
        if week.get("last") is None and upd < at - 3 * DAY:
            return None, "UEFA cədvəli son 3 gündə yenilənməyib"
        return uefa_item(facts, week, at, year)
    return make


def uefa_events(root, year):
    evs = []
    for wk in uefa_checks(root, year):
        day = wk["check"].date()
        if day.month == 6:
            continue
        season = _uefa_year(day)
        evs.append({"kind": "uefa-emsal", "key": f"uefa-emsal-{day.isoformat()}", "tries": [wk["check"]],
                    "label": "UEFA ölkə əmsalları", "make": uefa_make(wk, season), "week": wk,
                    "credit": UEFA_CREDIT, "link": UEFA_PAGE.format(season)})
    return evs


# --- Plan və items() ------------------------------------------------------------------------------------------------------

def events(root, year):
    """İlin bütün hadisələri (vaxtdan asılı olmayaraq): {kind, key, tries, label, make(fetch, at) -> (xəbər, səbəb)}."""
    evs = f1_events(year) + judo_events([e for e in CUDO_CAL if e["to"].year == year]) + uefa_events(root, year)
    return sorted(evs, key=lambda e: (e["tries"][0], PRIO[e["kind"]], e["key"]))


def day_events(root, day):
    out = []
    for year in sorted({day.year, (day - DAY).year}):
        out += [e for e in events(root, year) if e["tries"][0].date() == day]
    return out


def _default_fetch():
    def fetch(url, timeout=TIMEOUT, headers=None):
        return ox._u().fetch(url, timeout=timeout, headers=headers)
    return fetch


def items(root, now, fetch=None, done=None):
    """now anında (Bakı) dərc olunacaq xəbərlər (worth=True) və sorğusu getmiş, amma dərc olunmayan nəticələr
    (worth=False, «why» ilə). Sorğu yalnız cəhd pəncərəsindəki, açarı done-da olmayan xəbər üçün gedir; qaytarılan hər
    açar done-a yazılanda pəncərədə bir dəfə sorğu olur. Xəbər pəncərənin başlanğıc anı üçün qurulur (sınaqdakı kimi).
    Heç vaxt xəta qaldırmır: mənbə alınmayanda həmin xəbər çıxmır."""
    try:
        now = _aware(now)
        fetch = fetch or _default_fetch()
        done = set(done or ())
        good, rest = [], []
        for e in day_events(root, now.date()):
            k = _try_no(now, e["tries"])
            if k is None or e["key"] in done or _mark(e, k) in done:
                continue
            at = e["tries"][k]
            try:
                item, why = e["make"](fetch, at)
            except Exception as ex:
                item, why = None, f"xəta: {type(ex).__name__}"
            if item and item.get("worth"):
                good.append(item)
            elif item and item.get("key") == _mark(e, k):
                rest.append(item)                       # tam mətnli, amma xəbər olmayan nəticə (UEFA: dəyişməyib)
            else:
                if k < len(e["tries"]) - 1:
                    why = f"{why or 'xəbər qurulmadı'}; növbəti cəhd {ox.time_loc(e['tries'][k + 1])}"
                rest.append(_skip(e, _mark(e, k), at, why))
        good.sort(key=lambda i: (PRIO[i["kind"]], i["slot"], i["key"]))
        for item in good[DAILY_CAP:]:
            item["worth"], item["why"] = False, f"bir dəfəyə ən çox {DAILY_CAP} xəbər dərc olunur"
        return good + rest
    except Exception:
        return []


# --- Sınaq ----------------------------------------------------------------------------------------------------------------

def _paced(fetch, log):
    """Sınaq: eyni hosta sorğular arasında 1 saniyə fasilə, hər sorğu sayılır."""
    last = {}

    def run(url, timeout=TIMEOUT, headers=None):
        host = urllib.parse.urlsplit(url).netloc
        wait = SEC_PAUSE - (time.monotonic() - last.get(host, -10.0))
        if wait > 0:
            time.sleep(wait)
        log.append(host)
        try:
            return fetch(url, timeout=timeout, headers=headers)
        finally:
            last[host] = time.monotonic()
    return run


def _when(e):
    t = e["tries"][0]
    return f"{ox.day_text(t)} {t.year}, {t:%H:%M}"


def _verdict(item, why):
    if item and item.get("worth"):
        return ["✅ Dərc olunardı", ""]
    return [f"⏭ Dərc olunmazdı: {(item or {}).get('why') or why}", ""]


def _case(e, fetch, note=""):
    md = [f"**{LABEL[e['kind']]} · {_when(e)}** · `{e['key']}`" + (f" · {note}" if note else ""), ""]
    try:
        item, why = e["make"](fetch, e["tries"][0])
    except Exception as ex:
        item, why = None, f"xəta: {type(ex).__name__}"
    if item:
        md += ox.render(item)
    return md + _verdict(item, why)


def calendar_check(fetch, year):
    """Modulun təqvimləri API ilə: F1 (mövsümün təqvimi) və IJF (ilin siyahısı). Fərq varsa sətir-sətir."""
    md = []
    cal = F1_CAL.get(year) or []
    try:
        doc = _get(fetch, f"{F1_API}/{year}.json")
        races = {}
        for r in ((doc.get("MRData") or {}).get("RaceTable") or {}).get("Races") or []:
            q = r.get("Qualifying") or {}
            races[_int(r.get("round"))] = (r.get("raceName"), _ergast_dt(q.get("date"), q.get("time")),
                                           _ergast_dt(r.get("date"), r.get("time")))
        diff = [f"{c['round']}-ci mərhələ" for c in cal if races.get(c["round"]) != (c["name"], c["quali"], c["race"])]
        diff += [f"API-də əlavə mərhələ {k}" for k in races if k not in {c["round"] for c in cal}]
        md.append(f"- F1 {year}: " + (f"modulun təqvimi API ilə eynidir ({len(cal)} mərhələ)." if not diff and cal else
                                      "⚠ fərq var: " + ", ".join(diff[:8]) if diff else "⚠ modulda bu ilin təqvimi yoxdur."))
    except Exception as e:
        md.append(f"- F1 {year}: Jolpica alınmadı ({type(e).__name__}).")
    if not F1_CAL.get(year + 1):
        md.append(f"- F1 {year + 1}: modulda təqvim yoxdur; API-də çıxanda F1_CAL-a əlavə olunmalıdır.")
    for y in (year, year + 1):
        mine = [e for e in CUDO_CAL if e["to"].year == y]
        try:
            rows = _get(fetch, judo_list_url(y))
            live = {}
            for c in rows if isinstance(rows, list) else []:
                if c.get("rank_name") in JUDO_RANK and str(c.get("is_teams")) != "1" and list(c.get("ages") or []) == ["sen"]:
                    live[str(c.get("id_competition"))] = (c.get("rank_name"), c.get("city"), str(c.get("date_from")).replace("/", "-"),
                                                          str(c.get("date_to")).replace("/", "-"))
            ours = {e["id"]: (e["rank"], e["city"], e["from"].isoformat(), e["to"].isoformat()) for e in mine}
            diff = [f"{k} ({live[k][1]})" for k in live if ours.get(k) != live[k]] + [f"{k} siyahıda yoxdur" for k in ours if k not in live]
            md.append(f"- IJF {y}: " + (f"modulun təqvimi siyahı ilə eynidir ({len(ours)} turnir)." if not diff else
                                        "⚠ fərq var: " + ", ".join(diff[:8])))
        except Exception as e:
            md.append(f"- IJF {y}: siyahı alınmadı ({type(e).__name__}).")
    return md


def _latest(evs, kind, now, n=1, pred=None):
    past = [e for e in evs if e["kind"] == kind and e["tries"][0] <= now and (pred is None or pred(e))]
    return past[-n:]


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu günün planı, təqvimlərin yoxlanışı və hər növün son real halı, öz slot vaxtında qurulmuş."""
    now = _aware(now or datetime.datetime.now(BAKU))
    log = []
    fetch = _paced(fetch or _default_fetch(), log)
    md = ["## İdman: Formula 1, cüdo və UEFA ölkə əmsalları (oz_idman2.py)", "",
          f"Sınaq vaxtı: {now:%d.%m.%Y %H:%M} (Bakı). Mənbələr: Jolpica F1 API, IJF data API, UEFA (comp.uefa.com). "
          f"Canlıda sorğu yalnız xəbərin {int(TRY.total_seconds() // 60)} dəqiqəlik pəncərəsində və pəncərədə bir dəfə gedir "
          f"(adi gündə 0–3, ən çox 6).", ""]
    try:
        evs = []
        for y in (now.year - 1, now.year):
            evs += events(root, y)
        evs.sort(key=lambda e: (e["tries"][0], PRIO[e["kind"]], e["key"]))
    except Exception as e:
        return md + [f"> Plan qurulmadı: {type(e).__name__}", ""]
    today = [e for e in evs if e["tries"][0].date() == now.date()]
    md += [f"### Bu gün, {ox.day_text(now)}: plan", ""]
    for e in today:
        state = ("slotu gəlməyib" if now < e["tries"][0] else "pəncərədədir" if _try_no(now, e["tries"]) is not None
                 else "pəncərə keçib")
        md.append(f"- {', '.join(f'{t:%H:%M}' for t in e['tries'])} · {LABEL[e['kind']]} · {e['label']} · `{e['key']}` — {state}")
    if not today:
        md.append("- Bu gün üçün planda xəbər yoxdur.")
    nxt = [e for e in evs if e["tries"][0] > now][:5]
    if nxt:
        md += ["", "Növbəti planlı xəbərlər:"] + [f"- {_when(e)} · {LABEL[e['kind']]} · {e['label']} · `{e['key']}`" for e in nxt]
    md += ["", "### Təqvimlərin yoxlanışı", ""] + calendar_check(fetch, now.year) + [""]
    md += ["### Son real hallar (hərəsi öz slot vaxtında qurulub)", ""]
    for kind in ("f1-onbaxis", "f1-siralama", "f1-yaris"):
        for e in _latest(evs, kind, now):
            md += _case(e, fetch)
    for e in _latest(evs, "f1-yaris", now, pred=lambda e: "Azərbaycan" in e["label"]):
        if e not in _latest(evs, "f1-yaris", now):
            md += _case(e, fetch, "Bakı mərhələsi")
    for e in _latest(evs, "cudo", now, n=2):
        md += _case(e, fetch)
    for e in _latest(evs, "uefa-emsal", now):
        md += _case(e, fetch)
    md += [f"<sub>Bu sınaq {len(log)} sorğu göndərdi: " +
           ", ".join(f"{h} {log.count(h)}" for h in sorted(set(log))) + ".</sub>", ""]
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    when = _arg(argv, "--now")
    now = _iso(when) if when else None
    if when and now is None:
        print(f"--now oxunmadı: {when}", file=sys.stderr)
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
