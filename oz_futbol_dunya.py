"""Xarici futbol və basketbol üzrə 8ulduz-un öz xəbərləri: data/futbol/*.json-dan şablon mətnlər (faza 1).

Sahibin qərarı (2026-11-10): «Bəli, başla». Faza 1 sınaq budağında qurulur, sayta qoşulmur:
updater.py və pipeline.sh bu faylı çağırmır. Nümunələri `python oz_futbol_dunya.py --sinaq --root DIR` çıxarır.
Hər rəqəm, ad və tarix saytın artıq yığdığı fayllardandır. Şəbəkə sorğusu yoxdur.

Xəbər növləri:
1. Top liqalarda tur icmalı (İngiltərə, İspaniya, İtaliya, Almaniya, Fransa, Türkiyə), tur başa çatanda.
2. Digər çempionatlar (Portuqaliya, Hollandiya, Belçika, Şotlandiya, Rusiya, Braziliya, Çempionşip): gündə ən çox bir ümumi xəbər.
3. Bazar ertəsi: Avropa çempionatlarında liderlər, məğlubiyyətsiz komandalar, qələbə seriyaları.
4. Xarici kuboklar: mərhələ başa çatanda, yalnız böyük klub oynayıbsa.
5. Avrokubok turu (ÇL, AL, KL): yarış və tur başına bir xəbər, səhər 08:00-da. «Sabah» burada yazılmır, onu başqa modul yazır.
6. Böyük klubun oyunu: yalnız saytın izlədiyi klublar, həmin gün tur icmalına düşməyən oyun, gündə ən çox 3.
7. NBA: ABŞ-ın ötən gününün bütün oyunları bitəndə (slot 09:00). Vikipediya nəticələri gün ərzində dəyişə bilər.
8. Avroliqa (basketbol): tur başa çatanda, məlumat təzədirsə.
Bu moduldan gündə ən çox 8 xəbər çıxır.
"""
import datetime
import html
import json
import pathlib
import re
import sys

import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
SEC = datetime.timedelta(seconds=1)
POSTPONED = datetime.timedelta(days=3)   # turun median vaxtından 3 gündən çox sonraya salınan oyun təxirə salınmış sayılır
FOOT_READY = datetime.timedelta(hours=2, minutes=45)    # başlama vaxtından nəticənin fayla düşməsinədək (TheSportsDB ~1 saat gecikir)
CUP_READY = datetime.timedelta(hours=3, minutes=15)     # kubok: əlavə vaxt və penaltilər seriyası
BASKET_READY = datetime.timedelta(hours=2, minutes=45)
MIN_GAME = datetime.timedelta(minutes=105)  # oyun bundan tez bitmir (90 dəqiqə + fasilə)
LATE = datetime.timedelta(hours=14)      # məlumat gecikəndə xəbər slotdan bu qədər sonraya kimi dərc oluna bilər
DAILY_CAP = 8
CLUB_CAP = 3
LEADERS_MIN = 6                          # bazar ertəsi xəbəri: son həftə ən azı bu qədər çempionatda oyun olmalıdır
TITLE_MAX = 110

TOP = {
    "ingiltere": {"loc": "İngiltərə Premyer Liqasında", "gen": "İngiltərə Premyer Liqasının", "land": "İngiltərə", "in": "İngiltərədə"},
    "ispaniya": {"loc": "İspaniya La Liqasında", "gen": "İspaniya La Liqasının", "land": "İspaniya", "in": "İspaniyada"},
    "italiya": {"loc": "İtaliya A Seriyasında", "gen": "İtaliya A Seriyasının", "land": "İtaliya", "in": "İtaliyada"},
    "almaniya": {"loc": "Almaniya Bundesliqasında", "gen": "Almaniya Bundesliqasının", "land": "Almaniya", "in": "Almaniyada"},
    "fransa": {"loc": "Fransa çempionatında", "gen": "Fransa çempionatının", "land": "Fransa", "in": "Fransada"},
    "turkiye": {"loc": "Türkiyə Super Liqasında", "gen": "Türkiyə Super Liqasının", "land": "Türkiyə", "in": "Türkiyədə"},
}
OTHER = {
    "portuqaliya": {"label": "Portuqaliya (Primeyra Liqa)", "land": "Portuqaliya", "in": "Portuqaliyada", "eu": True},
    "hollandiya": {"label": "Hollandiya (Eredivizie)", "land": "Hollandiya", "in": "Hollandiyada", "eu": True},
    "belcika": {"label": "Belçika (Pro Liqa)", "land": "Belçika", "in": "Belçikada", "eu": True},
    "sotlandiya": {"label": "Şotlandiya (Premyership)", "land": "Şotlandiya", "in": "Şotlandiyada", "eu": True},
    "rusiya": {"label": "Rusiya (Premyer Liqa)", "land": "Rusiya", "in": "Rusiyada", "eu": True},
    "braziliya": {"label": "Braziliya (A Seriyası)", "land": "Braziliya", "in": "Braziliyada", "eu": False},
    "cempionsip": {"label": "İngiltərə (Çempionşip)", "land": "Çempionşip", "in": "Çempionşipdə", "eu": True},
}
LEADER_LEAGUES = ("ingiltere", "ispaniya", "italiya", "almaniya", "fransa", "turkiye",
                  "portuqaliya", "hollandiya", "belcika", "sotlandiya", "rusiya")
CUPS = {
    "ingiltere-kuboku": "İngiltərə Kubokunun",
    "liqa-kuboku": "İngiltərə Liqa Kubokunun",
    "ispaniya-kuboku": "İspaniya Kral Kubokunun",
    "italiya-kuboku": "İtaliya Kubokunun",
    "almaniya-kuboku": "Almaniya Kubokunun",
    "turkiye-kuboku": "Türkiyə Kubokunun",
}
NIGHTS = {
    "cl": {"loc": "Çempionlar Liqasında", "gen": "Çempionlar Liqasının", "prio": 1},
    "al": {"loc": "Avropa Liqasında", "gen": "Avropa Liqasının", "prio": 2},
    "kl": {"loc": "Konfrans Liqasında", "gen": "Konfrans Liqasının", "prio": 3},
}
# Saytın izlədiyi xarici klublar: assets/app.js SPORT_TEAMS (origin/main, 2026-11-10), «Türkiyə» və «Avropa» qrupları.
# Rəqəm növbədir: gündə 3-dən çox oyun olanda əvvəl Türkiyə klubları, sonra «Real Madrid» və «Barcelona».
BIG = {
    "galatasaray": 0, "fenerbahce": 0, "besiktas": 0, "trabzonspor": 0,
    "real-madrid": 1, "barcelona": 1,
    "manchester-city": 2, "manchester-united": 2, "liverpool": 2, "arsenal": 2, "chelsea": 2, "bayern-munich": 2,
    "inter-milan": 2, "ac-milan": 2, "milan": 2, "juventus": 2, "paris-saint-germain": 2,
}
# Azərbaycan klubları avrokubok xəbərində yazılmır: onları başqa modul yazır («Sabah Avropada»).
AZ_CLUBS = {"sabah", "qarabag", "neftci", "zire", "turan-tovuz", "araz-naxcivan", "sumqayit", "kepez", "samaxi",
            "imisli", "qebele", "sefa"}
TURKISH = {"galatasaray", "fenerbahce", "besiktas", "trabzonspor", "basaksehir", "samsunspor", "goztepe", "konyaspor",
           "kasimpasa", "alanyaspor", "rizespor", "kocaelispor", "amedspor", "gaziantep", "eyupspor", "corum",
           "erzurumspor", "genclerbirligi"}
TR_BASKET = ("Fenerbahçe", "Anadolu Efes", "Beşiktaş", "Galatasaray", "Türk Telekom", "Bahçeşehir", "Karşıyaka",
             "Darüşşafaka", "Tofaş", "Pınar")
PRIO = {"liqa-tur": 1, "avrokubok": 1, "klub-oyunu": 2, "nba": 2, "liqa-diger": 3, "kubok": 3, "avroliqa": 3,
        "liqa-liderler": 4}
LABEL = {"liqa-tur": "Top liqada tur icmalı", "liqa-diger": "Digər çempionatlar, ümumi xəbər",
         "liqa-liderler": "Bazar ertəsi: liderlər", "kubok": "Xarici kubok mərhələsi", "avrokubok": "Avrokubok turu",
         "klub-oyunu": "Böyük klubun oyunu", "nba": "NBA", "avroliqa": "Avroliqa turu"}

# --- Xarici adların şəkilçisi -------------------------------------------------------------------------------
# Şəkilçi yazılışa yox, oxunuşa görə seçilir. Sağ tərəf adın oxunuşunun sonudur, Azərbaycan hərfləri ilə:
# «Hull City» -> «siti» -> «Hull City»ni; «Chelsea» -> «çelsi» -> «Chelsea»yə; «Marseille» -> «marsel» -> «Marseille»i.
# «United»: Azərbaycan mətbuatı «Mançester Yunayted» yazır (data/news.json: “Mançester Yunayted”ə), ona görə incə sait:
# «Manchester United»i, «Manchester United»ə. Xəritədə olmayan ad yazılışına görə dəyişir (_snd).
# Xəritə altı top liqanın, ÇL, AL və KL-in bütün klublarını, digər çempionatları, NBA və Avroliqanı əhatə edir.
_PRON = """
1. FC Köln|köln
AC Milan|milan
AEK Athens|atens
AGF|ef
Ajax|ayaks
Alanyaspor|spor
Alavés|alaves
Amedspor|spor
Anderlecht|anderlext
Angers|anje
Ararat-Armenia|armeniya
Arsenal|arsenal
Aston Villa|villa
Atalanta|atalanta
Athletic Bilbao|bilbao
Atlético Madrid|madrid
Auxerre|oser
AZ|ze
Barcelona|barselona
Başakşehir|şehir
Bayer Leverkusen|leverkuzen
Bayern|bayern
Bayern Munich|münix
Benfica|benfika
Beşiktaş|beşiktaş
Bodø/Glimt|qlimt
Bologna|bolonya
Borac Banja Luka|luka
Borussia Dortmund|dortmund
Borussia Mönchengladbach|qladbax
Bournemouth|bornmut
Braga|braqa
Brann|bran
Brentford|brentford
Brest|brest
Brighton & Hove Albion|albion
Cagliari|kalyari
Celje|tselye
Celta Vigo|viqo
Celtic|seltik
Chelsea|çelsi
Club Brugge|brügge
Como|komo
Copenhagen|kopenhagen
Coventry City|siti
Crystal Palace|peles
CSKA Sofia|sofiya
Çorum|çorum
Deportivo A Coruña|korunya
Dinamo Zagreb|zaqreb
Egnatia|eqnatiya
Eintracht Frankfurt|frankfurt
Elche|elçe
Erzurumspor|spor
Espanyol|espanyol
Everton|everton
Eyüpspor|spor
FC Augsburg|auqsburq
Fenerbahçe|fenerbahçe
Ferencváros|ferentsvaroş
Feyenoord|feyenord
Fiorentina|fiorentina
Frosinone|frozinone
Fulham|fulem
Galatasaray|qalatasaray
Gaziantep|qaziantep
Gençlerbirliği|birliyi
Genoa|cenova
Gent|gent
Getafe|xetafe
Göztepe|göztepe
Hajduk Split|split
Hamburger SV|ve
Hapoel Be'er Sheva|şeva
Heart of Midlothian|midlotian
Hull City|siti
Iberia 1999|doqquz
Inter Club d'Escaldes|eskaldes
Inter Milan|milan
Ipswich Town|taun
Jablonec|yablonets
Jagiellonia Białystok|bialıstok
Juventus|yuventus
Kairat|kayrat
Kasımpaşa|paşa
Kauno Žalgiris|jalgiris
Kocaelispor|spor
Konyaspor|spor
KuPS|kups
LASK|lask
Lazio|latsio
Le Havre|avr
Le Mans|man
Lecce|leççe
Lech Poznań|poznan
Leeds United|yunayted
Lens|lans
Levante|levante
Levski Sofia|sofiya
Lille|lil
Lillestrøm|lilleström
Lincoln Red Imps|imps
Liverpool|liverpul
Lorient|loryan
Lugano|luqano
Lyon|lion
Mainz 05|beş
Málaga|malaqa
Manchester City|siti
Manchester United|yunayted
Marseille|marsel
Midtjylland|midtyulland
Milan|milan
Mjällby AIF|ef
Monaco|monako
Monza|montsa
Napoli|napoli
NEC|nek
Newcastle United|yunayted
Nice|nis
Nordsjælland|nordşellan
Nottingham Forest|forest
OFI|ofi
Olympiacos|olimpiakos
Omonia|omoniya
Osasuna|osasuna
Pafos|pafos
Panathinaikos|panatinaykos
Paris FC|ce
Paris Saint-Germain|jermen
Parma|parma
Porto|porto
PSV Eindhoven|eyndhoven
Racing Santander|santander
Rayo Vallecano|valyekano
RB Leipzig|laypsiq
Real Betis|betis
Real Madrid|madrid
Real Sociedad|sosyedad
Red Bull Salzburg|zaltsburq
Red Star Belgrade|belqreyd
Rennes|ren
Riga|riqa
Rizespor|spor
Roma|roma
Sabah|sabah
Samsunspor|spor
Sassuolo|sassuolo
SC Freiburg|frayburq
SC Paderborn|paderborn
Schalke 04|dörd
Sevilla|sevilya
Shakhtar Donetsk|donetsk
Sint-Truiden|trayden
Slavia Prague|praq
Slovan Bratislava|bratislava
Sparta Prague|praq
Sporting CP|pe
Strasbourg|strasbur
Sturm Graz|qrats
Sunderland|sanderlend
SV Elversberg|elversberq
Thun|tun
Torino|torino
Torreense|torreense
Tottenham Hotspur|hotspur
Toulouse|tuluz
Trabzonspor|spor
Troyes|trua
TSG Hoffenheim|hoffenhaym
Twente|tvente
Udinese|udineze
Union Berlin|berlin
Union Saint-Gilloise|jiluaz
Universitatea Craiova|krayova
Valencia|valensiya
Venezia|venetsiya
VfB Stuttgart|ştutqart
Viking|vikinq
Viktoria Plzeň|plzen
Villarreal|vilyareal
Werder Bremen|bremen
Santa Clara|klara
Arouca|aroka
Académico de Viseu|vizeu
Gil Vicente|visente
Moreirense|moreyrense
Famalicão|famalikau
Alverca|alverka
Estrela da Amadora|amadora
Nacional|nasional
Vitória de Guimarães|qimarayş
Marítimo|maritimo
Casa Pia|piya
Rio Ave|ave
Estoril Praia|praya
Heerenveen|herenfen
Fortuna Sittard|sittard
Go Ahead Eagles|iqls
Groningen|xroninqen
Cambuur|kambur
Sparta Rotterdam|rotterdam
PEC Zwolle|zvolle
Utrecht|utrext
Excelsior|ekselsior
Telstar|telstar
ADO Den Haag|haq
Willem II|tve
Union SG|qe
Charleroi|şarlrua
Lommel|lommel
Genk|genk
Standard Liège|lyej
Westerlo|vesterlo
OH Leuven|löven
Mechelen|mexelen
Antwerp|antverp
Zulte Waregem|vareqem
Beveren|beveren
Cercle Brugge|brügge
La Louvière|luvyer
Kortrijk|kortreyk
Rangers|reyncers
Falkirk|folkirk
Dundee|dandi
Dundee United|yunayted
St Johnstone|conston
St Mirren|mirren
Motherwell|mazervel
Hibernian|hibernian
Aberdeen|aberdin
Kilmarnock|kilmarnok
Zenit Saint Petersburg|peterburq
Dynamo Moscow|moskau
Spartak Moscow|moskau
Krasnodar|krasnodar
CSKA Moscow|moskau
Rostov|rostov
Krylia Sovetov Samara|samara
Rubin Kazan|kazan
Baltika Kaliningrad|kaliningrad
Orenburg|orenburq
Dynamo Makhachkala|maxaçkala
Akhmat Grozny|qrozni
Rodina Moscow|moskau
Akron Tolyatti|tolyatti
Lokomotiv Moscow|moskau
Fakel Voronezh|voronej
Flamengo|flamenqo
Palmeiras|palmeyras
Cruzeiro|kruzeyro
Fluminense|fluminense
Athletico Paranaense|paranaense
Bahia|bahiya
Atlético Mineiro|mineyro
Red Bull Bragantino|braqantino
Santos|santos
São Paulo|paulo
Botafogo|botafoqo
Coritiba|koritiba
Vasco da Gama|qama
Mirassol|mirasol
Vitória|vitoriya
Internacional|internasional
Corinthians|korintians
Grêmio|qremio
Remo|remo
Chapecoense|şapekoense
Birmingham City|siti
Middlesbrough|midlzbro
Stoke City|siti
Wolverhampton Wanderers|uonderers
West Bromwich Albion|albion
Swansea City|siti
Southampton|sauthempton
Queens Park Rangers|reyncers
West Ham United|yunayted
Sheffield United|yunayted
Portsmouth|portsmut
Norwich City|siti
Blackburn Rovers|rovers
Cardiff City|siti
Wrexham|reksem
Millwall|milvol
Bristol City|siti
Bolton Wanderers|uonderers
Charlton Athletic|atletik
Watford|uotford
Lincoln City|siti
Burnley|bernli
Derby County|kaunti
Preston North End|end
Fleetwood Town|taun
Bradford City|siti
Peterborough United|yunayted
1. FC Magdeburg|maqdeburq
Hertha BSC|ce
Holstein Kiel|kil
Dynamo Dresden|drezden
Philadelphia 76ers|siksers
Boston Celtics|seltiks
Detroit Pistons|pistons
Atlanta Hawks|hoks
New York Knicks|niks
Toronto Raptors|reptors
Cleveland Cavaliers|kavaliyers
Miami Heat|hit
Washington Wizards|vizerds
Charlotte Hornets|hornits
Indiana Pacers|peysers
Orlando Magic|mecik
Brooklyn Nets|nets
Chicago Bulls|bulls
Milwaukee Bucks|baks
Los Angeles Lakers|leykers
Oklahoma City Thunder|sander
San Antonio Spurs|spers
Minnesota Timberwolves|timbervulfs
Golden State Warriors|uorriors
Houston Rockets|rokits
Memphis Grizzlies|qrizlis
Portland Trail Blazers|bleyzers
Denver Nuggets|naqits
Dallas Mavericks|maveriks
New Orleans Pelicans|pelikans
Phoenix Suns|sans
Los Angeles Clippers|klippers
Sacramento Kings|kinqs
Utah Jazz|cez
Panathinaikos AKTOR|aktor
Crvena zvezda Meridianbet|meridianbet
Valencia Basket|basket
Fenerbahçe Tarfin|tarfin
Dubai Basketball|basketbol
Hapoel IBI Tel Aviv|aviv
Žalgiris|jalgiris
Partizan Mozzart Bet|bet
Anadolu Efes|efes
Paris Basketball|basketbol
Virtus Bologna|bolonya
LDLC ASVEL|asvel
Maccabi Rapyd Tel Aviv|aviv
Armani Olimpia Milan|milan
Kosner Baskonia|baskoniya
"""
PRON = dict(line.split("|", 1) for line in _PRON.strip().splitlines() if "|" in line)

_FOLD = str.maketrans({"á": "a", "à": "a", "â": "a", "ã": "a", "å": "a", "ä": "e", "é": "e", "è": "e", "ê": "e", "ë": "e",
                       "í": "i", "ì": "i", "î": "i", "ï": "i", "ó": "o", "ò": "o", "ô": "o", "õ": "o", "ø": "ö",
                       "ú": "u", "ù": "u", "û": "u", "ý": "i", "ÿ": "i", "æ": "e", "œ": "ö"})
_UNITS = ("sıfır", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz")
_TENS = ("", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan")


def num_word(n):
    """Ədədin oxunuşunun son sözü: 96 -> «altı», 40 -> «qırx», 100 -> «yüz», 4 -> «dörd»."""
    n = abs(int(n))
    if n == 0:
        return "sıfır"
    if n % 10:
        return _UNITS[n % 10]
    if n % 100:
        return _TENS[n % 100 // 10]
    return "yüz" if n % 1000 else "min"


def _snd(name):
    """Adın oxunuşunun sonu: xəritədən, yoxsa yazılışdan (vurğulu hərf sadələşir, sondakı rəqəm oxunur, İngilis -y -> i)."""
    tail = PRON.get(name)
    if tail:
        return tail
    words = name.split()
    word = words[-1] if words else ""
    if word.isdigit():
        return num_word(word)
    word = ox._low(word).translate(_FOLD)
    if len(word) > 1 and word[-1] == "y" and word[-2] not in ox._VOWELS:
        word = word[:-1] + "i"
    return word


def _back(sound):
    return ox._last_vowel(sound) in "aıou"


def acc(name):
    """Təsirlik hal: «Hull City»ni, «Bayern»i, «Barcelona»nı, «Liverpool»u."""
    s = _snd(name)
    return f"«{name}»{'n' if ox._vowel_end(s) else ''}{ox._four(s, ('ı', 'i', 'u', 'ü'))}"


def gen(name):
    """Yiyəlik hal: «Hull City»nin, «Arsenal»ın, «Liverpool»un."""
    s = _snd(name)
    return f"«{name}»{'n' if ox._vowel_end(s) else ''}{ox._four(s, ('ın', 'in', 'un', 'ün'))}"


def dative(name):
    """Yönlük hal: «Arsenal»a, «Barcelona»ya, «Chelsea»yə, «Nottingham Forest»ə."""
    s = _snd(name)
    return f"«{name}»{'y' if ox._vowel_end(s) else ''}{'a' if _back(s) else 'ə'}"


def ablative(name):
    """Çıxışlıq hal: «Barcelona»dan, «Chelsea»dən."""
    return f"«{name}»{'dan' if _back(_snd(name)) else 'dən'}"


_POSS = re.compile(r"(?:stadyumu|stadı|stadi|arenası|parkı|stadionu|sahəsi|sahası)$")


def locative(name):
    """Yerlik hal: «Old Trafford»da, «Anfield»də; mənsubiyyət şəkilçili ad: «Tüpraş Stadyumu»nda."""
    n = "n" if _POSS.search(ox._low(name)) else ""
    return f"«{name}»{n}{'da' if _back(_snd(name)) else 'də'}"


def num_dat(n):
    """Ədədin yönlük halı: 27 -> «27-yə», 25 -> «25-ə», 26 -> «26-ya», 30 -> «30-a»."""
    w = num_word(n)
    return f"{n}-{'y' if ox._vowel_end(w) else ''}{'a' if _back(w) else 'ə'}"


# --- Vaxt -------------------------------------------------------------------------------------------------

def _when(s):
    """ISO vaxt -> aware datetime; ofsetsiz vaxt UTC sayılır. Yoxdursa və ya oxunmursa None."""
    if not s:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _bk(t):
    return t.astimezone(BAKU)


def _aware(now):
    return (now if now.tzinfo else now.replace(tzinfo=BAKU)).astimezone(BAKU)


def _days_loc(times):
    """Bakı vaxtı ilə günlər: «8 noyabrda», «7–8 noyabrda», «31 oktyabr – 2 noyabrda»."""
    ds = sorted({_bk(t).date() for t in times})
    a, b = ds[0], ds[-1]
    if a == b:
        return ox.day_loc(a)
    if a.month == b.month:
        return f"{a.day}–{ox.day_loc(b)}"
    return f"{ox.day_text(a)} – {ox.day_loc(b)}"


def _slot_after(ready, morning=datetime.time(8, 30)):
    """Nəticə gündüz gəlirsə həmin vaxt (15 dəqiqəyə yuvarlaqlaşır), gecə gəlirsə səhər 08:30."""
    t = _bk(ready).replace(second=0, microsecond=0)
    t += datetime.timedelta(minutes=-t.minute % 15)
    if t.time() < datetime.time(8, 0):
        return datetime.datetime.combine(t.date(), morning, BAKU)
    if t.time() > datetime.time(23, 30):
        return datetime.datetime.combine(t.date() + DAY, morning, BAKU)
    return t


def _morning(last, hm=datetime.time(8, 0)):
    """Avrokubok gecəsindən sonrakı səhər: oyunlar Bakı vaxtı ilə ~01:00-da bitir."""
    return datetime.datetime.combine(_bk(last + datetime.timedelta(hours=6)).date(), hm, BAKU)


# --- Məlumat ----------------------------------------------------------------------------------------------

def _load(root, key):
    try:
        doc = json.loads((pathlib.Path(root) / "data" / "futbol" / f"{key}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) and isinstance(doc.get("games"), list) else None


def _team_name(slug, team):
    name = team.get("name") if isinstance(team, dict) else None
    return html.unescape(str(name)).strip() if name else slug.replace("-", " ").title()


def prep(doc):
    """Fayl -> oyunlar (aware vaxtla), turlar (fayldakı sıra ilə), rəsmi cədvəl, xal düzəlişi (xal çıxılması)."""
    teams = doc.get("teams") if isinstance(doc.get("teams"), dict) else {}
    names = {s: _team_name(s, t) for s, t in teams.items()}
    games, rounds = [], {}
    for i, g in enumerate(doc.get("games") or []):
        if not isinstance(g, dict) or not g.get("home") or not g.get("away"):
            continue
        hs, as_ = g.get("hs"), g.get("as")
        x = {"i": i, "t": _when(g.get("date")), "d": str(g.get("date") or "")[:10], "home": str(g["home"]),
             "away": str(g["away"]), "rnd": str(g.get("round") or ""), "hs": hs, "as": as_,
             "ok": g.get("played") is True and isinstance(hs, int) and isinstance(as_, int),
             "pen": str(g.get("pen") or ""), "stadium": html.unescape(str(g.get("stadium") or "")).strip()}
        for s in (x["home"], x["away"]):
            if s not in names:
                names[s] = _team_name(s, None)
        games.append(x)
        rounds.setdefault(x["rnd"], []).append(x)
    groups = []
    for grp in doc.get("groups") or []:
        if isinstance(grp, dict):
            rows = [r for r in grp.get("rows") or [] if isinstance(r, dict) and r.get("team")]
            groups.append({"name": str(grp.get("name") or ""), "rows": rows})
    rows = groups[0]["rows"] if groups else []
    adj, order = {}, {}
    for n, r in enumerate(rows):
        order.setdefault(r["team"], n)
        if all(isinstance(r.get(k), int) for k in ("pts", "w", "d")):
            adj[r["team"]] = r["pts"] - 3 * r["w"] - r["d"]
    return {"doc": doc, "names": names, "games": games, "rounds": rounds, "groups": groups, "rows": rows,
            "adj": adj, "order": order, "season": str(doc.get("key") or "")}


def load(root):
    data = {}
    for key in (*TOP, *OTHER, *CUPS, *NIGHTS, "nba", "avroliqa"):
        doc = _load(root, key)
        if doc:
            data[key] = prep(doc)
    return data


def _credit(lg):
    doc = lg["doc"]
    src = str(doc.get("source") or "")
    if "OpenLigaDB" in src:
        return "OpenLigaDB (ODbL 1.0)", "https://www.openligadb.de/"
    if "TheSportsDB" in src:
        return "TheSportsDB", str(doc.get("source_url") or "https://www.thesportsdb.com/")
    if "Vikipediya" in src or "Wikipedia" in src:
        return "Vikipediya", str(doc.get("url") or "https://en.wikipedia.org/")
    return src or "8ulduz", str(doc.get("url") or doc.get("source_url") or "")


def _played(g, now):
    """Oynanıb: bayraq, hər iki hesab və oyun now anına qədər bitə bilərdi (başlamadan ən azı 105 dəqiqə keçib).
    Belə olanda sınaqda keçmiş an üçün qurulan xəbər sonradan gələn nəticəni görmür."""
    return g["ok"] and g["t"] is not None and g["t"] + MIN_GAME <= now


def _nm(lg, slug):
    return lg["names"].get(slug) or slug


def _pair(lg, g):
    return f"«{_nm(lg, g['home'])}» – «{_nm(lg, g['away'])}»"


_PEN = re.compile(r"(\d+)\s*[–—-]\s*(\d+)")


def _pen(g):
    m = _PEN.search(g.get("pen") or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _score_line(lg, g):
    line = f"{_pair(lg, g)} {g['hs']}:{g['as']}"
    pen = _pen(g)
    if pen and g["hs"] == g["as"]:
        line += f" (penaltilər seriyası {pen[0]}:{pen[1]})"
    return line


# --- Tur və cədvəl ----------------------------------------------------------------------------------------

def _core(games):
    """Turun əsas oyunları və gec oyunlar. Median vaxtdan 3 gündən çox sonraya salınan oyun gec sayılır (təxirə salınıb);
    tarixi olmayan oyun əsas sayılır, yəni turu bitməmiş saxlayır."""
    dated = sorted(g["t"] for g in games if g["t"] is not None)
    if not dated:
        return list(games), []
    edge = dated[(len(dated) - 1) // 2] + POSTPONED
    return ([g for g in games if g["t"] is None or g["t"] <= edge],
            [g for g in games if g["t"] is not None and g["t"] > edge])


def round_plan(lg, rnd):
    """Turun vaxta bağlı olmayan planı: əsas və gec oyunlar, ilk və son oyun, slot."""
    core, late = _core(lg["rounds"].get(rnd) or [])
    if not core or any(g["t"] is None for g in core):
        return None
    first, last = min(g["t"] for g in core), max(g["t"] for g in core)
    return {"core": core, "late": late, "first": first, "last": last, "slot": _slot_after(last + FOOT_READY)}


def table(lg, cutoff, now):
    """Cədvəl: cutoff anınadək başlamış və now anında oynanmış oyunlardan, rəsmi xal düzəlişi ilə (Çempionşipdə xal çıxılıb).
    Rəsmi cədvəl hesablanmışla üst-üstə düşürsə sıra rəsmi cədvəldəndir, yalnız xala görə yenidən düzülür
    (Türkiyə cədvəli bəzən səhv sıralanır). Düşmürsə: xal, qol fərqi, vurulan qol. Qaytarır: (sətirlər, rəsmi_sıra)."""
    st = {s: [0, 0, 0, 0, 0, 0] for s in lg["order"]}
    for g in lg["games"]:
        if g["t"] is None or g["t"] > cutoff or not _played(g, now):
            continue
        for me, gf, ga in ((g["home"], g["hs"], g["as"]), (g["away"], g["as"], g["hs"])):
            r = st.setdefault(me, [0, 0, 0, 0, 0, 0])
            r[0] += 1
            r[1 if gf > ga else 2 if gf == ga else 3] += 1
            r[4] += gf
            r[5] += ga
    rows = [{"team": s, "p": v[0], "w": v[1], "d": v[2], "l": v[3], "gf": v[4], "ga": v[5],
             "pts": 3 * v[1] + v[2] + lg["adj"].get(s, 0)} for s, v in st.items()]
    off = {r["team"]: r for r in lg["rows"]}
    official = bool(off) and len(off) == len(rows)
    for r in rows:
        o = off.get(r["team"])
        if not o or any(o.get(k) != r[k] for k in ("p", "w", "d", "l", "gf", "ga")):
            official = False
            break
    if official:
        rows.sort(key=lambda r: (-r["pts"], lg["order"][r["team"]]))
    else:
        rows.sort(key=lambda r: (-r["pts"], r["ga"] - r["gf"], -r["gf"], lg["order"].get(r["team"], 999), r["team"]))
    for n, r in enumerate(rows, 1):
        r["pos"] = n
    return rows, official


def _row(rows, team):
    return next((r for r in rows if r["team"] == team), None)


def _sure(rows, team, official):
    """Yer dəqiqdir: sıra rəsmi cədvəldəndir, ya da başqa komandanın eyni xalı yoxdur."""
    r = _row(rows, team)
    return bool(r) and (official or sum(1 for x in rows if x["pts"] == r["pts"]) == 1)


def _leaders(rows):
    """(liderlər, ikinci yerin xalı, ikinci yerdəki komandalar)."""
    if not rows:
        return [], None, []
    top = rows[0]["pts"]
    rest = [r for r in rows if r["pts"] < top]
    second = rest[0]["pts"] if rest else None
    return [r for r in rows if r["pts"] == top], second, [r for r in rest if r["pts"] == second]


def round_facts(lg, rnd, now):
    """Bitmiş turun faktları, ya da (None, səbəb). Tur bitib: əsas oyunların hamısı oynanıb;
    gec (təxirə salınmış) oyunlar turu saxlamır, mətndə adı çəkilir."""
    if not rnd.isdigit():
        return None, "turun nömrəsi yoxdur"
    plan = round_plan(lg, rnd)
    if not plan:
        return None, "turun oyunları və ya tarixləri yoxdur"
    pending = sorted((g for g in plan["core"] if not _played(g, now)), key=lambda g: (g["t"], g["i"]))
    if pending:
        more = f" (daha {len(pending) - 1} oyun)" if len(pending) > 1 else ""
        return None, f"tur başa çatmayıb: {_pair(lg, pending[0])} oyununun nəticəsi yoxdur{more}"
    after, official = table(lg, plan["last"], now)
    before, _ = table(lg, plan["first"] - SEC, now)
    if not after or not any(r["p"] for r in after):
        return None, "cədvəl yoxdur"
    core = sorted(plan["core"], key=lambda g: (g["t"], g["i"]))
    skipped = sorted((g for g in plan["late"] if not _played(g, now)), key=lambda g: (g["t"], g["i"]))
    return {"plan": plan, "core": core, "skipped": skipped, "after": after, "before": before, "official": official}, ""


def _game_of(core, team):
    return next((g for g in core if team in (g["home"], g["away"])), None)


def _side(g, team):
    """(rəqib, öz qolları, rəqibin qolları, yer)."""
    if g["home"] == team:
        return g["away"], g["hs"], g["as"], "doğma meydanda"
    return g["home"], g["as"], g["hs"], "səfərdə"


def _res(op, gm, go, where=""):
    """Nəticə, öz qolları əvvəl: «Hull City»ni 1:0 hesabı ilə məğlub edib / «Y» ilə 1:1 ... heç-heçə edib / «Y»yə 0:1 ... uduzub."""
    w = f"{where} " if where else ""
    if gm > go:
        return f"{w}{acc(op)} {gm}:{go} hesabı ilə məğlub edib"
    if gm < go:
        return f"{w}{dative(op)} {gm}:{go} hesabı ilə uduzub"
    if gm:
        return f"{w}«{op}» ilə {gm}:{go} hesabı ilə heç-heçə edib"
    return f"{w}«{op}» ilə qolsuz heç-heçə edib"


def _res_adj(op, gm, go):
    """Sifət kimi: «Brentford»u 2:0 hesabı ilə məğlub edən, «Nottingham Forest»ə 1:3 hesabı ilə uduzan."""
    if gm > go:
        return f"{acc(op)} {gm}:{go} hesabı ilə məğlub edən"
    if gm < go:
        return f"{dative(op)} {gm}:{go} hesabı ilə uduzan"
    if gm:
        return f"«{op}» ilə {gm}:{go} hesabı ilə heç-heçə edən"
    return f"«{op}» ilə qolsuz heç-heçə edən"


def _team_res(lg, g, team, where=True):
    op, gm, go, place = _side(g, team)
    return _res(_nm(lg, op), gm, go, place if where else "")


def _game_text(lg, g):
    """Oyun, qalib mübtəda kimi: «Como» səfərdə «Lens»i 9:1 hesabı ilə məğlub edib."""
    h, a = _nm(lg, g["home"]), _nm(lg, g["away"])
    if g["hs"] > g["as"]:
        return f"«{h}» {acc(a)} {g['hs']}:{g['as']} hesabı ilə məğlub edib"
    if g["hs"] < g["as"]:
        return f"«{a}» səfərdə {acc(h)} {g['as']}:{g['hs']} hesabı ilə məğlub edib"
    if g["hs"]:
        return f"«{h}» ilə «{a}» {g['hs']}:{g['as']} hesabı ilə heç-heçə edib"
    return f"«{h}» ilə «{a}» qolsuz heç-heçə edib"


def _unique_max(games, key):
    """Ən böyük göstəricili oyun, yalnız təkdirsə («ən böyük hesab» deyə bilmək üçün)."""
    if not games:
        return None
    best = max(key(g) for g in games)
    top = [g for g in games if key(g) == best]
    return top[0] if len(top) == 1 else None


def _total(g):
    return g["hs"] + g["as"]


def _margin(g):
    return abs(g["hs"] - g["as"])


def _and(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " və " + parts[-1]


def _hw_line(core):
    hw = sum(1 for g in core if g["hs"] > g["as"])
    aw = sum(1 for g in core if g["hs"] < g["as"])
    dr = len(core) - hw - aw
    bits = []
    if hw and aw:
        bits.append(f"ev sahibləri {hw}, qonaqlar {aw} oyunda qalib gəlib")
    elif hw:
        bits.append(f"ev sahibləri {hw} oyunda qalib gəlib, qonaqlar qələbə qazanmayıb")
    elif aw:
        bits.append(f"qonaqlar {aw} oyunda qalib gəlib, ev sahibləri qələbə qazanmayıb")
    if dr:
        bits.append(f"{dr} oyun heç-heçə bitib")
    text = ", ".join(bits)
    return text[:1].upper() + text[1:] + "."


def story(lg, f):
    """Liderlik faktları: case = kept (lider qalıb), new (yeni lider), alone (bərabərlikdən təkbaşına), co (bərabər), first (ilk tur)."""
    after, before, core = f["after"], f["before"], f["core"]
    la, second, seconds = _leaders(after)
    x = la[0]["team"]
    s = {"x": x, "pts": la[0]["pts"], "co": [r["team"] for r in la], "gx": _game_of(core, x),
         "gap": la[0]["pts"] - second if len(la) == 1 and second is not None else 0,
         "second": [r["team"] for r in seconds], "gap_b": None, "prev": None, "lead_b": []}
    started = any(r["p"] for r in before)
    lb, second_b, _ = _leaders(before) if started else ([], None, [])
    s["lead_b"] = [r["team"] for r in lb]
    if len(la) > 1:
        s["case"] = "co"
    elif not started:
        s["case"] = "first"
    elif len(lb) == 1 and lb[0]["team"] == x:
        s["case"] = "kept"
        s["gap_b"] = lb[0]["pts"] - second_b if second_b is not None else 0
    elif x in [r["team"] for r in lb]:
        s["case"] = "alone"
    else:
        s["case"] = "new"
        s["prev"] = lb[0]["team"] if len(lb) == 1 else None
    return s


def _gap_text(lg, s):
    if s["gap"] <= 0:
        return ""
    x = _nm(lg, s["x"])
    if len(s["second"]) == 1:
        return f"«{x}» ikinci yerdəki {ablative(_nm(lg, s['second'][0]))} {s['gap']} xal öndədir."
    return f"«{x}» ən yaxın izləyicilərindən {s['gap']} xal öndədir."


def _leader_lead(lg, s, f):
    """Lead-in liderlik cümləsi və adı çəkilən komandalar."""
    core, after, official = f["core"], f["after"], f["official"]
    x, pts, gx = _nm(lg, s["x"]), s["pts"], s["gx"]
    named = {s["x"]}
    if gx:
        named |= {gx["home"], gx["away"]}
    if s["case"] == "co":
        bits = []
        for t in s["co"][:3]:
            g = _game_of(core, t)
            if g:
                bits.append(f"«{_nm(lg, t)}» {_team_res(lg, g, t)}")
                named |= {g["home"], g["away"]}
        lead = (", ".join(bits) + ". ") if bits else ""
        who = "Hər iki komandanın" if len(s["co"]) == 2 else f"{len(s['co'])} komandanın"
        return lead + f"{who} {pts} xalı var və onlar cədvəlin başındadır.", named
    if s["case"] == "kept":
        if gx:
            gm, go = _side(gx, s["x"])[1:3]
            tail = f"xallarının sayını {num_dat(pts)} çatdırıb." if gm >= go else f"{pts} xalda qalıb."
            text = f"Lider «{x}» {_team_res(lg, gx, s['x'])} və {tail}"
        else:
            text = f"Lider «{x}» bu turda oynamayıb, onun {pts} xalı var."
        gap = _gap_text(lg, s)
        return text + (" " + gap if gap else ""), named
    if s["case"] in ("new", "alone"):
        what = "birinci yerə yüksəlib" if s["case"] == "new" else "təkbaşına birinci yerə çıxıb"
        text = f"«{x}» {_team_res(lg, gx, s['x'])} və {pts} xalla {what}." if gx else f"«{x}» {pts} xalla {what}."
        prev = s["prev"]
        if prev:
            named.add(prev)
            gp = _game_of(core, prev)
            pr = _row(after, prev)
            text += f" Əvvəlki lider «{_nm(lg, prev)}» " + (_team_res(lg, gp, prev) if gp else "bu turda oynamayıb")
            if gp:
                named |= {gp["home"], gp["away"]}
            if pr and _sure(after, prev, official):
                text += f" və {pr['pts']} xalla {ox.ordinal(pr['pos'])} yerə düşüb."
            elif pr:
                text += f", onun {pr['pts']} xalı var."
            else:
                text += "."
        if s["gap"] > 0:
            text += f" Fərq {s['gap']} xaldır." if s["second"] == [prev] else " " + _gap_text(lg, s)
        return text, named
    return f"Turdan sonra «{x}» {pts} xalla birinci yerdədir.", named


def _movers(lg, f, skip):
    """İlk dördlükdə yeri dəyişənlər, ən çox üç. Turdan sonrakı yer dəqiq olmalıdır; turdan əvvəlki yer xal bərabərliyində
    bir aralıqdır [lo, hi], hərəkət yalnız yeni yer bu aralıqdan kənardadırsa yazılır (6–7-ci yerdən 4-cü yerə: yüksəlib)."""
    after, before, official, core = f["after"], f["before"], f["official"], f["core"]
    if not any(r["p"] for r in before):
        return [], set()
    out, named = [], set()
    cands = [r["team"] for r in after[:4]] + [r["team"] for r in before[:4] if not any(a["team"] == r["team"] for a in after[:4])]
    for t in cands:
        r, rb = _row(after, t), _row(before, t)
        if t in skip or not r or not rb or not _sure(after, t, official):
            continue
        lo = 1 + sum(1 for x in before if x["pts"] > rb["pts"])
        hi = sum(1 for x in before if x["pts"] >= rb["pts"])
        if lo <= r["pos"] <= hi:
            continue
        g = _game_of(core, t)
        who = f"«{_nm(lg, t)}»"
        if g:
            op, gm, go, _ = _side(g, t)
            who = _res_adj(_nm(lg, op), gm, go) + " " + who
        verb = "yüksəlib" if r["pos"] < lo else "düşüb"
        out.append(f"{who} {r['pts']} xalla {ox.ordinal(r['pos'])} yerə {verb}")
        named.add(t)
        if g:
            named |= {g["home"], g["away"]}
        if len(out) == 3:
            break
    return out, named


def _top_line(lg, rows, n=4):
    return "Cədvəlin başı: " + ", ".join(f"«{_nm(lg, r['team'])}» — {r['pts']} xal" for r in rows[:n]) + "."


def _pick_title(cands, fallback):
    for t in cands:
        if t and len(t) <= TITLE_MAX:
            return t
    return fallback


def _title_heads(lg, s, core):
    """Başlığın əsas faktı, xəbər dəyərinə görə sıra ilə."""
    x = _nm(lg, s["x"])
    heads = []
    if s["case"] == "new":
        heads.append(f"«{x}» liderliyə yüksəlib")
    elif s["case"] == "alone":
        heads.append(f"«{x}» təkbaşına liderdir")
    elif s["case"] == "co":
        names = [_nm(lg, t) for t in s["co"]]
        heads.append(f"«{names[0]}» və «{names[1]}» {s['pts']} xalla cədvəlin başındadır" if len(names) == 2
                     else f"{len(names)} komanda {s['pts']} xalla cədvəlin başındadır")
    elif s["case"] == "kept" and s["gap_b"] is not None and s["gap"] != s["gap_b"]:
        if s["gap"] > s["gap_b"]:
            heads.append(f"«{x}» fərqi {s['gap']} xala çatdırıb")
        elif s["gx"]:
            gm, go = _side(s["gx"], s["x"])[1:3]
            lost = "uduzub" if gm < go else "xal itirib" if gm == go else ""
            heads.append(f"«{x}» {lost}, fərq {s['gap']} xala enib" if lost else f"«{x}» qalib gəlib, fərq {s['gap']} xala enib")
        else:
            heads.append(f"«{x}» oynamayıb, fərq {s['gap']} xala enib")
    big = _unique_max(core, _margin)
    if big and _margin(big) >= 4:
        heads.append(_game_text(lg, big))
    high = _unique_max(core, _total)
    if high and _total(high) >= 7 and high is not big:
        heads.append(_game_text(lg, high))
    if s["gx"]:
        heads.append(f"lider «{x}» " + _team_res(lg, s["gx"], s["x"], where=False))
    return heads


def _item(kind, key, title, lead, body, lg, slot, listed=True):
    credit, link = _credit(lg) if isinstance(lg, dict) else lg
    return {"kind": kind, "key": key, "title": title, "lead": lead, "body": body, "list": listed and bool(body),
            "credit": credit, "link": link, "topic": "idman", "slot": f"{slot:%H:%M}", "date": slot.date().isoformat(),
            "worth": True}


_LEADER = re.compile(r"prezident|ilham əliyev|mehriban əliyeva|vitse-prezident|birinci xanım|ali baş komandan")


def leader_free(text):
    """Rəhbərliyin adı keçmir (oz_xeber.needs_owner; updater yoxdursa sadə yoxlama)."""
    try:
        return not ox.needs_owner(text)
    except Exception:
        return not _LEADER.search(ox._low(text))


def _finish(item):
    text = "\n".join([item["title"], item["lead"], *item["body"]])
    if not leader_free(text):
        return None, "mətndə rəhbərliyin adı keçir"
    return item, ""


# --- 1. Top liqalarda tur icmalı ----------------------------------------------------------------------------

def round_item(key, lg, rnd, now):
    meta = TOP[key]
    f, why = round_facts(lg, rnd, now)
    if not f:
        return None, why
    s = story(lg, f)
    core = f["core"]
    lead1 = f"{meta['gen']} {ox.ordinal(rnd)} turu {_days_loc([g['t'] for g in core])} keçirilib."
    lead2, named = _leader_lead(lg, s, f)
    moves, moved = _movers(lg, f, named)
    named |= moved
    goals = sum(_total(g) for g in core)
    lead4 = (f"Turun {len(core)} oyununda" if not f["skipped"] else f"Turda keçirilən {len(core)} oyunda") + f" {goals} qol vurulub"
    high = _unique_max(core, _total)
    if high and _total(high) >= 5 and not ({high["home"], high["away"]} & named):
        lead4 += f", ən məhsuldar görüşdə {_game_text(lg, high)}"
    lead = " ".join(p for p in (lead1, lead2, (", ".join(moves) + ".") if moves else "", lead4 + ".") if p)
    body = [_score_line(lg, g) for g in core]
    body += [f"{_pair(lg, g)} oyunu hələ keçirilməyib." for g in f["skipped"]]
    body += [_top_line(lg, f["after"]), _hw_line(core)]
    pre, short = f"{meta['loc']} {ox.ordinal(rnd)} tur: ", f"{meta['in']} {ox.ordinal(rnd)} tur: "
    cands = []
    for h in _title_heads(lg, s, core):
        cands += [pre + h, short + h]
    title = _pick_title(cands, f"{meta['in']} {ox.ordinal(rnd)} tur başa çatıb")
    return _finish(_item("liqa-tur", f"liqa-{key}-{lg['season']}-t{rnd}", title, lead, body, lg, f["plan"]["slot"]))


# --- 2. Digər çempionatlar: gündə bir ümumi xəbər -------------------------------------------------------------

def other_line(key, lg, rnd, now):
    """Bir çempionatın turu üçün 1–2 cümlə, ya da (None, səbəb)."""
    meta = OTHER[key]
    f, why = round_facts(lg, rnd, now)
    if not f:
        return None, why
    s = story(lg, f)
    core, after, official = f["core"], f["after"], f["official"]
    x, pts, gx = _nm(lg, s["x"]), s["pts"], s["gx"]
    res = f" {_team_res(lg, gx, s['x'])}" if gx else ""
    gap = ""
    if s["gap"] > 0 and len(s["second"]) == 1:
        gap = f", ikinci yerdəki {ablative(_nm(lg, s['second'][0]))} {s['gap']} xal öndədir"
    head = None
    if s["case"] == "co" and len(s["co"]) == 2:
        bits = []
        for t in s["co"]:
            g = _game_of(core, t)
            bits.append(f"«{_nm(lg, t)}» {_team_res(lg, g, t)}" if g else f"«{_nm(lg, t)}» bu turda oynamayıb")
        text = f"{bits[0]}, {bits[1]}; hər iki komandanın {pts} xalı var və onlar cədvəlin başındadır"
        if len(s["lead_b"]) == 1 and s["lead_b"][0] in s["co"]:     # əvvəlki lider təkbaşına idi, indi ona çatıblar
            old = s["lead_b"][0]
            new = next(t for t in s["co"] if t != old)
            head = (0, f"«{_nm(lg, new)}» {meta['in']} «{_nm(lg, old)}» ilə xalları bərabərləşdirib")
    elif s["case"] == "co":
        text = f"{len(s['co'])} komanda {pts} xalla cədvəlin başındadır"
    elif s["case"] == "new":
        text = f"«{x}»{res} və {pts} xalla liderliyə yüksəlib"
        prev = s["prev"]
        pr = _row(after, prev) if prev else None
        if pr and _sure(after, prev, official):
            text += f", əvvəlki lider «{_nm(lg, prev)}» {pr['pts']} xalla {ox.ordinal(pr['pos'])} yerdədir"
        head = (0, f"«{x}» {meta['in']} liderliyə yüksəlib")
    elif s["case"] == "kept":
        text = (f"lider «{x}»{res} və {pts} xalla birinci yerdədir" if gx else f"lider «{x}» oynamayıb, onun {pts} xalı var") + gap
        if s["gap_b"] is not None and s["gap"] > s["gap_b"]:
            head = (1, f"«{x}» {meta['in']} fərqi {s['gap']} xala çatdırıb")
    else:
        text = f"«{x}»{res} və {pts} xalla birinci yerdədir" + gap
    goals = sum(_total(g) for g in core)
    line = f"{meta['label']}, {ox.ordinal(rnd)} tur: {text}. {len(core)} oyunda {goals} qol vurulub."
    for g in f["skipped"]:
        line += f" {_pair(lg, g)} oyunu hələ keçirilməyib."
    weekend = all(_bk(g["t"]).weekday() in (4, 5, 6, 0) for g in core)
    return {"key": key, "rnd": rnd, "line": line, "text": text, "lead": f"{meta['in']} {text}.", "head": head,
            "eu": meta["eu"], "weekend": weekend, "lg": lg}, ""


def other_item(data, day, rounds, now):
    """rounds: [(açar, tur)], həmin günün pəncərəsinə (dünən 10:30 – bu gün 10:30) düşən turlar."""
    lines, skipped = [], []
    for key, rnd in rounds:
        res, why = other_line(key, data[key], rnd, now)
        if res:
            lines.append(res)
        else:
            skipped.append(f"{OTHER[key]['land']}, {ox.ordinal(rnd)} tur: {why}")
    if not lines:
        return None, "; ".join(skipped) or "başa çatmış tur yoxdur"
    eu, weekend = all(r["eu"] for r in lines), all(r["weekend"] for r in lines)
    scope = ("Avropa çempionatlarında" if eu else "Xarici çempionatlarda") + (" həftə sonu" if weekend else " tur yekunları")
    heads = sorted((r["head"] for r in lines if r["head"]), key=lambda h: h[0])
    cands = [f"{scope}: {h[1]}" for h in heads]
    fallback = f"{scope}: {len(lines)} çempionatda turlar başa çatıb"
    title = _pick_title(cands + [fallback], fallback)
    first = next((r for r in lines if r["head"] and r["head"] == heads[0]), lines[0]) if heads else lines[0]
    if len(lines) > 1:
        names = _and(f"{OTHER[r['key']]['land']} ({ox.ordinal(r['rnd'])} tur)" for r in lines)
        lead = f"{len(lines)} çempionatda turlar başa çatıb: {names}. {first['lead']}"
    else:
        lead = f"{OTHER[first['key']]['in']} {ox.ordinal(first['rnd'])} tur başa çatıb: {first['text']}."
    credits = sorted({_credit(r["lg"])[0] for r in lines})
    link = _credit(lines[0]["lg"])[1]
    item = _item("liqa-diger", f"liqa-diger-{day.isoformat()}", title, lead, [r["line"] for r in lines],
                 (", ".join(credits), link), datetime.datetime.combine(day, datetime.time(10, 30), BAKU))
    item["skipped"] = skipped
    return _finish(item)


def _other_window(ready):
    """Ümumi xəbərin günü: dünən 10:30-dan bu gün 10:30-dək bitən turlar bu günün xəbərinə düşür."""
    t = _bk(ready)
    return t.date() if t.time() <= datetime.time(10, 30) else t.date() + DAY


# --- 3. Bazar ertəsi: liderlər --------------------------------------------------------------------------------

def _streak(lg, team, now):
    """Komandanın son ardıcıl qələbələrinin sayı (now anınadək oynanmış oyunlar)."""
    gs = sorted((g for g in lg["games"] if _played(g, now) and team in (g["home"], g["away"])), key=lambda g: (g["t"], g["i"]))
    k = 0
    for g in reversed(gs):
        gm, go = _side(g, team)[1:3]
        if gm <= go:
            break
        k += 1
    return k


def _active(lg, since, upto):
    return any(g["t"] is not None and since <= g["t"] < upto for g in lg["games"])


def leaders_item(data, monday, now):
    since = datetime.datetime.combine(monday - 7 * DAY, datetime.time(0, 0), BAKU)
    upto = datetime.datetime.combine(monday, datetime.time(0, 0), BAKU)
    leagues = [(k, data[k]) for k in LEADER_LEAGUES if k in data]
    active = [(k, lg) for k, lg in leagues if any(g["t"] and since <= g["t"] < upto and _played(g, now) for g in lg["games"])]
    if len(active) < LEADERS_MIN:
        return None, f"son həftə yalnız {len(active)} çempionatda oyun olub (beynəlxalq fasilə)"
    meta = {**TOP, **OTHER}
    tops, body, unbeaten, perfect, streaks = [], [], [], [], []
    for key, lg in leagues:
        rows, official = table(lg, now, now)
        if not rows or not any(r["p"] for r in rows):
            continue
        la, second, seconds = _leaders(rows)
        names = [_nm(lg, r["team"]) for r in la]
        land, where = meta[key]["land"], meta[key]["in"]
        if len(la) == 1:
            line = f"{land}: «{names[0]}» — {la[0]['pts']} xal"
            if second is not None and len(seconds) == 1:
                line += f", ikinci yerdəki {ablative(_nm(lg, seconds[0]['team']))} {la[0]['pts'] - second} xal öndədir"
            elif second is not None:
                line += f", ən yaxın izləyicilərindən {la[0]['pts'] - second} xal öndədir"
            who = f"«{names[0]}»"
        else:
            who = _and("«" + n + "»" for n in names[:3])
            line = f"{land}: {who} — {la[0]['pts']} xal"
        body.append(line + ".")
        if key in TOP:
            tops.append((where, who, la[0]["pts"]))
        for r in rows:
            if r["l"] == 0 and r["p"] >= 5:
                unbeaten.append((key, r))
                if r["d"] == 0:
                    perfect.append((key, r))
            k = _streak(lg, r["team"], now)
            if k >= 4:
                streaks.append((k, key, r["team"]))
    if not tops:
        return None, "top liqaların cədvəli yoxdur"
    head = "Avropa çempionatlarında liderlər"
    cands = []
    perfect.sort(key=lambda kr: (-kr[1]["p"], LEADER_LEAGUES.index(kr[0])))
    streaks.sort(key=lambda s: (-s[0], LEADER_LEAGUES.index(s[1]), s[2]))
    perfect_text = ""
    if perfect:
        k, r = perfect[0]
        perfect_text = f"«{_nm(data[k], r['team'])}» {r['p']} oyunda {r['p']} qələbə qazanıb"
        cands.append(f"{head}: {perfect_text}")
    if streaks and (len(streaks) == 1 or streaks[0][0] > streaks[1][0]) and streaks[0][0] >= 5:
        k, key, t = streaks[0]
        cands.append(f"{head}: «{_nm(data[key], t)}» ardıcıl {k} oyunda qalib gəlib")
    if unbeaten:
        cands.append(f"{head}: {len(unbeaten)} komanda hələ məğlub olmayıb")
    title = _pick_title(cands, f"{head} və məğlubiyyətsiz komandalar" if unbeaten else head)
    parts = []
    for n, (w, who, p) in enumerate(tops):
        if n == 0:
            parts.append(f"{w} {who} ({p} xal)")
        else:
            parts.append(f"{w}{' isə' if n == len(tops) - 1 else ''} {who} ({p})")
    lead = "Cədvəllərin hazırkı vəziyyətinə görə " + ", ".join(parts) + " cədvəlin başındadır."
    if unbeaten:
        names = ["«" + _nm(data[k], r["team"]) + "»" for k, r in unbeaten[:8]]
        more = f" və daha {len(unbeaten) - 8} komanda" if len(unbeaten) > 8 else ""
        lead += f" {_and(names)}{more} hələ məğlub olmayıb."
    if perfect_text and perfect_text not in title:
        k, r = perfect[0]
        lead += f" «{_nm(data[k], r['team'])}» {r['p']} oyunun hamısında qalib gəlib."
    if streaks:
        body.append("Çempionatda ardıcıl qələbə seriyaları: " + ", ".join(f"«{_nm(data[key], t)}» — {k} oyun" for k, key, t in streaks[:5]) + ".")
    credits = sorted({_credit(lg)[0] for _, lg in leagues})
    link = next((_credit(lg)[1] for _, lg in leagues if _credit(lg)[0] == "TheSportsDB"), _credit(leagues[0][1])[1])
    slot = datetime.datetime.combine(monday, datetime.time(9, 0), BAKU)
    return _finish(_item("liqa-liderler", f"liqa-liderler-{monday.isoformat()}", title, lead, body,
                         (", ".join(credits), link), slot))


# --- 4. Xarici kuboklar -------------------------------------------------------------------------------------

def _stage_gen(stage):
    """«4-cü mərhələ» -> «4-cü mərhələsinin», «1/8 final» -> «1/8 finalının», «Təsnifat» -> «təsnifat mərhələsinin»."""
    low = ox._low(stage)
    if low.endswith("mərhələ"):
        return stage + "sinin"
    if low.endswith("final"):
        return stage + "ının"
    return stage[:1].lower() + stage[1:] + " mərhələsinin"


def _stage_poss(stage):
    low = ox._low(stage)
    if low.endswith("mərhələ"):
        return stage + "si"
    if low.endswith("final"):
        return stage + "ı"
    return stage[:1].lower() + stage[1:] + " mərhələsi"


def _stage_dat(stage):
    low = ox._low(stage)
    if low.endswith("mərhələ"):
        return stage + "yə"
    if low.endswith("final"):
        return stage + "a"
    return stage[:1].lower() + stage[1:] + " mərhələsinə"


def _stage_of_gen(stage):
    """«1/4 final» -> «1/4 finalın», «4-cü mərhələ» -> «4-cü mərhələnin»."""
    low = ox._low(stage)
    if low.endswith("mərhələ"):
        return stage + "nin"
    if low.endswith("final"):
        return stage + "ın"
    return stage[:1].lower() + stage[1:] + " mərhələsinin"


def _slug(s):
    s = ox._low(s).translate(str.maketrans("əıöüçşğ", "eioucsg"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _dated(games):
    """Oyunlar vaxt sırası ilə, ya da hansınınsa tarixi yoxdursa None."""
    if not games or any(g["t"] is None for g in games):
        return None
    return sorted(games, key=lambda g: (g["t"], g["i"]))


def cup_item(key, lg, stage, now):
    games = _dated(lg["rounds"].get(stage) or [])
    if not games:
        return None, "mərhələnin oyunları və ya tarixləri yoxdur"
    left = [g for g in games if not _played(g, now)]
    if left:
        return None, f"mərhələ başa çatmayıb: {len(left)} oyun qalıb"
    bigs = [g for g in games if g["home"] in BIG or g["away"] in BIG]
    if not bigs:
        return None, "böyük klub oynamayıb"
    stages = list(lg["rounds"])
    nxt = stages[stages.index(stage) + 1] if stages.index(stage) + 1 < len(stages) else None
    nteams = set()
    for g in lg["rounds"].get(nxt) or []:
        nteams |= {g["home"], g["away"]}
    full = bool(nxt) and len(nteams) == len(games)    # növbəti mərhələnin cütləri bəllidir: hər qalib üçün bir yer
    sents, heads = [], []
    bigs.sort(key=lambda g: (min(BIG.get(g["home"], 9), BIG.get(g["away"], 9)), g["t"], g["i"]))
    for g in bigs:
        pen = _pen(g) if g["hs"] == g["as"] else None
        home_won = g["hs"] > g["as"] or bool(pen and pen[0] > pen[1])
        if g["home"] in BIG and g["away"] in BIG:
            b = g["home"] if home_won or (g["hs"] == g["as"] and not pen) else g["away"]
        else:
            b = g["home"] if g["home"] in BIG else g["away"]
        op, gm, go, _ = _side(g, b)
        pm = (pen if b == g["home"] else (pen[1], pen[0])) if pen else None
        won, lost = gm > go or bool(pm and pm[0] > pm[1]), gm < go or bool(pm and pm[0] < pm[1])
        B, O = _nm(lg, b), _nm(lg, op)
        text = f"«{B}» {_team_res(lg, g, b)}"
        if pm:
            text += f", penaltilər seriyasında isə {pm[0]}:{pm[1]} hesabı ilə {'qalib gəlib' if won else 'uduzub'}"
        if full and b in nteams:
            text += f" və {_stage_dat(nxt)} yüksəlib"
        elif full and lost:
            text += " və mübarizədən kənarlaşıb"
        sents.append(text + ".")
        if lost:
            heads.append((0, f"«{B}» {'penaltilər seriyasında ' if pm else ''}{dative(O)} uduzub"))
        elif won and pm:
            heads.append((2, f"«{B}» penaltilər seriyasında {acc(O)} üstələyib"))
        elif won:
            heads.append((1 if gm - go >= 3 else 2, f"«{B}» {acc(O)} {gm}:{go} hesabı ilə məğlub edib"))
        else:
            heads.append((3, f"«{B}» «{O}» ilə {gm}:{go} hesabı ilə heç-heçə edib"))
    heads.sort(key=lambda h: h[0])
    prefix = f"{CUPS[key]} {_stage_poss(stage)}: "
    title = _pick_title([prefix + h[1] for h in heads], prefix.rstrip(": ") + " başa çatıb")
    lead = f"{CUPS[key]} {_stage_gen(stage)} oyunları {_days_loc([g['t'] for g in games])} keçirilib. " + " ".join(sents)
    body = [_score_line(lg, g) for g in games]
    if full:
        body.append(f"{_stage_of_gen(nxt)} cütləri: " + ", ".join(_pair(lg, g) for g in lg["rounds"][nxt]) + ".")
    slot = _slot_after(max(g["t"] for g in games) + CUP_READY)
    return _finish(_item("kubok", f"kubok-{key}-{lg['season']}-{_slug(stage)}", title, lead, body, lg, slot))


# --- 5. Avrokubok turu (ÇL, AL, KL) -------------------------------------------------------------------------

def night_item(key, lg, md, now):
    meta = NIGHTS[key]
    games = _dated(lg["rounds"].get(md) or [])
    if not games:
        return None, "turun oyunları və ya tarixləri yoxdur"
    left = [g for g in games if not _played(g, now)]
    if left:
        return None, f"tur başa çatmayıb: {len(left)} oyunun nəticəsi yoxdur"
    last = max(g["t"] for g in games)
    rows, official = table(lg, last, now)
    shown = [g for g in games if g["home"] not in AZ_CLUBS and g["away"] not in AZ_CLUBS]
    shown_ids = {g["i"] for g in shown}
    goals = sum(_total(g) for g in games)
    stage = f"liqa mərhələsinin {ox.ordinal(md)} turu" if md.isdigit() else f"«{md}» mərhələsi"
    tour = f"{ox.ordinal(md)} tur" if md.isdigit() else md
    sents = [f"{meta['gen']} {stage} başa çatıb."]
    la, _, _ = _leaders(rows) if rows and any(r["p"] for r in rows) else ([], None, [])
    lnames = _and("«" + _nm(lg, r["team"]) + "»" for r in la[:4]) if la else ""
    if len(la) == 1:
        sents.append(f"{lnames} {la[0]['p']} oyunda {la[0]['pts']} xal toplayıb və cədvəlin başındadır.")
    elif 2 <= len(la) <= 4:
        perfect = all(r["p"] == la[0]["p"] and r["w"] == r["p"] for r in la)
        every = {2: "hər iki", 3: "hər üç", 4: "hər dörd"}[len(la)]
        sents.append(f"{lnames} {la[0]['pts']} xalla cədvəlin başındadır"
                     + (f": {every} komanda {la[0]['p']} oyunun hamısında qalib gəlib." if perfect else "."))
    elif la:
        sents.append(f"{len(la)} komanda {la[0]['pts']} xalla cədvəlin başındadır.")
    named = {r["team"] for r in la}
    heads = []
    turkish = [g for g in shown if g["home"] in TURKISH or g["away"] in TURKISH]
    for n, g in enumerate(turkish):
        t = g["home"] if g["home"] in TURKISH else g["away"]
        r = _row(rows, t)
        text = f"«{_nm(lg, t)}» {_team_res(lg, g, t)}"
        if r and _sure(rows, t, official):
            text += f" və {r['pts']} xalla {ox.ordinal(r['pos'])} yerdədir"
        sents.append(("Türkiyə klublarından " if n == 0 else "") + text + ".")
        named |= {g["home"], g["away"]}
        op, gm, go, _ = _side(g, t)
        ro = _row(rows, op)
        if gm > go:
            heads.append((0, -(ro["pts"] if ro else 0), f"«{_nm(lg, t)}» {acc(_nm(lg, op))} {gm}:{go} hesabı ilə məğlub edib"))
        else:                            # Türkiyə klubunun heç-heçəsi və ya məğlubiyyəti də oxucu üçün əsas faktdır
            heads.append((3, -(ro["pts"] if ro else 0), f"«{_nm(lg, t)}» " + _team_res(lg, g, t, where=False)))
    big = _unique_max(games, _margin)
    if big and _margin(big) >= 3 and big["i"] in shown_ids:
        w = big["home"] if big["hs"] > big["as"] else big["away"]
        op, gm, go, place = _side(big, w)
        if not ({big["home"], big["away"]} & named):
            sents.append(f"Turun ən böyük hesablı qələbəsini «{_nm(lg, w)}» qazanıb: komanda {place} {acc(_nm(lg, op))} "
                         f"{gm}:{go} hesabı ilə məğlub edib.")
            named |= {big["home"], big["away"]}
        if _margin(big) >= 4:
            heads.append((1, 0, f"{_game_text(lg, big)}, {len(games)} oyunda {goals} qol vurulub"))
            heads.append((2, 0, _game_text(lg, big)))
    high = _unique_max(games, _total)
    if high and high["i"] in shown_ids and _total(high) >= 6 and not ({high["home"], high["away"]} & named):
        sents.append(f"Ən məhsuldar oyunda {_game_text(lg, high)}.")
    sents.append(f"Turun {len(games)} oyununda {goals} qol vurulub.")
    if 1 <= len(la) <= 4:
        heads.append((4, 0, f"{lnames} {la[0]['pts']} xalla liderdir"))
    heads.sort(key=lambda h: (h[0], h[1]))
    pre = f"{meta['loc']} {tour}: "
    title = _pick_title([pre + h[2] for h in heads] + [pre + f"{len(games)} oyunda {goals} qol vurulub"],
                        f"{meta['loc']} {tour} başa çatıb")
    body = [_score_line(lg, g) for g in shown]
    if rows and any(r["p"] for r in rows):
        body.append("Cədvəlin ilk səkkizliyi: " + ", ".join(f"«{_nm(lg, r['team'])}» — {r['pts']}" for r in rows[:8]) + " xal.")
    item = _item("avrokubok", f"avrokubok-{key}-{lg['season']}-t{_slug(md)}", title, " ".join(sents), body, lg, _morning(last))
    return _finish(item)


# --- 6. Böyük klubun oyunu ----------------------------------------------------------------------------------

def club_item(comp, lg, g, now):
    if not _played(g, now):
        return None, "oyun hələ bitməyib"
    bigs = [s for s in (g["home"], g["away"]) if s in BIG]
    if not bigs:
        return None, "böyük klub oynamayıb"
    if len(bigs) == 2:
        b = g["away"] if g["as"] > g["hs"] else g["home"]
    else:
        b = bigs[0]
    op, gm, go, place = _side(g, b)
    B, O = _nm(lg, b), _nm(lg, op)
    rnd = g["rnd"]
    if comp in TOP:
        c_loc, stage = TOP[comp]["loc"], f"{TOP[comp]['gen']} {ox.ordinal(rnd)} turunda" if rnd.isdigit() else TOP[comp]["loc"]
        scope = ("çempionatdakı", "çempionatda")
    else:
        c_loc = NIGHTS[comp]["loc"]
        stage = (f"{NIGHTS[comp]['gen']} liqa mərhələsinin {ox.ordinal(rnd)} turunda" if rnd.isdigit()
                 else f"{NIGHTS[comp]['gen']} «{rnd}» mərhələsində")
        scope = ("turnirdəki", "turnirdə")
    when = _bk(g["t"])
    day = ox.day_loc(when)
    if when.hour < 6:
        day += f" Bakı vaxtı ilə {ox.time_loc(when)} başlayan oyunda"
    title = f"«{B}» {c_loc} {_res(O, gm, go)}"
    lead = f"{stage} «{B}» {day} {_res(O, gm, go, place)}."
    prev = sorted((x for x in lg["games"] if x["t"] is not None and x["t"] < g["t"] and _played(x, now)
                   and b in (x["home"], x["away"])), key=lambda x: (x["t"], x["i"]))
    if gm > go:
        wins = [_side(x, b)[1] > _side(x, b)[2] for x in prev]
        if prev and not any(wins):
            lead += f" Bu, {gen(B)} {scope[0]} ilk qələbəsidir."
        else:
            k = 1
            for w in reversed(wins):
                if not w:
                    break
                k += 1
            if k >= 3:
                lead += f" Bu, {gen(B)} {scope[1]} ardıcıl {ox.ordinal(k)} qələbəsidir."
    rows, official = table(lg, now, now)
    rb, ro = _row(rows, b), _row(rows, op)
    among = f"{len(rows)} komanda arasında " if comp in NIGHTS else ""
    if rb and rb["p"]:
        if _sure(rows, b, official):     # yer dəqiqdirsə yer də, rəqibin yeri də; xal bərabərdirsə yalnız xal
            lead += f" «{B}» {rb['p']} oyunda {rb['pts']} xal toplayıb və {among}{ox.ordinal(rb['pos'])} yerdədir."
            if ro and ro["p"] and _sure(rows, op, official):
                lead += f" «{O}» {ro['pts']} xalla {ox.ordinal(ro['pos'])} yerdədir."
        else:
            lead += f" «{B}» {rb['p']} oyunda {rb['pts']} xal toplayıb."
    body = [f"Görüş {locative(g['stadium'])} keçirilib."] if g["stadium"] else []
    slot = _slot_after(g["t"] + FOOT_READY)
    item = _item("klub-oyunu", f"klub-{comp}-{lg['season']}-{g['home']}-{g['away']}", title, lead, body, lg, slot, listed=False)
    return _finish(item)


# --- 7. NBA -------------------------------------------------------------------------------------------------

def _conf(lg):
    """{komanda: konfrans adı} (Şərq/Qərb)."""
    out = {}
    for grp in lg["groups"]:
        for r in grp["rows"]:
            out[r["team"]] = grp["name"]
    return out


def _conf_gen(name):
    low = ox._low(name)
    return "Şərq konfransının" if "şərq" in low else "Qərb konfransının" if "qərb" in low else f"{name}nın"


def nba_item(lg, us_day, now):
    """ABŞ tarixi us_day (Vikipediyada oyun günü 12:00 UTC kimi yazılır) üçün xəbər. Nəticələr gün ərzində dəyişə bilir:
    yalnız həmin günün hamısı oynanıbsa və hesablar ağlabatandırsa (bərabər hesab, 50-dən az və ya 200-dən çox xal yoxdur)."""
    day = us_day.isoformat()
    games = sorted((g for g in lg["games"] if g["d"] == day), key=lambda g: g["i"])
    if not games:
        return None, "həmin gün oyun yoxdur"
    left = [g for g in games if not _played(g, now)]
    if left:
        return None, f"ABŞ vaxtı ilə {ox.day_text(us_day)} oyunlarının hamısı bitməyib ({len(games) - len(left)}/{len(games)})"
    odd = [g for g in games if g["hs"] == g["as"] or not (50 <= g["hs"] <= 200 and 50 <= g["as"] <= 200)]
    if odd:
        return None, f"şübhəli hesab: {_pair(lg, odd[0])} {odd[0]['hs']}:{odd[0]['as']}"
    upto = [g for g in lg["games"] if g["d"] and g["d"] <= day and _played(g, now)]
    rec, seq = {}, {}
    for g in sorted(upto, key=lambda g: (g["d"], g["i"])):
        for t, won in ((g["home"], g["hs"] > g["as"]), (g["away"], g["as"] > g["hs"])):
            w, l = rec.get(t, (0, 0))
            rec[t] = (w + 1, l) if won else (w, l + 1)
            seq.setdefault(t, []).append(won)

    def streak(t):
        k = 0
        for won in reversed(seq.get(t, [])):
            if not won:
                break
            k += 1
        return k

    conf = _conf(lg)
    leaders = {}
    for c in sorted(set(conf.values())):
        teams = [t for t in conf if conf[t] == c and t in rec]
        if not teams:
            continue
        pct = {t: rec[t][0] / (rec[t][0] + rec[t][1]) for t in teams}
        best = max(pct.values())
        top = [t for t in teams if pct[t] == best]
        if len(top) == 1:
            leaders[top[0]] = c
    winners = [(g["home"] if g["hs"] > g["as"] else g["away"], g) for g in games]
    st = sorted(((streak(t), n, t, g) for n, (t, g) in enumerate(winners)), key=lambda x: (-x[0], x[1]))
    lead = f"NBA-da ABŞ vaxtı ilə {ox.day_loc(us_day)} {len(games)} oyun keçirilib."
    heads, named = [], set()
    if st and st[0][0] >= 5 and (len(st) == 1 or st[0][0] > st[1][0]):
        heads.append(f"«{_nm(lg, st[0][2])}» ardıcıl {ox.ordinal(st[0][0])} qələbəsini qazanıb")
    for t, g in winners:
        if t in leaders:
            w, l = rec[t]
            lead += (f" «{_nm(lg, t)}» {_team_res(lg, g, t)} və {w} qələbə, {l} məğlubiyyətlə "
                     f"{_conf_gen(leaders[t])} lideridir.")
            named.add(t)
    if st and st[0][0] >= 5 and (len(st) == 1 or st[0][0] > st[1][0]):
        lead += f" Bu, {gen(_nm(lg, st[0][2]))} ardıcıl {ox.ordinal(st[0][0])} qələbəsidir."
    big = _unique_max(games, _margin)
    if big:
        w = big["home"] if big["hs"] > big["as"] else big["away"]
        op, gm, go, place = _side(big, w)
        lead += f" Günün ən böyük fərqli qələbəsini «{_nm(lg, w)}» qazanıb: komanda {place} {acc(_nm(lg, op))} {gm}:{go} hesabı ilə üstələyib."
        if _margin(big) >= 20:
            heads.append(f"«{_nm(lg, w)}» {acc(_nm(lg, op))} {gm}:{go} hesabı ilə məğlub edib")
    for t, g in winners:
        if t in leaders:
            heads.append(f"lider «{_nm(lg, t)}» " + _team_res(lg, g, t, where=False))
    body = [_score_line(lg, g) for g in games]
    lines = []
    for c in sorted(set(conf.values())):
        teams = sorted((t for t in conf if conf[t] == c and t in rec), key=lambda t: (-rec[t][0] / sum(rec[t]), -rec[t][0], t))
        if teams:
            t = teams[0]
            lines.append(f"{_conf_gen(c).replace('konfransının', 'konfransında')} «{_nm(lg, t)}» — {rec[t][0]} qələbə, {rec[t][1]} məğlubiyyət")
    if lines:
        body.append("Konfransların başında: " + "; ".join(lines) + ".")
    title = _pick_title([f"NBA-da {h}" for h in heads], f"NBA-da ABŞ vaxtı ilə {ox.day_text(us_day)}: {len(games)} oyunun nəticələri")
    slot = datetime.datetime.combine(us_day + DAY, datetime.time(9, 0), BAKU)
    return _finish(_item("nba", f"nba-{day}", title, lead, body, lg, slot))


# --- 8. Avroliqa (basketbol) --------------------------------------------------------------------------------

def _tr_basket(name):
    return any(k in name for k in TR_BASKET)


def euro_item(lg, rnd, now):
    """Avroliqa turu. Faylda turun bütün oyunları olmur (bəzi komandaların oyunu yoxdur), ona görə oyun sayı yazılmır;
    yer və qələbə-məğlubiyyət rəsmi cədvəldəndir."""
    if not rnd.isdigit():
        return None, "turun nömrəsi yoxdur"
    games = _dated(lg["rounds"].get(rnd) or [])
    if not games:
        return None, "turun oyunları və ya tarixləri yoxdur"
    left = [g for g in games if not _played(g, now)]
    if left:
        return None, f"tur başa çatmayıb: {_pair(lg, left[0])} oyununun nəticəsi yoxdur"
    rows = [r for r in lg["rows"] if isinstance(r.get("w"), int) and isinstance(r.get("l"), int)]
    if not rows:
        return None, "cədvəl yoxdur"
    if min(r["w"] + r["l"] for r in rows) < int(rnd):
        return None, "cədvəl bu turu hələ saymayıb (məlumat təzə deyil)"
    last = max(g["t"] for g in games)
    asof = str(lg["doc"].get("asof") or "")
    if asof and asof < last.astimezone(UTC).date().isoformat():
        return None, "məlumat təzə deyil"
    rows = sorted(rows, key=lambda r: (r.get("pos") or 99, -r["w"]))
    lead_r = rows[0]
    co = [r for r in rows if r["w"] == lead_r["w"] and r["l"] == lead_r["l"]]
    L = _nm(lg, lead_r["team"])
    gl = _game_of(games, lead_r["team"])
    sents = []
    if len(co) == 1:
        res = f" {_team_res(lg, gl, lead_r['team'])} və" if gl else ""
        sents.append(f"Basketbol üzrə Avroliqanın {ox.ordinal(rnd)} turunda lider «{L}»{res} {lead_r['w']} qələbə, "
                     f"{lead_r['l']} məğlubiyyətlə birinci yerdədir.")
    else:
        who = _and("«" + _nm(lg, r["team"]) + "»" for r in co[:3])
        sents.append(f"Basketbol üzrə Avroliqanın {ox.ordinal(rnd)} turundan sonra {who} "
                     f"{lead_r['w']} qələbə, {lead_r['l']} məğlubiyyətlə cədvəlin başındadır.")
    heads = []
    tr = [g for g in games if _tr_basket(_nm(lg, g["home"])) or _tr_basket(_nm(lg, g["away"]))]
    bits = []
    for g in tr:
        t = g["home"] if _tr_basket(_nm(lg, g["home"])) else g["away"]
        if t == lead_r["team"]:
            continue
        bits.append(f"«{_nm(lg, t)}» {_team_res(lg, g, t)}")
        op, gm, go, _ = _side(g, t)
        if gm > go:
            pos = next((r.get("pos") or 99 for r in rows if r["team"] == op), 99)
            heads.append((0, pos, f"«{_nm(lg, t)}» {acc(_nm(lg, op))} {gm}:{go} hesabı ilə məğlub edib"))
    if bits:
        sents.append("Türkiyə klublarından " + ", ".join(bits) + ".")
    if gl and len(co) == 1:
        heads.append((1, 0, f"lider «{L}» " + _team_res(lg, gl, lead_r["team"], where=False)))
    heads.append((2, 0, f"«{L}» {lead_r['w']} qələbə ilə liderdir" if len(co) == 1 else "cədvəlin başında bərabərlik"))
    heads.sort(key=lambda h: (h[0], h[1]))
    pre = f"Avroliqada {ox.ordinal(rnd)} tur: "
    title = _pick_title([pre + h[2] for h in heads], f"Avroliqada {ox.ordinal(rnd)} tur başa çatıb")
    body = [_score_line(lg, g) for g in games]
    body.append("Cədvəlin başı: " + "; ".join(f"«{_nm(lg, r['team'])}» — {r['w']} qələbə, {r['l']} məğlubiyyət" for r in rows[:4]) + ".")
    slot = _slot_after(last + BASKET_READY)
    return _finish(_item("avroliqa", f"avroliqa-{lg['season']}-t{rnd}", title, " ".join(sents), body, lg, slot))


# --- Plan: hansı gün nə çıxır -------------------------------------------------------------------------------

def _ev(kind, key, slot, make, prio=None, **extra):
    e = {"kind": kind, "key": key, "slot": slot, "prio": PRIO[kind] if prio is None else prio, "make": make}
    e.update(extra)
    return e


def events(data):
    """Məlumatdakı bütün hadisələr (hər gün üçün), vaxtdan asılı olmadan. make(now) -> (xəbər, səbəb)."""
    evs, cover = [], {}
    for key in TOP:
        lg = data.get(key)
        if not lg:
            continue
        for rnd in lg["rounds"]:
            plan = round_plan(lg, rnd)
            if not plan or not rnd.isdigit():
                continue
            for g in plan["core"]:
                cover[(key, g["i"])] = plan["slot"].date()
            evs.append(_ev("liqa-tur", f"liqa-{key}-{lg['season']}-t{rnd}", plan["slot"],
                           lambda now, key=key, lg=lg, rnd=rnd: round_item(key, lg, rnd, now), league=key))
    for key in NIGHTS:
        lg = data.get(key)
        if not lg:
            continue
        for md, games in lg["rounds"].items():
            if not games or any(g["t"] is None for g in games):
                continue
            slot = _morning(max(g["t"] for g in games))
            for g in games:
                cover[(key, g["i"])] = slot.date()
            evs.append(_ev("avrokubok", f"avrokubok-{key}-{lg['season']}-t{_slug(md)}", slot,
                           lambda now, key=key, lg=lg, md=md: night_item(key, lg, md, now), prio=NIGHTS[key]["prio"], league=key))
    days = {}
    for key in OTHER:
        lg = data.get(key)
        if not lg:
            continue
        for rnd in lg["rounds"]:
            plan = round_plan(lg, rnd)
            if plan and rnd.isdigit():
                days.setdefault(_other_window(plan["last"] + FOOT_READY), []).append((key, rnd))
    for day, rounds in sorted(days.items()):
        evs.append(_ev("liqa-diger", f"liqa-diger-{day.isoformat()}", datetime.datetime.combine(day, datetime.time(10, 30), BAKU),
                       lambda now, day=day, rounds=rounds: other_item(data, day, rounds, now)))
    leagues = [data[k] for k in LEADER_LEAGUES if k in data]
    dated = [g["t"] for lg in leagues for g in lg["games"] if g["t"] is not None]
    if dated:
        monday = _bk(min(dated)).date()
        monday += DAY * ((7 - monday.weekday()) % 7)
        end = _bk(max(dated)).date() + 7 * DAY
        while monday <= end:
            since = datetime.datetime.combine(monday - 7 * DAY, datetime.time(0, 0), BAKU)
            upto = datetime.datetime.combine(monday, datetime.time(0, 0), BAKU)
            n = sum(1 for lg in leagues if _active(lg, since, upto))
            extra = {} if n >= LEADERS_MIN else {"why": f"son həftə yalnız {n} çempionatda oyun var (beynəlxalq fasilə)"}
            evs.append(_ev("liqa-liderler", f"liqa-liderler-{monday.isoformat()}", datetime.datetime.combine(monday, datetime.time(9, 0), BAKU),
                           lambda now, monday=monday: leaders_item(data, monday, now), **extra))
            monday += 7 * DAY
    for key in CUPS:
        lg = data.get(key)
        if not lg:
            continue
        for stage, games in lg["rounds"].items():
            if not games or any(g["t"] is None for g in games):
                continue
            extra = {} if any(g["home"] in BIG or g["away"] in BIG for g in games) else {"why": "böyük klub oynamır"}
            evs.append(_ev("kubok", f"kubok-{key}-{lg['season']}-{_slug(stage)}", _slot_after(max(g["t"] for g in games) + CUP_READY),
                           lambda now, key=key, lg=lg, stage=stage: cup_item(key, lg, stage, now), league=key, **extra))
    for comp in (*TOP, *NIGHTS):
        lg = data.get(comp)
        if not lg:
            continue
        for g in lg["games"]:
            bigs = [s for s in (g["home"], g["away"]) if s in BIG]
            if not bigs or g["t"] is None:
                continue
            slot = _slot_after(g["t"] + FOOT_READY)
            extra = {}
            if cover.get((comp, g["i"])) == slot.date():
                extra["why"] = "oyun həmin gün dərc olunan tur icmalındadır"
            evs.append(_ev("klub-oyunu", f"klub-{comp}-{lg['season']}-{g['home']}-{g['away']}", slot,
                           lambda now, comp=comp, lg=lg, g=g: club_item(comp, lg, g, now),
                           rank=(min(BIG[s] for s in bigs), g["t"], g["i"]), league=comp, **extra))
    lg = data.get("nba")
    if lg:
        for d in sorted({g["d"] for g in lg["games"] if g["d"]}):
            try:
                us = datetime.date.fromisoformat(d)
            except ValueError:
                continue
            evs.append(_ev("nba", f"nba-{d}", datetime.datetime.combine(us + DAY, datetime.time(9, 0), BAKU),
                           lambda now, lg=lg, us=us: nba_item(lg, us, now)))
    lg = data.get("avroliqa")
    if lg:
        for rnd, games in lg["rounds"].items():
            if rnd.isdigit() and games and all(g["t"] is not None for g in games):
                evs.append(_ev("avroliqa", f"avroliqa-{lg['season']}-t{rnd}", _slot_after(max(g["t"] for g in games) + BASKET_READY),
                               lambda now, lg=lg, rnd=rnd: euro_item(lg, rnd, now)))
    return evs


def day_plan(evs, day):
    """Günün planı: böyük klub oyunu ən çox 3 (əvvəl Türkiyə klubları, sonra «Real Madrid» və «Barcelona»), cəmi ən çox 8
    (vaciblik sırası ilə). Plan cədvəldən qurulur, ona görə gün ərzində dəyişmir. Qaytarır: (qalanlar, limitə düşənlər)."""
    todays = [e for e in evs if e["slot"].date() == day and not e.get("why")]
    clubs = sorted((e for e in todays if e["kind"] == "klub-oyunu"), key=lambda e: e["rank"])
    extra = clubs[CLUB_CAP:]
    drop = {e["key"] for e in extra}
    todays = sorted((e for e in todays if e["key"] not in drop), key=lambda e: (e["prio"], e["slot"], e["key"]))
    return todays[:DAILY_CAP], todays[DAILY_CAP:] + extra


def cut_reason(evs, e):
    """Hadisə günün planından limitə görə çıxıbsa, səbəbi; yoxsa boş sətir."""
    day = e["slot"].date()
    if e["key"] not in {c["key"] for c in day_plan(evs, day)[1]}:
        return ""
    if e["kind"] == "klub-oyunu":
        clubs = sorted((x for x in evs if x["kind"] == "klub-oyunu" and x["slot"].date() == day and not x.get("why")),
                       key=lambda x: x["rank"])
        if e["key"] in {x["key"] for x in clubs[CLUB_CAP:]}:
            return f"böyük klub oyunu limiti (gündə {CLUB_CAP})"
    return f"gündəlik limit ({DAILY_CAP})"


def items(root, now, fetch=None):
    """now anında (Bakı) dərc olunacaq xəbərlər: slotu gəlmiş, məlumatı tam və slotdan 14 saatdan çox keçməmiş.
    fetch işlənmir: modul sorğu göndərmir."""
    now = _aware(now)
    evs = events(load(root))
    out = []
    for day in (now.date() - DAY, now.date()):
        for e in day_plan(evs, day)[0]:
            if e["slot"] <= now <= e["slot"] + LATE:
                item, _ = e["make"](now)
                if item and item.get("worth"):
                    out.append(item)
    out.sort(key=lambda i: (i["date"], i["slot"], i["key"]))
    return out


# --- Sınaq --------------------------------------------------------------------------------------------------

def _latest(evs, now):
    """Hər növün ən son real halları (slotu now-dan əvvəl olan)."""
    past = sorted((e for e in evs if e["slot"] <= now), key=lambda e: (e["slot"], e["key"]))
    out = []
    for key in TOP:
        out += [e for e in past if e["kind"] == "liqa-tur" and e.get("league") == key][-1:]
    out += [e for e in past if e["kind"] == "liqa-diger"][-1:]
    mondays = [e for e in past if e["kind"] == "liqa-liderler"]
    if mondays and mondays[-1].get("why"):     # son bazar ertəsi fasilədir: ondan əvvəlki adi həftəni də göstər
        out += [e for e in mondays if not e.get("why")][-1:]
    out += mondays[-1:]
    recent = now - 21 * DAY
    for key in CUPS:
        out += [e for e in past if e["kind"] == "kubok" and e.get("league") == key and e["slot"] >= recent][-1:]
    for key in NIGHTS:
        out += [e for e in past if e["kind"] == "avrokubok" and e.get("league") == key][-1:]
    clubs = [e for e in past if e["kind"] == "klub-oyunu"]
    out += [e for e in clubs if not e.get("why")][-3:] + [e for e in clubs if e.get("why")][-2:]
    out += [e for e in past if e["kind"] == "nba"][-1:]
    out += [e for e in past if e["kind"] == "avroliqa"][-1:]
    return out


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu günün planı və hər növün son real halı, öz slot vaxtında qurulmuş."""
    now = _aware(now or datetime.datetime.now(BAKU))
    md = ["## Xarici futbol və basketbol (oz_futbol_dunya.py)", "",
          f"Sınaq vaxtı: {now:%d.%m.%Y %H:%M} (Bakı). Mənbə: saytın data/futbol faylları, şəbəkə sorğusu yoxdur. "
          f"Gündə ən çox {DAILY_CAP} xəbər, böyük klub oyunu ən çox {CLUB_CAP}.", ""]
    data = load(root)
    if not data:
        return md + ["> data/futbol faylları tapılmadı: xəbər yoxdur.", ""]
    evs = events(data)
    keep, cut = day_plan(evs, now.date())
    md += [f"### Bu gün, {ox.day_text(now)}: plan", ""]
    if not keep and not cut:
        md += ["> Bu gün üçün planda xəbər yoxdur.", ""]
    for e in keep:
        if now < e["slot"]:
            status = "slotu gəlməyib"
        else:
            item, why = e["make"](now)
            status = "✅ hazırdır" if item else f"⏳ {why}"
        md.append(f"- {e['slot']:%H:%M} · {LABEL[e['kind']]} · `{e['key']}` — {status}")
    for e in cut:
        md.append(f"- {e['slot']:%H:%M} · {LABEL[e['kind']]} · `{e['key']}` — ✂ {cut_reason(evs, e)}")
    md += ["", "### Son real hallar (hərəsi öz slot vaxtında qurulub)", ""]
    for e in _latest(evs, now):
        at = e["slot"]
        md += [f"**{LABEL[e['kind']]} · {ox.day_text(at)} {at.year}, {at:%H:%M}** · `{e['key']}`", ""]
        item, why = e["make"](at)
        if item:
            md += ox.render(item)
        cut_why = "" if e.get("why") or not item else cut_reason(evs, e)
        if e.get("why"):
            md += [f"⏭ Dərc olunmazdı: {e['why']}", ""]
        elif not item:
            md += [f"⏭ Dərc olunmazdı: {why}", ""]
        elif cut_why:
            md += [f"⏭ Dərc olunmazdı: {cut_why}", ""]
        else:
            md += ["✅ Dərc olunardı", ""]
    if "kl" in data and not any(g["ok"] for g in data["kl"]["games"]):
        md += ["> Konfrans Liqası: kl.json-da hələ nəticə yoxdur, tur xəbəri nəticələr gələndə çıxacaq.", ""]
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    when = _arg(argv, "--now")
    now = _when(when) if when else None
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
