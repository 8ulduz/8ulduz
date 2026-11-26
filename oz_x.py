"""X-dən videolu xəbərlər: türk dilli rəsmi hesabların videolu paylaşımları əsasında ƏVVƏLCƏDƏN YAZILMIŞ xəbərlərin növbəsi
(sahib, 2026-11-18: «x la iş qura bilsək belə özəl 8ulduz xəbərləri verə bilərik saytda hətta videolu», «əsas türk dilində
olsun mənbələr», yerləşmə: Video bölməsi, «Son xəbərlər» lenti, xəbərin öz səhifəsi — «Bəli, başla»).

Niyə növbə faylı (oz_dunya ilə eyni səbəb): açarsız maşın tərcüməsi GitHub-dan işləmir. Mətni planlı Claude tapşırığı
yazır: X-in açıq məlumatından (API-siz: api.fxtwitter.com hesab lenti) HESABLAR-dakı hesabların videolu paylaşımlarını
götürür, Azərbaycan dilində qısa xəbər yazır və bu faylın yanındakı oz_x.json-a qoyur. Modul yalnız həmin faylı oxuyur:
sorğu göndərmir (gündə 0 sorğu), süni intellekt çağırmır.

Video saytda saxlanmır: X-in öz serverindən (video.twimg.com) oynayır, yalnız oxucu basanda. X videonu başqa saytdan
gələn sorğuya vermir (403), mənbə ünvanı göndərilməyəndə verir: tətbiq onu referrer göndərməyən iframe-də (srcdoc),
statik səhifə isə <meta name="referrer" content="no-referrer"> ilə açır. X-in skripti heç yerdə yüklənmir.

Növbə faylı: {"v": 1, "items": [sətir, ...]}. Sətir:
  id      paylaşımın nömrəsi (yalnız rəqəm; açar «x-<id>» olur)
  date    ilk dərc günü (Bakı), until: son gün (yazılmasa date + 1 gün; ən çoxu date + 3 gün)
  slot    «SS:DD», 07:00–23:59
  kind    NOVLER-dən biri (bölməni o təyin edir)
  title, lead, body (1–4 abzas)
  handle  HESABLAR-dakı hesab (credit cədvəldəki addır)
  post    paylaşımın ünvanı: https://x.com/<handle>/status/<id>
  video   https://video.twimg.com/...mp4 (paylaşımın mp4 variantı, 720p-dən böyük olmayan)
  poster  https://pbs.twimg.com/... (videonun öz şəkli)
  w, h    videonun ölçüsü (piksel)
  src     paylaşımın orijinal mətni (türkcə): xəbərdəki HƏR RƏQƏM burada olmalıdır. Dərc olunmur.

Qapılar (qırmızı xətt 2 və 4): check() sətri rədd edir, əgər oz_dunya-nın mətn qapıları pozulub (uzunluq, nisbi gün sözü,
kiril, nida, keçid, mənbədə olmayan rəqəm, rəhbərliyin adı) və ya
- hesab cədvəldə yoxdur, post/video/poster ünvanı göstərilən formada deyil, ölçü yararsızdır;
- mətndə və ya mənbə mətnində Azərbaycan mövzusu var (content_policy.AZ_TERMS, LEADER_TERMS): xarici mənbədən Azərbaycan
  haqqında xəbər düşmür. İdman hesabı da istisna deyil (məsələn «Karabağ» oyunu da düşür).
Dərc hissəsinin öz qapısı (oz_derc.gate) bundan sonra yenə işləyir.

Sınaq: python oz_x.py --sinaq --root DIR [--now 2026-11-19T12:00+04:00]
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.parse

import content_policy
import oz_dunya as dn
import oz_xeber as ox

BAKU = ox.BAKU
NOVBE = pathlib.Path(__file__).resolve().with_suffix(".json")
KEY = "x-"
BODY_MAX = 4
SRC_MAX = 2
SRC_LEN = (10, 1200)
SLOT_FROM, SLOT_TO = "07:00", "23:59"
SIZE = (120, 4096)
TEKRAR = "id təkrarlanır"

# Növ -> mövzu. Hamısı bir mövzudur («video»): dərc hissəsində X xəbərlərinin öz gündəlik həddi var (oz_derc.MOVZU_HEDD),
# futbol modullarının «idman» yerini tutmur. Bölmə oz_derc.BOLME_NOV-dadır.
NOVLER = {"x-idman": "video", "x-dunya": "video", "x-elm": "video", "x-maraqli": "video",
          "x-transfer": "transfer"}   # sahib 2026-11-19: X-in transfer xəbərləri (Romano, Moretto …) — videosuz ola bilər
# Transfer hesabları: əsasən mətn və şəkil paylaşır, video tələb olunmur (kind="x-transfer"). Başlıqda «transfer» sözü olur:
# saytın «Transfer xəbərləri» bölməsi (app.js TRANSFER_WORDS) xəbəri bu sözlə tanıyır.
TRANSFER_HESABLAR = {"FabrizioRomano": "Fabrizio Romano", "MatteMoretto": "Matteo Moretto", "DeadlineDayLive": "Transfer News Live",
                     "ekremkonur": "Ekrem Konur", "David_Ornstein": "David Ornstein"}

# Hesab -> xəbərdə göstərilən ad. Yalnız ilkin mənbələr: agentliklər, yayımçılar, klublar, federasiya, qurumlar.
# Başqasının videosunu yenidən paylaşan «xəbər» hesabları (məsələn THS Haber) yoxdur: video ilə başlıq çox vaxt uyğun gəlmir.
HESABLAR = {
    "anadoluajansi": "Anadolu Agentliyi",
    "aa_spor": "AA İdman",
    "trthaber": "TRT Haber",
    "trtspor": "TRT Spor",
    "ntvspor": "NTV Spor",
    "beINSPORTS_TR": "beIN SPORTS Türkiyə",
    "dhainternet": "Demirören Xəbər Agentliyi (DHA)",
    "ihacomtr": "İhlas Xəbər Agentliyi (İHA)",
    "euronews_tr": "Euronews Türkçe",
    "TFF_Org": "Türkiyə Futbol Federasiyası",
    "MilliTakimlar": "Türkiyə millisi",
    "GalatasaraySK": "Qalatasaray",
    "Fenerbahce": "Fənərbağça",
    "Besiktas": "Beşiktaş",
    "Trabzonspor": "Trabzonspor",
    "TUBITAK": "TÜBİTAK",
    # Sahib, 2026-11-19 («Bəli, 10-u əlavə et»): videosu çox olan xəbər və maraqlı hesablar. Münaqişə hesabları ağır kadr
    # verə bilər: yazıcının təlimatı (x_yazici.PROMPT) onları seçmir, təsdiqlənməmiş iddianı hesabın adı ilə verir.
    "TamirveTadilat": "Tamir & Tadilat",
    "clashreport": "Clash Report",
    "ConflictTR": "Conflict",
    "gusholderhaber": "Gusholder Haber",
    "Pars_Pluss": "Pars Plus",
    "avionot": "Avionot",
    "Derinkuvvet": "Derin Kuvvetler",
    "gdhdijital": "GDH",
    "ozetgechaber": "Özet Geç",
    "VoiceOfLevant": "Voice of Levant",
    # Sahib, 2026-11-19: «Azərbaycanda ən çox hansı tip qısa videolara baxıldığını araşdırıb x da o mənbələri tap» — Videolent üçün
    # vizual hesablar (idman, elm/maraqlı, oyun); FxTwitter ilə yoxlanıb, gündə 3+ video (research_notes/qisa-video-menbeleri.md).
    # Əlavə olunmayıb: siyasi şərh (TheFigen_, Pirat_Nation), mərc/kazino reklamı, qan riski (ufc), danışıq videoları (ClutchPoints).
    "Rainmaker1973": "Massimo (Rainmaker1973)",
    "LaLiga": "LaLiga",
    "premierleague": "Premyer Liqa",
    "aspor": "A Spor",
    "buitengebieden": "Buitengebieden",
    "IGN": "IGN",
    "ChampionsLeague": "UEFA Çempionlar Liqası",
    "Ballislife": "Ballislife",
    "Fotomac": "Fotomaç",
    "Yoda4ever": "Yoda4ever",
    "wonderofscience": "Wonder of Science",
    "DAZNFootball": "DAZN Football",
    "atptour": "ATP Tour",
    "F1": "Formula 1",
    "NBA": "NBA",
    "TivibuSpor": "Tivibu Spor",
    "ESPNUK": "ESPN UK",
    "TansuYegen": "Tansu Yegen",
    "ESPNNBA": "ESPN NBA",
    "WWE": "WWE",
    "EuropaLeague": "UEFA Avropa Liqası",
    "LFC": "Liverpul",
    "GameSpot": "GameSpot",
    "Discovery": "Discovery",
    "ajansspor": "Ajansspor",
    "MLS": "MLS",
    "Olympics": "Olimpiya Oyunları",
    "overtime": "Overtime",
}
HESABLAR.update(TRANSFER_HESABLAR)
_HANDLE = {h.lower(): h for h in HESABLAR}

# Videolent mənbələri (sahib, 2026-11-19: «maraqlı video mənbəyini 10 qat artır. video axını tiktok kimi olsun»): yalnız qısa video
# lenti üçün, bunlardan xəbər yazılmır. Yazıcı hər işdə siyahının bir hissəsini növbə ilə yoxlayır (x_yazici.VL_PER_RUN).
# FxTwitter ilə 2026-11-19-da yoxlanıb: hesab var və son 3 gündə video paylaşıb. Mərc, qan və böyüklər üçün məzmun hesabları
# yoxdur; Azərbaycan və Ermənistan mövzusu hər videoda ayrıca süzülür (reel_check). Xəbər və siyasətin kadr arxası hesabları
# sahibin 2026-11-22 göstərişi ilədir («xəbər mahiyyətli videolar, siyasi kontekstdə arxa qapı videoları»; qrup «xeber»).
# Mövzular (sahib, 2026-11-19: «videoların əksəriyyəti futboldur. belə olmasın proporsional olsun müxtəlif mövzular»): yazıcı hər
# işdə və lent axında videoları mövzulara bərabər paylayır (x_yazici.by_topic, lent.js mix).
VIDEOLENT_QRUPLAR = {
    "tebiet": {   # Heyvan və təbiət (114; saylar 2026-11-26)
        "AMAZlNGNATURE": "Nature is Amazing", "AnimalBeingBros": "AnimalBeingBros", "AnimalPlanet": "Animal Planet",
        "AnimalsLover": "AnimalsLover", "AnimalsWithKids": "AnimalsWithKids", "AnimalsWorId": "AnimalsWorId",
        "Animals_Vibes": "Animals_Vibes", "AquariumPacific": "AquariumPacific", "ASPCA": "ASPCA",
        "AustraliaZoo": "AustraliaZoo", "AustraliaZoo_": "AustraliaZoo_", "AwesomeAnimals": "AwesomeAnimals",
        "battersea": "battersea", "BBCEarth": "BBC Earth", "BBCSpringwatch": "BBCSpringwatch",
        "BBCWeather": "BBCWeather", "beautifulplaces": "BeautifulPlaces", "BestEarthPix": "BestEarthPix",
        "BestNatureVids": "BestNatureVids", "BigCatRescue": "BigCatRescue", "BindiIrwin": "BindiIrwin",
        "Bodegacats_": "Bodega Cats", "BornFreeFDN": "BornFreeFDN", "BristolZoo": "BristolZoo",
        "BronxZoo": "Bronx Zoo", "Cats_Protection": "Cats_Protection", "CatWorkers": "cats with jobs",
        "ChesterZoo": "Chester Zoo", "CincinnatiZoo": "Cincinnati Zoo", "CuteAnimals": "CuteAnimals",
        "CuteEmergency": "CuteEmergency", "DenverZoo": "DenverZoo", "DisneyAnimals": "DisneyAnimals",
        "DogsTrust": "DogsTrust", "dog_feelings": "dog_feelings", "dog_rates": "dog_rates",
        "DurrellWildlife": "DurrellWildlife", "earthcurated": "earthcurated", "Earthlings_Vids": "Earthlings_Vids",
        "EarthPix": "Earthpix", "Edinburgh_Zoo": "Edinburgh_Zoo", "EmrgencyKittens": "EmrgencyKittens",
        "exploreorg": "exploreorg", "GeorgiaAquarium": "Georgia Aquarium", "HoustonZoo": "Houston Zoo",
        "IrwinRobert": "IrwinRobert", "IUCN": "IUCN", "KoalaHospital": "KoalaHospital",
        "LAZoo": "Los Angeles Zoo", "MeowFriends": "MeowFriends", "metoffice": "metoffice",
        "MontereyAq": "Monterey Bay Aquarium", "NatGeo": "National Geographic", "natgeoanimals": "natgeoanimals",
        "NatGeoPhotos": "NatGeoPhotos", "NatGeoUK": "NatGeoUK", "NatGeoWild": "NatGeoWild",
        "NationalZoo": "National Zoo", "NatureisAmazing": "Amazing Nature", "NatureIsLit": "Nature Is Lit",
        "NatureVibes": "NatureVibes", "Nature_and_Pets": "Nature_and_Pets", "nature_org": "nature_org",
        "NEAQ": "NEAQ", "NHC_Atlantic": "NHC_Atlantic", "NOAA": "NOAA Satellites",
        "NWS": "National Weather Service", "NWSSPC": "NWS Storm Prediction Center", "oceana": "oceana",
        "OceanX": "OceanX", "OregonZoo": "OregonZoo", "PetsRule": "PetsRule",
        "PhillyZoo": "PhillyZoo", "PhotoArk": "PhotoArk", "ReedTimmerUSA": "ReedTimmerUSA",
        "RSPCA_official": "RSPCA_official", "SanDiegoZoo": "San Diego Zoo Wildlife Alliance", "SDZoo": "SDZoo",
        "SDZSafariPark": "SDZSafariPark", "SeaWorld": "SeaWorld", "SheddAquarium": "SheddAquarium",
        "SheldrickTrust": "SheldrickTrust", "SmithsonianNMNH": "SmithsonianNMNH", "SmithsonianZoo": "SmithsonianZoo",
        "spann": "spann", "stlzoo": "stlzoo", "StormchaserUKEU": "StormchaserUKEU",
        "TarongaZoo": "Taronga Zoo", "TheDodo": "The Dodo Blog", "theoceancleanup": "theoceancleanup",
        "ThePhotoHour": "ThePhotoHour", "the_wild_side_": "the_wild_side_", "TorontoZoo": "TorontoZoo",
        "USGSVolcanoes": "USGSVolcanoes", "USGS_Quakes": "USGS Earthquakes", "volcaholic1": "volcaholic1",
        "weatherchannel": "The Weather Channel", "WeatherNation": "WeatherNation", "Whales_org": "Whales_org",
        "WildAid": "WildAid", "WildEarth": "WildEarth", "WildlifeAid": "WildlifeAid",
        "WildlifeTrusts": "The Wildlife Trusts", "Wildlife_Planet": "Wildlife_Planet", "wildlife_videos": "wildlife_videos",
        "woodlandparkzoo": "woodlandparkzoo", "WWF": "WWF", "ZooMiami": "ZooMiami",
        "ZSL": "ZSL", "ZSLLondonZoo": "London Zoo",
        # Ekstremal hava hesabları (Hava Forum, Colin McCarthy, Ryan Hall, Max Velocity) 2026-11-26 «xeber» qrupuna köçüb.
    },
    "elm": {   # Elm, kosmos, tarix (120)
        "AmerMuseum": "AmerMuseum", "AMNH": "AMNH", "Archaeologymag": "Archaeologymag",
        "Arianespace": "Arianespace", "AsapSCIENCE": "AsapSCIENCE", "AstroBehnken": "AstroBehnken",
        "AstronomyMag": "AstronomyMag", "AstroVicGlover": "AstroVicGlover", "astro_christina": "astro_christina",
        "Astro_Jessica": "Astro_Jessica", "astro_pettit": "astro_pettit", "BBCScienceNews": "BBCScienceNews",
        "blueorigin": "Blue Origin", "BrianRoemmele": "Brian Roemmele", "britishmuseum": "britishmuseum",
        "calacademy": "calacademy", "Caltech": "Caltech", "Cambridge_Uni": "Cambridge_Uni",
        "CERN": "CERN", "chandraxray": "chandraxray", "CNES": "CNES",
        "DLR_en": "DLR_en", "engineers_feed": "World of Engineering", "HowThingsWork_": "How Things Work", "sciencegirl": "Science girl", "Erdayastronaut": "Erdayastronaut",
        "esa": "European Space Agency", "esaoperations": "esaoperations", "esaspaceflight": "esaspaceflight",
        "ESA_EO": "ESA_EO", "ESA_ES": "ESA_ES", "ESA_Italia": "ESA_Italia",
        "ESA_Webb": "ESA_Webb", "ESO": "ESO", "Exploratorium": "Exploratorium",
        "exploreplanets": "exploreplanets", "FieldMuseum": "FieldMuseum", "gunsnrosesgirl3": "gunsnrosesgirl3",
        "Harvard": "Harvard", "HISTORY": "HISTORY", "HistoryHit": "HistoryHit",
        "historyinmemes": "Historic Vids", "historyinpics": "History Photographed", "IFLScience": "IFLScience",
        "ISRO": "ISRO", "JAXA_en": "JAXA_en", "JAXA_jp": "JAXA_jp",
        "Kurz_Gesagt": "Kurz_Gesagt", "LiveScience": "LiveScience", "MachinePix": "MachinePix",
        "MarsCuriosity": "MarsCuriosity", "metmuseum": "metmuseum", "minutephysics": "minutephysics",
        "MIT": "MIT", "MuseeLouvre": "MuseeLouvre", "NASA": "NASA",
        "NASAAmes": "NASAAmes", "NASAArtemis": "NASAArtemis", "NASAEarth": "NASA Earth",
        "NASAGlenn": "NASAGlenn", "NASAGoddard": "NASAGoddard", "NASAhistory": "NASAhistory",
        "NASAHubble": "Hubble", "NASAJPL": "NASAJPL", "NASAJuno": "NASAJuno",
        "NASAKennedy": "NASA's Kennedy Space Center", "NASAMars": "NASAMars", "NASAMoon": "NASAMoon",
        "NASAPersevere": "NASAPersevere", "NASASolarSystem": "NASASolarSystem", "NASASpaceflight": "NASASpaceflight",
        "NASASun": "NASASun", "NASAVoyager": "NASAVoyager", "NASAWebb": "NASA Webb Telescope",
        "NASAWebb_ES": "NASAWebb_ES", "NASA_Astronauts": "NASA_Astronauts", "NASA_es": "NASA_es",
        "NASA_Johnson": "NASA_Johnson", "NASA_Marshall": "NASA Marshall", "NASA_Orion": "NASA_Orion",
        "NASA_SLS": "NASA_SLS", "NASA_TESS": "NASA_TESS", "NASA_Wallops": "NASA_Wallops",
        "NatHistoryMuse": "NatHistoryMuse", "NationalGallery": "NationalGallery", "Nature": "Nature",
        "NewAtlas": "NewAtlas", "newscientist": "newscientist", "NHM_London": "NHM_London",
        "physicsJ": "Dr James O'Donoghue", "physorg_com": "physorg_com", "PopMech": "PopMech",
        "PopSci": "PopSci", "Ri_Science": "Ri_Science", "RocketLab": "Rocket Lab",
        "sciam": "sciam", "ScienceChannel": "Science Channel", "ScienceGuys": "TomoWaku",
        "ScienceMagazine": "ScienceMagazine", "sciencemuseum": "sciencemuseum", "ScienceNews": "ScienceNews",
        "SETIInstitute": "SETIInstitute", "smartereveryday": "smartereveryday", "Smithsonian": "Smithsonian",
        "SmithsonianMag": "SmithsonianMag", "SmithsonianNASM": "SmithsonianNASM", "spacecom": "spacecom",
        "SPACEdotcom": "SPACEdotcom", "SpaceflightNow": "SpaceflightNow", "SpaceflightNow_": "SpaceflightNow_",
        "SpaceX": "SpaceX", "Space_Station": "International Space Station", "Stanford": "Stanford",
        "Tate": "Tate", "tedtalks": "tedtalks", "TED_ed": "TED_ed",
        "Uffizi": "Uffizi", "ULALaunch": "ULALaunch", "UniofOxford": "UniofOxford",
        "veritasium": "veritasium",
    },
    "texnika": {   # Texnika, avtomobil, aviasiya (159)
        "1x_tech": "1x_tech", "Adobe": "Adobe", "agilityrobotics": "agilityrobotics",
        "Airbus": "Airbus", "AirCanada": "AirCanada", "AirFranceKLM": "AirFranceKLM",
        "AirlineGeeks": "AirlineGeeks", "AlfaRomeo": "AlfaRomeo", "AMD": "AMD",
        "AmericanAir": "AmericanAir", "Amtrak": "Amtrak", "ANAJapan": "ANAJapan",
        "Android": "Android", "Apple": "Apple", "arduino": "arduino",
        "ArsTechnica": "ArsTechnica", "astonmartin": "astonmartin", "ASUS": "ASUS",
        "Audi": "Audi USA", "Autocar": "Autocar", "AutoExpress": "AutoExpress",
        "AviationWeek": "AviationWeek", "BBC_TopGear": "BBC_TopGear", "BentleyMotors": "BentleyMotors",
        "BMW": "BMW", "BMWMotorrad": "BMWMotorrad", "Boeing": "Boeing",
        "Bombardier": "Bombardier", "BostonDynamics": "Boston Dynamics", "British_Airways": "British_Airways",
        "Bugatti": "Bugatti", "BYDCompany": "BYDCompany", "Canon_UK": "Canon_UK",
        "caranddriver": "caranddriver", "carthrottle": "carthrottle", "carwow": "carwow",
        "Chevrolet": "Chevrolet", "CNET": "CNET", "CORSAIR": "CORSAIR",
        "DDE_Official": "DDE_Official", "dell": "dell", "Delta": "Delta",
        "DJI": "DJI", "DJIGlobal": "DJIGlobal", "Dodge": "Dodge",
        "Dyson": "Dyson", "Electrek": "Electrek", "EmbraerSA": "EmbraerSA",
        "emirates": "emirates", "engadget": "engadget", "etihad": "etihad",
        "Eurostar": "Eurostar", "evo_magazine": "evo_magazine", "Ferrari": "Ferrari",
        "Figure_robot": "Figure_robot", "flightradar24": "flightradar24", "Ford": "Ford Motor Company",
        "Fujifilm_UK": "Fujifilm_UK", "Gizmodo": "Gizmodo", "Google": "Google",
        "googlepixel": "googlepixel", "GoPro": "GoPro", "Gulfstream": "Gulfstream",
        "Hagerty": "Hagerty", "HarleyDavidson": "HarleyDavidson", "Honda": "Honda",
        "HONORglobal": "HONORglobal", "HP": "HP", "Huawei": "Huawei",
        "Hyundai": "Hyundai", "insta360": "insta360", "intel": "intel",
        "Jalopnik": "Jalopnik", "JapanAirlines": "JapanAirlines", "Jeep": "Jeep",
        "Kawasaki_Moto": "Kawasaki_Moto", "Kia": "Kia", "KLM": "KLM",
        "koenigsegg": "koenigsegg", "KoreanAir": "KoreanAir", "Lamborghini": "Lamborghini",
        "LandRover": "LandRover", "Lenovo": "Lenovo", "Lexus": "Lexus",
        "LGUS": "LGUS", "LogitechG": "LogitechG", "LotusCars": "LotusCars",
        "LucidMotors": "LucidMotors", "Lufthansa": "Lufthansa", "MaseratiHQ": "MaseratiHQ",
        "mashable": "mashable", "MazdaUSA": "MazdaUSA", "McLarenAuto": "McLarenAuto",
        "MercedesBenz": "Mercedes-Benz", "Microsoft": "Microsoft", "MINI": "MINI",
        "MKBHD": "MKBHD", "Motor1com": "Motor1com", "MotorTrend": "MotorTrend",
        "NikonUSA": "NikonUSA", "NIOGlobal": "NIOGlobal", "Nissan": "Nissan",
        "nothing": "nothing", "nvidia": "NVIDIA", "OnePlus_EU": "OnePlus_EU",
        "OpenAI": "OpenAI", "oppo": "oppo", "Peugeot": "Peugeot",
        "Polaris": "Polaris", "PolestarCars": "PolestarCars", "Porsche": "Porsche",
        "Qantas": "Qantas", "qatarairways": "Qatar Airways", "Raspberry_Pi": "Raspberry_Pi",
        "Razer": "Razer", "realmeglobal": "realmeglobal", "Renault": "Renault",
        "Rivian": "Rivian", "RollsRoyceCars": "RollsRoyceCars", "Samsung": "Samsung Electronics",
        "SamsungMobile": "Samsung Mobile", "SamsungUS": "SamsungUS", "ShmeeOfficial": "ShmeeOfficial",
        "SingaporeAir": "SingaporeAir", "Skoda": "Skoda", "Snapdragon": "Snapdragon",
        "sonyalpha": "sonyalpha", "SonyElectronics": "SonyElectronics", "SonyXperia": "SonyXperia",
        "SouthwestAir": "SouthwestAir", "subaru_usa": "subaru_usa", "supercarblondie": "supercarblondie",
        "techradar": "techradar", "TEKNOFESTTR": "TEKNOFESTTR", "baykartech": "BAYKAR", "TUSAS_TR": "TUSAŞ", "ROKETSAN": "ROKETSAN", "Tesla": "Tesla",
        "Tesla_Optimus": "Tesla_Optimus", "Togg": "Togg", "tomshardware": "tomshardware",
        "TopGear": "TopGear", "Toyota": "Toyota", "ToyotaGR": "ToyotaGR",
        "TurkishAirlines": "TurkishAirlines", "united": "united", "UnitreeRobotics": "Unitree",
        "verge": "verge", "Vespa": "Vespa", "VirginGalactic": "VirginGalactic",
        "vivo_global": "vivo_global", "Volvo": "Volvo", "VW": "VW",
        "WIRED": "WIRED", "Xiaomi": "Xiaomi", "XPengMotors": "XPengMotors",
        # usta işi (FxTwitter, 2026-11-23: 72 saatda 21–25 video): zavod istehsalı, bərpa, mühəndislik
        "Brand_Anuj": "Global Brand", "muhendisIiktr": "Mühendislik Harikası",
        "SawyerMerritt": "Sawyer Merritt",   # 2026-11-26: elektromobil, robotaksi, kosmos yenilikləri, median 200 min baxış
    },
    "yemek": {   # Yemək, səyahət, ev (85)
        "pratikdunya": "Pratik Dünya", "Airbnb": "Airbnb", "Allrecipes": "Allrecipes",
        "archdaily": "archdaily", "ArchDigest": "ArchDigest", "Australia": "Australia",
        "BBCFood": "BBCFood", "BBCGoodFood": "BBCGoodFood", "BettyCrocker": "BettyCrocker",
        "BHG": "BHG", "bonappetit": "bonappetit", "BonAppetitMag": "BonAppetitMag",
        "bookingcom": "bookingcom", "BrightSide": "BrightSide", "BuzzFeedTasty": "BuzzFeedTasty",
        "CNTraveler": "Condé Nast Traveler", "CookingLight": "CookingLight", "Delish": "Delish",
        "designboom": "designboom", "dezeen": "dezeen",
        "easyJet": "easyJet", "Eater": "Eater", "epicurious": "epicurious",
        "Expedia": "Expedia", "feelgoodfoodie": "Yumna Jawad Feel Good Foodie", "Food52": "Food52",
        "foodandwine": "foodandwine", "FoodBeast": "FoodBeast", "foodnetwork": "foodnetwork",
        "FoodNetworkUK": "FoodNetworkUK", "Food_Network": "Food_Network", "GBBO": "GBBO",
        "GermanyTourism": "GermanyTourism", "GordonRamsay": "Gordon Ramsay", "GoTurkiye": "Go Türkiye",
        "HGTV": "HGTV", "IKEAUSA": "IKEAUSA",
        "insiderfood": "insiderfood", "instructables": "instructables", "jamieoliver": "jamieoliver",
        "LonelyPlanet": "LonelyPlanet", "MarthaBakes": "MarthaBakes", "MarthaStewart": "MarthaStewart",
        "MasterChefAU": "MasterChefAU", "MasterChefUK": "MasterChefUK", "michelinguide": "michelinguide",
        "MySwitzerland": "MySwitzerland", "NatGeoTravel": "Nat Geo Travel", "NewZealand": "NewZealand",
        "Nigella_Lawson": "Nigella_Lawson", "nusr_et": "nusr_et", "NYCgo": "NYCgo",
        "NYTCooking": "NYTCooking", "nytfood": "nytfood", "Ryanair": "Ryanair",
        "seriouseats": "seriouseats", "Starbucks": "Starbucks", "tastemade": "tastemade",
        "Tasty": "Tasty", "TastyDemais": "TastyDemais", "TastyJapan": "Tasty Japan",
        "TastyRecetas": "TastyRecetas", "TastyUK": "TastyUK", "Tasty_UK": "Tasty_UK",
        "thekitchn": "thekitchn", "ThisOldHouse": "ThisOldHouse", "tourismnz": "tourismnz",
        "TravelChannel": "TravelChannel", "TravelLeisure": "Travel + Leisure", "Tripadvisor": "Tripadvisor",
        "VisitBritain": "VisitBritain", "VisitCalifornia": "VisitCalifornia",
        "visitdubai": "visitdubai", "VisitFinland": "VisitFinland", "visitgreecegr": "visitgreecegr",
        "VisitIceland_": "VisitIceland_", "visitlondon": "visitlondon", "VisitMaldives": "VisitMaldives",
        "VisitNorway": "VisitNorway", "visitscotland": "visitscotland", "VisitSpain": "VisitSpain",
        "VisitTheUSA": "VisitTheUSA", "VisitTurkiye": "VisitTurkiye", "Visit_Japan": "Visit_Japan",
        "Visit_Thailand": "Visit_Thailand",
    },
    "oyun": {   # Oyun və e-idman (94)
        "100Thieves": "100Thieves", "2K": "2K", "VidsThatGoHard": "vids that go hard", "Activision": "Activision",
        "assetto_corsa": "assetto_corsa", "BandaiNamcoUS": "BandaiNamcoUS", "Battlefield": "Battlefield",
        "Bethesda": "Fallout 76", "BLASTPremier": "BLASTPremier", "Blizzard_Ent": "Diablo Immortal",
        "BrawlStars": "BrawlStars", "CallofDuty": "Call of Duty", "CapcomUSA_": "CapcomUSA_",
        "Capcom_Unity": "Capcom_Unity", "CDPROJEKTRED": "CDPROJEKTRED", "ClashofClans": "Clash of Clans",
        "ClashRoyale": "Clash Royale", "CounterStrike": "CS2", "CSGO": "CSGO",
        "Dexerto": "Dexerto", "Diablo": "Diablo", "dota2": "DOTA 2",
        "EA": "Electronic Arts", "EAFootballClub": "EAFootballClub", "EAMaddenNFL": "EAMaddenNFL",
        "EpicGames": "EpicGames", "ESLCS": "ESL Counter-Strike", "ESLGaming": "ESLGaming",
        "EternalFireGG": "EternalFireGG", "FaZeClan": "FaZeClan", "FNATIC": "FNATIC",
        "Fortnite": "Fortnite", "FortniteGame": "FortniteGame", "ForzaMotorsport": "ForzaMotorsport",
        "FreeFire_TR": "FreeFire_TR", "G2esports": "G2esports", "GenshinImpact": "GenshinImpact",
        "GranTurismo": "GranTurismo", "GTAOnline": "GTAOnline", "Hasbro": "Hasbro",
        "Hearthstone": "Hearthstone", "HLTVorg": "HLTV.org", "honkaistarrail": "honkaistarrail",
        "HotWheels": "HotWheels", "HoYoverse_EN": "HoYoverse_EN", "iRacing": "iRacing",
        "Konami": "Konami", "Kotaku": "Kotaku", "LeagueOfLegends": "LeagueOfLegends",
        "Lego": "Lego", "lolesports": "lolesports", "Mattel": "Mattel",
        "Minecraft": "Minecraft", "MobileLegends": "MobileLegends", "MortalKombat": "MortalKombat",
        "natusvincere": "natusvincere", "NBA2K": "NBA2K", "Nerf": "Nerf",
        "NFSNL": "NFSNL", "Nintendo": "Nintendo", "NintendoAmerica": "Nintendo of America",
        "NintendoEurope": "NintendoEurope", "PCGamer": "PCGamer", "PlayApex": "Apex Legends",
        "PlayHearthstone": "PlayHearthstone", "PlayOverwatch": "PlayOverwatch", "PlayStation": "PlayStation",
        "PlayStationEU": "PlayStationEU", "PlayVALORANT": "VALORANT", "play_eFootball": "eFootball",
        "Pokemon": "Pokemon", "Polygon": "Polygon", "PUBG": "PUBG: BATTLEGROUNDS",
        "PUBGMOBILE": "PUBG MOBILE", "redbullgaming": "redbullgaming", "riotgames": "riotgames",
        "Roblox": "Roblox", "RockstarGames": "Rockstar Games", "SEGA": "SEGA",
        "SquareEnix": "SquareEnix", "StardewValley": "StardewValley", "Steam": "Steam",
        "StreetFighter": "StreetFighter", "Supercell": "Supercell", "TeamLiquid": "TeamLiquid",
        "Tekken": "Tekken", "Terraria": "Terraria", "Twitch": "Twitch",
        "Ubisoft": "Ubisoft", "ValorantEsports": "ValorantEsports", "WBGames": "WBGames",
        "WorldofWarcraft": "WorldofWarcraft", "Xbox": "XBOX", "XboxGamePass": "XboxGamePass",
    },
    "kino": {   # Kino, serial, musiqi, məşhurlar (151)
        "20thcentury": "20thcentury", "A24": "A24", "acdc": "acdc",
        "Adele": "Adele", "aespa_official": "aespa_official", "AleynaTilki": "AleynaTilki",
        "AppleMusic": "AppleMusic", "AppleTV": "AppleTV", "AppleTVPlus": "AppleTVPlus",
        "ArianaGrande": "ArianaGrande", "ATEEZofficial": "ATEEZofficial", "atvcomtr": "atv",
        "BABYMONSTER_YG": "BABYMONSTER_YG", "BBCiPlayer": "BBCiPlayer", "BBCOne": "BBCOne",
        "beinconnect_tr": "beinconnect_tr", "Beyonce": "Beyonce", "BIGBANG_YG": "BIGBANG_YG",
        "billboard": "billboard", "billieeilish": "billieeilish", "BLACKPINK": "BLACKPINK",
        "blutv": "Blu tv", "BrunoMars": "BrunoMars", "BTS_bighit": "BTS_bighit",
        "BTS_twt": "BTS_twt", "coldplay": "coldplay", "coldplay_": "coldplay_",
        "columbia": "columbia", "Crunchyroll": "Crunchyroll", "DCOfficial": "DCOfficial",
        "discoveryplus": "discoveryplus", "Disney": "Disney", "DisneyAnimation": "Disney Animation",
        "DisneyPixar": "DisneyPixar", "DisneyPlus": "DisneyPlus", "disneyplustr": "disneyplustr",
        "disneyplusuk": "disneyplusuk", "Drake": "Drake", "DreamWorks": "DreamWorks",
        "DuaLipa": "DuaLipa", "edsheeran": "edsheeran", "Eminem": "Eminem",
        "ENHYPEN_members": "ENHYPEN_members", "EXO_SMTOWN": "EXO_SMTOWN", "exxen": "exxen",
        "FocusFeatures": "FocusFeatures", "GameOfThrones": "GameOfThrones", "Gulsen": "Gulsen",
        "hadise": "hadise", "Harry_Styles": "Harry_Styles", "HBO": "HBO",
        "hbomax": "hbomax", "HBO_Max": "HBO_Max", "HouseofDragon": "HouseofDragon",
        "hulu": "hulu", "HYBEOFFICIALtwt": "HYBEOFFICIALtwt", "illumination": "illumination",
        "Imaginedragons": "Imaginedragons", "IMDb": "IMDb", "Interscope": "Interscope",
        "ITV": "ITV", "ITZYofficial": "ITZYofficial", "IVEstarship": "IVEstarship",
        "JBALVIN": "JBALVIN", "justinbieber": "justinbieber", "JYPETWICE": "JYPETWICE",
        "kanal7": "kanal7", "kanald": "kanald", "KAROLGMUSIC": "KAROLGMUSIC",
        "katyperry": "katyperry", "kenandogulu": "kenandogulu", "ladygaga": "ladygaga",
        "LegendaryEnt": "LegendaryEnt", "le_sserafim": "le_sserafim", "linkinpark": "linkinpark",
        "Lionsgate": "Lionsgate", "lizzo": "lizzo", "Lucasfilm": "Lucasfilm",
        "mabelmatiz": "mabelmatiz", "maroon5": "maroon5", "Marvel": "Marvel Entertainment",
        "MarvelStudios": "MarvelStudios", "Metallica": "Metallica", "MTV": "MTV",
        "muratboz": "muratboz", "MuratDalkilic": "MuratDalkilic", "NCTsmtown": "NCTsmtown",
        "neonrated": "neonrated", "Netflix": "Netflix", "netflixanime": "netflixanime",
        "NetflixBrasil": "NetflixBrasil", "NetflixIndia": "NetflixIndia", "NetflixJP": "NetflixJP",
        "NetflixKR": "NetflixKR", "NetflixMENA": "NetflixMENA", "netflixturkiye": "Netflix Türkiye",
        "NetflixUK": "NetflixUK", "netflix_es": "netflix_es", "nowtvturkiye": "NOW",
        "Olivia_Rodrigo": "Olivia_Rodrigo", "OneRepublic": "OneRepublic", "ParamountPics": "ParamountPics",
        "peacock": "peacock", "pixar": "pixar", "pledis_17": "pledis_17",
        "PostMalone": "PostMalone", "PrimeVideo": "Prime Video", "primevideotr": "primevideotr",
        "primevideouk": "primevideouk", "QueenWillRock": "QueenWillRock", "RecordingAcad": "RecordingAcad",
        "rihanna": "rihanna", "RottenTomatoes": "RottenTomatoes", "SabrinaAnnLynn": "SabrinaAnnLynn",
        "samsmith": "samsmith", "sanbenito": "sanbenito", "selenagomez": "selenagomez",
        "sezenaksu": "sezenaksu", "shakira": "shakira", "showtv": "Show TV",
        "SimgeSagin": "SimgeSagin", "SkyUK": "SkyUK", "SMTOWNGLOBAL": "SMTOWNGLOBAL",
        "sonymusic": "sonymusic", "SonyPictures": "SonyPictures", "Spotify": "Spotify",
        "startv": "startv", "StarWars": "StarWars", "Stranger_Things": "Stranger_Things",
        "Stray_Kids": "Stray_Kids", "Tarkan_Official": "Tarkan_Official", "taylorswift13": "taylorswift13",
        "TheBoysTV": "TheBoysTV", "theweeknd": "theweeknd", "treasuremembers": "treasuremembers",
        "TRT1": "TRT 1", "TRT2": "TRT2", "trtbelgesel": "TRT Belgesel",
        "TRTCocuk": "TRTCocuk", "tv8": "tv8", "TXT_members": "TXT_members",
        "U2": "U2", "UMG": "UMG", "UniversalPics": "UniversalPics",
        "Variety": "Variety", "WarnerBrosPics": "WarnerBrosPics", "WarnerMusic": "WarnerMusic",
        "YGEntertainment": "YGEntertainment",
        # 2026-11-26 (FxTwitter, 72 saat, median baxış): məşhurlar və əyləncə anları — TMZ 223 min, Pop Base 153 min, Pop Crave 121 min
        "TMZ": "TMZ", "PopBase": "Pop Base", "PopCrave": "Pop Crave",
    },
    "maraqli": {   # Maraqlı və gülməli (43)
        "9GAG": "9GAG", "AFV": "JH", "AFVofficial": "AFVofficial",
        "AFV_Official": "AFV_Official", "boredpanda": "boredpanda", "TheFigen_": "The Figen",
        "DudePerfect": "DudePerfect", "FailArmy": "FailArmy", "Fascinatingpics": "Fascinatingpics",
        "FreeRunning": "FreeRunning", "FunnyOrDie": "FunnyOrDie", "GWR": "GWR",
        "HumansNoContext": "HumansNoContext", "InternetH0F": "internet hall of fame", "Jukinmedia": "Jukinmedia",
        "JukinVideo": "JukinVideo", "JustForLaughs": "JustForLaughs", "ladbible": "ladbible",
        "MastersOfMotion": "MastersOfMotion", "MrBeast": "MrBeast", "nitrocircus": "nitrocircus",
        "NoContextBrits": "NoContextBrits", "NoContextHumans": "NoContextHumans", "OddIySatisfying": "Oddly Satisfying",
        "OnlyBangers_": "OnlyBangers_", "parkour": "parkour", "PeopleArePower": "PeopleArePower",
        "PicturesFoIder": "PicturesFoIder", "redbull": "Red Bull", "RedBullSnow": "RedBullSnow",
        "RedBullUSA": "RedBullUSA", "Ripleys": "Ripleys", "satisfyingsound": "satisfyingsound",
        "satisfying_vids": "satisfying_vids", "skydiving": "skydiving", "UberFacts": "UberFacts",
        "UNILAD": "UNILAD", "upworthy": "upworthy", "ViralHog": "ViralHog",
        "weirdlilguys": "cats being weird little guys", "wowterrifying": "wowterrifying", "XGames": "X Games",
        "FearedBuck": "FearBuck",   # 2026-11-26: internet məşhurlarının viral anları, median 513 min baxış (72 saatda 17 video)
    },
    "xeber": {   # Xəbər, hadisə anı və siyasətin kadr arxası (32; ilk 10-u sahib 2026-11-22). Median baxış: Collin Rugg 747 min, Fox News 193 min,
        # Macron 390 min, AP 82 min, Disclose.tv 74 min, Breaking911 59 min, Al Jazeera 54 min, Sky News 36 min, CBS 23 min, Nawfal 22 min
        "AP": "The Associated Press", "AJEnglish": "Al Jazeera English", "Breaking911": "Breaking911",
        "CBSNews": "CBS News", "CollinRugg": "Collin Rugg", "disclosetv": "Disclose.tv",
        "EmmanuelMacron": "Emmanuel Macron", "FoxNews": "Fox News", "MarioNawfal": "Mario Nawfal",
        "SkyNews": "Sky News",
        # Sahib 2026-11-23: «siyasət arxa qapı videoları maraqlı hadisə videoları yoxdur … ən çox baxılan videolar olsun». FxTwitter,
        # 2026-11-23 17:35–18:15 UTC, 72 saat, öz videoları: median baxış ≥ 50 min, ≥ 5 video. Hadisə anı: Pusholder 175 min, BPT 157 min
        # (Türkiyə); müharibə kadrı, ağır kadr görünmədi: OSINTdefender 153 min, OSINTtechnical 240 min; siyasətin pərdəarxası:
        # Zelenskiy 237 min, Aaron Rupar 91 min, Acyn 59 min, BBC Politics 56 min, Visegrád 24 53 min, Ağ Ev 170 min. Çıxarılan:
        # DailyLoud (öz videolarında Rainbet mərc reklamı), Megatron_ron, dom_lucre, WallStreetApes (təbliğat, icma qeydi, nifrət).
        "pusholder": "Pusholder", "bpthaber": "BPT", "sentdefender": "OSINTdefender", "OSINTtechnical": "OSINTtechnical",
        "ZelenskyyUa": "Volodymyr Zelenskyy", "atrupar": "Aaron Rupar", "Acyn": "Acyn", "BBCPolitics": "BBC Politics",
        "visegrad24": "Visegrád 24", "WhiteHouse": "The White House",
        # Sahib 2026-11-24 (X-in «Sizin üçün» lentindən 20 ekran şəkli): «bu kimi həm xəbər tipli, həm də digər çox maraqlı videolar olan
        # hesablardan istifadə etməyi təmin et». FxTwitter, 2026-11-24 ~13:40 UTC, 72 saat, öz videoları: GaGa Haber 7 video, median 46 min
        # baxış; Kupür Haber 12 / 6,1 min; Tiraj 18 / 4,5 min; THS Haber 11 / 4,4 min; Parasizceo 14 / 4,2 min. Baxış azdır, ona görə
        # VIDEOLENT_ONDE-də deyil: seçimdə baxış sayı ilə yarışırlar. Xəbər hesabı (HESABLAR) deyil: başqasının videosunu yayırlar, video ilə
        # başlıq çox vaxt uyğun gəlmir — Videolentdə yalnız qısa izahla. Crazy Clips (median 98 min) yoxdur: CrazyClips_ kimi kazino reklamı.
        "GagaHaberTR": "GaGa Haber", "HaberKupur": "Kupür Haber", "tirajnews": "Tiraj", "thshaber": "THS Haber", "Parasizceo": "Parasizceo",
        # Sahib 2026-11-26 («instagramda müəyyən etdiyimiz çox baxılan istiqamətlərini X ə tətbiq et»): hadisə yerindən kadr, Türkiyə.
        # FxTwitter, 2026-11-26 06:45–08:05 UTC, 72 saat, öz videoları (median baxış; docs/x-yazici.md «2026-11-26»): Boşuna Tıklama 87 min,
        # DarkWeb Haber 58 min (Türkiyənin rəqəmsal mediası: insan hekayəsi, hadisə, məşhurlar), NTV 36 min, BNO News 173 min,
        # Oliya Scootercaster 49 min (şahid kadrı), Insider Paper 31 min, ABC News 23 min (xilasetmə, qəza, təbiət hadisəsi).
        "bosunatiklama": "Boşuna Tıklama", "darkwebhaber": "DarkWeb Haber", "ntv": "NTV", "BNONews": "BNO News",
        "ScooterCasterNY": "Oliya Scootercaster", "TheInsiderPaper": "Insider Paper", "ABC": "ABC News",
        # Ekstremal hava və təbii fəlakətin anı — 2026-11-26 «tebiet»-dən köçürülüb (sahib: «nə heyvan nə təbiət nə kosmos», sonra
        # «ekstremal hadisələrə də»): «tebiet» qrupu sosial videoya düşmür, bu hesabların kadrı isə fırtına, sel, dalğa, qar içində
        # insan və maşındır (xilasetmə, son anda qurtulma). FxTwitter, 72 saat, median baxış: Hava Forum 124 min (Türkiyə),
        # Colin McCarthy 52 min, Ryan Hall 50 min, Max Velocity 27 min.
        "HavaForum": "Hava Forum", "US_Stormwatch": "Colin McCarthy", "RyanHallYall": "Ryan Hall, Y'all",
        "MaxVelocityWX": "Max Velocity",
    },
    "idman": {   # İdman (267)
        "10Ronaldinho": "10Ronaldinho", "433": "433", "nocontextfooty": "Out Of Context Football", "ufc": "UFC", "ringmagazine": "Ring Magazine", "acmilan": "AC Milan",
        "AFCAjax": "AFC Ajax", "AFCBournemouth": "AFC Bournemouth", "Alanyaspor": "Alanyaspor",
        "AlanyasporKlb": "AlanyasporKlb", "AlHilal_EN": "AlHilal_EN", "AlNassrFC": "AlNassrFC",
        "AlpineF1Team": "BWT Alpine Formula One Team", "Al_Ittihad": "Al_Ittihad", "AnadoluEfesSK": "AnadoluEfesSK",
        "AntalyasporAS": "Antalyaspor", "Arsenal": "Arsenal", "aspor_tv": "aspor_tv",
        "AstonMartinF1": "AstonMartinF1", "AstonVilla": "Aston Villa", "Atleti": "Atlético de Madrid",
        "AustralianOpen": "AustralianOpen", "beINSPORTS": "beIN SPORTS", "beINSPORTS_EN": "beINSPORTS_EN",
        "beINSPORTS_TV": "beINSPORTS_TV", "Benzema": "Benzema", "BesiktasBasket": "Beşiktaş Basket",
        "Besiktas_EN": "Besiktas_EN", "BHAFC": "Brighton & Hove Albion", "biathlonworld": "biathlonworld",
        "BigTen": "BigTen", "BJKTV": "BJKTV", "BlackYellow": "Borussia Dortmund",
        "BleacherReport": "BleacherReport", "Brasileirao": "Brasileirao", "Brentford": "Brent Langford",
        "brfootball": "BR Football", "Bucks": "Milwaukee Bucks", "Bundesliga": "Bundesliga",
        "Bundesliga_DE": "Bundesliga_DE", "Bundesliga_EN": "Bundesliga English", "BurgerKing": "BurgerKing",
        "Carabao_Cup": "Carabao Cup", "caykurrizespor": "caykurrizespor", "CBSSports": "CBSSports",
        "CBSSportsGolazo": "CBS Sports Golazo", "CelticFC": "Celtic Football Club", "celtics": "celtics",
        "CEVolleyball": "CEVolleyball", "championat": "championat", "ChelseaFC": "Chelsea FC",
        "chesscom": "chesscom", "chicagobulls": "Chicago Bulls", "CocaCola": "CocaCola",
        "CPFC": "Crystal Palace F.C.", "Cristiano": "Cristiano", "dakar": "dakar",
        "dallasmavs": "dallasmavs", "DAZN_ES": "DAZN_ES", "diarioas": "diarioas",
        "Dominos": "Dominos", "Ducati": "Ducati", "Eczacibasi_SK": "Eczacibasi_SK",
        "EFL": "EFL", "ehfcl": "ehfcl", "EmiratesFACup": "Emirates FA Cup",
        "Eredivisie": "Eredivisie", "ErlingHaaland": "ErlingHaaland", "espn": "ESPN",
        "ESPNArgentina": "ESPNArgentina", "ESPNBrasil": "ESPNBrasil", "ESPNFC": "ESPN FC",
        "ESPNFC_es": "ESPNFC_es", "ESPNmx": "ESPNmx", "EURO2028": "EURO2028",
        "EuroBasket2025": "FIBA EuroBasket 2025", "EuroLeague": "EuroLeague", "Everton": "Everton",
        "EyupsporKulubu": "EyupsporKulubu", "F1Academy": "F1Academy", "fanatik": "fanatik",
        "FBTVResmi": "FBTVResmi", "FCBarcelona": "FC Barcelona", "FCBayernEN": "FC Bayern",
        "FCPorto": "FC Porto", "Fenerbahce_EN": "Fenerbahce_EN", "FIAWEC": "FIAWEC",
        "FIBA": "FIBA", "FIBA3x3": "FIBA3x3", "FIBAWC": "FIBAWC",
        "FIDE_chess": "FIDE_chess", "FIFAcom": "FIFA", "FIFAWorldCup": "FIFA World Cup",
        "FISskijumping": "FISskijumping", "FIS_Alpine": "FIS_Alpine", "FIVBVolleyball": "FIVBVolleyball",
        "FootballDaily": "Football Daily", "Footballogue": "Footballogue", "Formula_E": "Formula_E",
        "FOXSoccer": "FOX Soccer", "foxsports": "foxsports", "FulhamFC": "Fulham Football Club",
        "galatasaraytv": "galatasaraytv", "GaziantepFK": "Gaziantep FK", "Gazzetta_it": "La Gazzetta dello Sport",
        "goal": "GOAL", "GoztepeSK": "ibrahim", "GSBasketbol": "Galatasaray MCT Technic",
        "HaasF1Team": "HaasF1Team", "haberturkspor": "haberturkspor", "handballworld": "handballworld",
        "HomeDepot": "HomeDepot", "HondaRacingCorp": "HondaRacingCorp", "HoopsNation": "HoopsNation",
        "HoustonRockets": "HoustonRockets", "IAmZlatan": "IAmZlatan", "ibfk2014": "İstanbul Başakşehir",
        "IBSFsliding": "IBSFsliding", "ICC": "ICC", "IMSA": "IMSA",
        "IndyCar": "IndyCar", "Inter": "Inter", "ISU_Figure": "ISU_Figure",
        "ISU_Speed": "ISU_Speed", "juventusfc": "JuventusFC", "Kaka": "Kaka",
        "KasimpasaSK": "Kasımpaşa", "Kayserispor": "Kayserispor", "KFC": "KFC",
        "kicker": "kicker", "KingJames": "KingJames", "KMbappe": "KMbappe",
        "konyaspor": "TÜMOSAN Konyaspor", "KTM_Racing": "KTM_Racing", "Lakers": "Los Angeles Lakers",
        "LaLigaEN": "LALIGA English", "LaLigaTV": "LaLigaTV", "LCFC": "Leicester City",
        "lequipe": "lequipe", "LeTour": "LeTour", "Libertadores": "CONMEBOL Libertadores",
        "LigaMXEN": "LigaMXEN", "ligaportugal": "ligaportugal", "Ligue1UberEats": "Ligue1UberEats",
        "Ligue1_ENG": "Ligue 1 English", "Lowes": "Lowes", "ManCity": "Manchester City",
        "ManUtd": "Manchester United", "MARCA": "MARCA", "marca_en": "marca_en",
        "marchmadness": "marchmadness", "MatchTV": "MatchTV", "McDonalds": "McDonalds",
        "McLarenF1": "McLarenF1", "MercedesAMGF1": "Mercedes-AMG PETRONAS F1 Team", "MiamiHEAT": "MiamiHEAT",
        "MLB": "MLB", "MLSes": "MLSes", "MotoGP": "MotoGP",
        "mundodeportivo": "Mundo Deportivo", "NASCAR": "NASCAR", "NBAAllStar": "NBAAllStar",
        "NBAEurope": "NBAEurope", "NBAHistory": "NBAHistory", "NBAonESPN": "NBAonESPN",
        "NBAonPrime": "NBAonPrime", "NBATV": "NBA TV", "NBA_Africa": "NBA_Africa",
        "NBCSports": "NBCSports", "NBCSportsSoccer": "NBC Sports Soccer", "NCAA": "NCAA",
        "Nescafe": "Nescafe", "neymarjr": "neymarjr", "NFFC": "Nottingham Forest",
        "NFL": "NFL", "NFLonCBS": "NFLonCBS", "NHL": "NHL",
        "NHLonSN": "NHLonSN", "ntvspor_tv": "ntvspor_tv", "NUFC": "Newcastle United",
        "nuggets": "nuggets", "nyknicks": "NEW YORK KNICKS", "OfficialASRoma": "AS Roma",
        "OfficialWRC": "FIA World Rally Championship", "okcthunder": "okcthunder", "paulpogba": "paulpogba",
        "Pepsi": "Pepsi", "PGATOUR": "PGA Tour", "PSG_English": "Paris Saint-Germain",
        "PSV": "PSV", "RangersFC": "Rangers Football Club", "realmadrid": "Real Madrid C.F.",
        "RedBullAir": "RedBullAir", "redbullbike": "redbullbike", "RedBullBMX": "RedBullBMX",
        "RedBullF1": "RedBullF1", "redbullMOTOR": "redbullMOTOR", "redbullracing": "redbullracing",
        "RedBullTurkiye": "RedBullTurkiye", "RedBull_AZ": "RedBull_AZ", "RizesporAS": "RizesporAS",
        "rolandgarros": "rolandgarros", "Samsunspor": "Samsunspor", "sauberf1team": "sauberf1team",
        "SaudiProLeague": "SaudiProLeague", "ScuderiaFerrari": "ScuderiaFerrari", "SECNetwork": "SECNetwork",
        "SerieA": "Lega Serie A", "SerieA_EN": "SerieA_EN", "Sivasspor": "Sivasspor",
        "SkySport": "skysport", "SkySportsNews": "SkySportsNews", "SkySportsPL": "Sky Sports Premier League",
        "SLBenfica": "SL Benfica", "SPFL": "SPFL", "sport": "Diario SPORT",
        "Sport24_ru": "Sport24_ru", "sportbible": "SPORTbible", "SportingCP": "Sporting CP",
        "SPORTSbible": "SPORTSbible", "SportsCenter": "SportsCenter", "Sportsnet": "Sportsnet",
        "sportsru": "sportsru", "SportTV": "SportTV", "sporx": "sporx",
        "spurs": "San Antonio Spurs", "SpursOfficial": "Tottenham Hotspur", "sscnapoli": "Official SSC Napoli",
        "StephenCurry30": "StephenCurry30", "Suns": "Suns", "SuperFormula": "SuperFormula",
        "SuperLig": "Trendyol Süper Lig", "surfline": "surfline", "TBLStats": "TBLStats",
        "TFFStore": "TFFStore", "theathletic": "The Athletic", "TNTSportsBR": "TNT Sports BR",
        "Trabzonspor_EN": "Trabzonspor_EN", "TSN_Sports": "TSN", "TSTV1967": "TSTV1967",
        "TurkishVolley": "TurkishVolley", "TwitchSupport": "Twitch Support", "UCI_BMX": "UCI_BMX",
        "UCI_cycling": "UCI", "UCI_MTB": "UCI_MTB", "UEFA": "UEFA",
        "UEFAcom_tr": "UEFAcomtr", "usopen": "usopen", "VakifBankSK": "VakıfBank Spor Kulübü",
        "VCARB_F1": "VCARB_F1", "vinijr": "vinijr", "volleyballworld": "Volleyball World",
        "warriors": "warriors", "WestHam": "West Ham United", "WilliamsRacing": "Atlassian Williams F1 Team",
        "Wimbledon": "Wimbledon", "WNBA": "WNBA", "Wolves": "Wolves",
        "WorldAquatics": "WorldAquatics", "WorldAthletics": "WorldAthletics", "worldgymnastics": "worldgymnastics",
        "WorldRugby": "WorldRugby", "WorldSBK": "WorldSBK", "WSL": "WSL",
        "WTA": "wta", "YahooSports": "Yahoo Sports", "yamahamotogp": "yamahamotogp",
    },
}
VIDEOLENT_HESABLAR = {h: ad for q in VIDEOLENT_QRUPLAR.values() for h, ad in q.items()}
# Çıxarılmış Videolent hesabları: yeni videosu götürülmür, növbədə qalan sətirləri lentə çıxmır (reels, keep_reels). Adı cədvəldə qalır
# ki, növbə faylındakı köhnə sətirlər yoxlamadan keçsin; REELS_DAYS-dan sonra buradan da silmək olar.
CIXAN = {"CrazyClips_": "Crazy Clips"}   # 2026-11-20–22: öz videolarında kazino (Roobet) reklamı — mərc və qumar qadağandır
_CIXAN = {h.lower() for h in CIXAN}
ADLAR = {**HESABLAR, **VIDEOLENT_HESABLAR, **CIXAN}
_REEL_HANDLE = {h.lower(): h for h in ADLAR}
# Xəbər hesablarının mövzusu (idman olmayanlar); qalanı idmandır.
_XEBER_MOVZU = {"TUBITAK": "elm", "wonderofscience": "elm", "Rainmaker1973": "maraqli", "buitengebieden": "tebiet",
                "Yoda4ever": "tebiet", "IGN": "oyun", "GameSpot": "oyun", "Discovery": "tebiet", "TansuYegen": "maraqli",
                "TamirveTadilat": "yemek", "avionot": "texnika", "anadoluajansi": "xeber", "trthaber": "xeber", "dhainternet": "xeber",
                "ihacomtr": "xeber", "euronews_tr": "xeber", "clashreport": "xeber", "ConflictTR": "xeber", "gusholderhaber": "xeber",
                "Pars_Pluss": "xeber", "Derinkuvvet": "xeber", "gdhdijital": "xeber", "ozetgechaber": "xeber", "VoiceOfLevant": "xeber"}
_MOVZU = {h: m for m, q in VIDEOLENT_QRUPLAR.items() for h in q}
# Birinci dərəcəli maraqlı hadisə videoları (sahib 2026-11-20: «1-ci dərəcədə maraqlı hadisələr olan videoları olan mənbələr tap, onlara
# üstünlük ver»). FxTwitter ölçüsü, 2026-11-20: son 3 gündə tez-tez video, video başına median 15–200 min baxış (heyrətamiz anlar,
# rekordlar, ixtiralar, heyvanlar, kadr arxası). Yazıcı bu hesabları hər işdə yoxlayır (x_yazici.videolent_slice), seçimdə öz mövzusunun
# başında durur; lent görülməmiş videolar arasında hər mövzuda onları əvvəl göstərir (reels «p»). Mövzu bölgüsü dəyişmir.
VIDEOLENT_ONDE = ("TheFigen_", "TansuYegen", "historyinmemes", "HowThingsWork_", "engineers_feed", "sciencegirl",
                  "buitengebieden", "nocontextfooty", "wonderofscience", "Yoda4ever", "NoContextHumans", "9GAG", "Rainmaker1973",
                  "GWR", "redbull", "VidsThatGoHard", "InternetH0F", "CollinRugg", "FoxNews", "Breaking911", "ufc",
                  "pusholder", "bpthaber", "sentdefender",   # 2026-11-23: hadisə anı, median 150–175 min baxış
                  "TMZ", "SawyerMerritt")   # 2026-11-26: median 223 və 200 min baxış, 72 saatda 8 və 7 video
# VIDEOLENT_ONDE hər işdə yoxlanır və x_yazici.VL_PER_RUN-dan yer tutur: 2026-11-26-da 25 hesab (USTA_HESABLAR ilə) — mövzu başına
# 5 hesab qalır; daha 1 hesab əlavə olunsa 4-ə düşür (bütün mövzular yavaş dövr edir). Ona görə öndə yalnız ən güclü iki hesab.
_ONDE = {h.lower() for h in VIDEOLENT_ONDE}


def onde(handle):
    """Hesab birinci dərəcəli (VIDEOLENT_ONDE) mənbədirmi."""
    return str(handle or "").lower() in _ONDE


# Lentin iki sinfi (sahib 2026-11-22): «h» — təzə və maraqlı hadisələr, yeniliklər, xəbər, kadr arxası, sürətli yemək və s. (60%);
# «u» — «Tamir & Tadilat» kimi bir işin necə görüldüyünü göstərən videolar, çox fərqli sahələrdə (40%). Sinfi hər video üçün Gemini
# verir (x_yazici.pick_reels); verilməyibsə (köhnə sətir, açarsız iş) hesabın əsas sinfi: aşağıdakılar «u», qalanı «h».
USTA_PAY = 0.4
# 2026-11-23 (FxTwitter, 72 saat): əvvəlki 11 hesabdan 7 gündə yalnız TamirveTadilat və HowThingsWork_ video vermişdi — DIYcrafts və
# 5MinuteCrafts yoxdur (404), TroomTroom 2017-dən yazmır, Homestead başqasının boş hesabıdır, Woodworking reklama keçib (çıxarıldı);
# engineers_feed, HGTV, instructables demək olar video vermir. Yeni: Brand_Anuj (25 video), pratikdunya (22), muhendisIiktr (21).
# Bu hesablar hər işdə yoxlanır (x_yazici.videolent_slice): usta işinin mənbəyi azdır.
USTA_HESABLAR = {"TamirveTadilat", "HowThingsWork_", "ThisOldHouse", "Brand_Anuj", "pratikdunya", "muhendisIiktr"}
_USTA = {h.lower() for h in USTA_HESABLAR}


def sinif(row):
    """Videonun sinfi: «u» (usta işi) və ya «h» (hadisə). Sətirdəki «sinif», yoxdursa hesabın əsas sinfi."""
    s = row.get("sinif") if isinstance(row, dict) else None
    if s in ("h", "u"):
        return s
    return "u" if str((row or {}).get("handle") or "").lower() in _USTA else "h"


# Gemini-siz qaydalar (sahib 2026-11-23: «Geminidən başqa daha dayanıqlı bir yol tap pulsuz. … Alınmırsa izah lazım deyil. 20-80 yaş
# arası ən çox baxılan videolar olsun»). Seçim X-in öz saylarına (baxış, bəyənmə, paylaşma) və bu süzgəclərə əsaslanır; Gemini
# işləyəndə yalnız izah və sinif əlavə edir.
# Usta işi mətndən: bir işin necə görüldüyünü deyən sözlər (ingilis, türk, rus).
_USTA_TEXT = re.compile(r"how (?:it'?s|they'?re|it is|are) made|how to (?:make|build|fix|repair)|restor(?:e|ed|ing|ation)|\brepair(?:ing|ed)?\b|"
                        r"\bfactory\b|manufactur|production line|craftsm|handmade|woodwork|blacksmith|welding|\bforg(?:e|ing)\b|carpent|"
                        r"\bdiy\b|nasıl yapılır|nasıl üretilir|yapımı|üretim|restorasyon|onarım|\btamir|usta(?:lık)?\b|fabrika|el yapımı|"
                        r"как делают|производств|реставрац|ремонт", re.I)
# Lentə düşməyən mətn (Gemini-siz də): mərc və qumar, açıq-saçıq, ağır kadr xəbərdarlığı, edam, uşaq istismarı və zorlama. X-in
# öz «possibly_sensitive» nişanı və icma qeydi (community note) x_yazici.candidate-də ayrıca yoxlanır, amma 2026-11-23 ölçüsündə
# nişan 10 486 paylaşımın yalnız birində idi — ağır kadrı mətn tutur (BPT belə videoları «HASSAS» yazır).
_UNSAFE_TEXT = re.compile(r"casino|kazino|roobet|rainbet|stake\.com|1xbet|polymarket|betting|sportsbook|\bbahis|iddaa|kumar|jackpot|"
                          r"onlyfans|\bnsfw\b|porn|\bxxx\b|\+18\b|\b18\+|\bgraphic\b|disturbing|viewer discretion|sensitive content|"
                          r"\bhassas\b|rahatsız edici|\bgore\b|behead|dead bod|corpse|ceset|infaz|\bexecution of\b|kafa kes|"
                          r"child abuse|molest|\brape[ds]?\b|istismar|taciz|tecavüz|казино|ставк|порн", re.I)


def usta_text(text):
    """Mətn bir işin necə görüldüyündən danışırmı (Gemini-siz sinif)."""
    return bool(_USTA_TEXT.search(str(text or "")))


def unsafe_text(text):
    """Mətndə lentə düşməyən mövzu (mərc, açıq-saçıq, ağır kadr) varmı."""
    return bool(_UNSAFE_TEXT.search(str(text or "")))


# Ən çox baxılan (sahib 2026-11-23): yaşına görə həddən az baxılan hadisə videosu «boş» sayılır və lentə düşmür. Ölçü (FxTwitter,
# 2026-11-23, 118 hesab, 3 705 video): baxış yaşla artır — median 3 saatdan təzədə 8 min, 3–12 saatda 15 min, 12 saatdan sonra
# ~45 min (son sayın ~90%-i). Hədd hər yaşda medianın təxminən özüdür: hadisə videolarının yuxarı yarısı. Paylaşım 24 saat
# namizəddir (x_yazici.REEL_WINDOW) və sayı yenilənir: təzə video sonra həddi keçə bilər. Usta işi az baxılır (TamirveTadilat
# median 6,7 min) — sahibin özü nümunə göstərdiyi videolardır, həddi aşağıdır. Lentin başına ən çox baxılanı sıralama gətirir.
REEL_MIN_VIEWS = {"u": 3000, "h": ((3, 8000), (12, 15000), (None, 40000))}   # h: (saatadək, baxış)


def min_views(row):
    """Sinfin və sayın ölçüldüyü yaşın həddi (vt yoxdursa video köhnə sayılır)."""
    if sinif(row) == "u":
        return REEL_MIN_VIEWS["u"]
    at, vt = _at(row.get("at")), _at(row.get("vt"))
    hours = (vt - at).total_seconds() / 3600 if at and vt else 24
    return next(n for limit, n in REEL_MIN_VIEWS["h"] if limit is None or hours < limit)


def empty(row):
    """Baxış sayı bilinir və həddən azdır: «boş» video."""
    return "v" in row and row["v"] < min_views(row)


_COUNT = ("v", "l", "rp")   # sətirdə: baxış, bəyənmə, paylaşma (vt — sayların vaxtı)


def popularity(row):
    """Populyarlıq: baxış + bəyənmə və paylaşmanın çəkisi (bəyənən və paylaşan baxandan çox maraqlanıb). Say yoxdursa 0."""
    return int(row.get("v") or 0) + 20 * int(row.get("l") or 0) + 60 * int(row.get("rp") or 0)


# Videonun izahı (sahib 2026-11-22: «mənası başa düşülməyən videolar olmasın»): Azərbaycan dilində bir qısa cümlə, lentdə hesabın
# adının altında. Gemini paylaşımın mətnindən yazır; yoxlamadan keçməyən izahlı video lentə düşmür.
IZAH_LEN = (10, 120)
_ARMENIA = re.compile(r"armeni|ermeni|erməni|армян|армени|pashinyan|paşinyan|пашинян|yerevan|ереван|irəvan", re.I)


def forbidden_topic(text):
    """Qısa videoda olmayan mövzu: Azərbaycan və rəhbərliyi (qırmızı xətt 2) və ya Ermənistan."""
    return about_azerbaijan(text) or bool(_ARMENIA.search(text))


def izah_check(c):
    """İzah yararsızdırsa səbəbi, yoxsa None."""
    if not isinstance(c, str) or not IZAH_LEN[0] <= len(c) <= IZAH_LEN[1]:
        return f"izah {IZAH_LEN[0]}–{IZAH_LEN[1]} simvol olmalıdır"
    if re.search(r"https?:|www\.|[@#<>]", c):
        return "izahda keçid, @ və ya # olmaz"
    if forbidden_topic(c):
        return "izahda Azərbaycan və ya Ermənistan mövzusu"
    return None


def movzu(handle):
    """Hesabın mövzusu (VIDEOLENT_QRUPLAR açarı; xəbər hesablarında _XEBER_MOVZU, yoxdursa «idman»)."""
    h = _REEL_HANDLE.get(str(handle or "").lower(), "")
    return _MOVZU.get(h) or _XEBER_MOVZU.get(h) or "idman"

_ID = re.compile(r"[1-9]\d{5,24}")
_POST = re.compile(r"https://x\.com/([A-Za-z0-9_]{1,15})/status/(\d+)")
_SLOT = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


def _line(s):
    return " ".join(str(s or "").split())


def _url_ok(url, host, suffix=""):
    """Yalnız verilən host, https, ASCII, boşluqsuz, sorğu hissəsi sadə."""
    text = str(url or "")
    if not text.isascii() or any(c in text for c in ' "\'<>\\`') or not content_policy.safe_url(text):
        return False
    try:
        parts = urllib.parse.urlsplit(text)
    except ValueError:
        return False
    return parts.scheme == "https" and parts.hostname == host and not parts.port and parts.path.lower().endswith(suffix) and not parts.fragment


def _size(v):
    return isinstance(v, int) and not isinstance(v, bool) and SIZE[0] <= v <= SIZE[1]


def about_azerbaijan(text):
    return bool(content_policy.AZ_TERMS.search(text) or content_policy.LEADER_TERMS.search(text))


def check(row):
    """Sətir dərc oluna bilməzsə səbəbi, yoxsa None."""
    if not isinstance(row, dict):
        return "sətir lüğət deyil"
    ident = row.get("id")
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        return "id yararsızdır (paylaşımın nömrəsi)"
    if dn.window(row) is None:
        return "date / until yararsızdır"
    slot = str(row.get("slot") or "")
    if not _SLOT.fullmatch(slot) or not SLOT_FROM <= slot <= SLOT_TO:
        return "slot yararsızdır (07:00–23:59)"
    if row.get("kind") not in NOVLER:
        return "növ cədvəldə yoxdur"
    handle = _HANDLE.get(str(row.get("handle") or "").lower())
    if not handle:
        return "hesab cədvəldə yoxdur"
    m = _POST.fullmatch(str(row.get("post") or ""))
    if not m or m.group(1).lower() != handle.lower() or m.group(2) != ident:
        return "post ünvanı https://x.com/<hesab>/status/<id> olmalıdır"
    transfer = row.get("kind") == "x-transfer"   # videosuz ola bilər; şəkil varsa yenə pbs.twimg.com
    if (not transfer or row.get("video")) and not _url_ok(row.get("video"), "video.twimg.com", ".mp4"):
        return "video ünvanı video.twimg.com-da mp4 olmalıdır"
    if (not transfer or row.get("poster")) and not _url_ok(row.get("poster"), "pbs.twimg.com"):
        return "poster ünvanı pbs.twimg.com-da olmalıdır"
    if (not transfer or row.get("video")) and not (_size(row.get("w")) and _size(row.get("h"))):
        return f"w və h {SIZE[0]}–{SIZE[1]} arası tam ədəd olmalıdır"
    title, lead, body = _line(row.get("title")), _line(row.get("lead")), dn._body(row)
    if transfer and "transfer" not in title.lower():
        return "transfer xəbərinin başlığında «transfer» sözü olmalıdır (Transfer bölməsi onu belə tanıyır)"
    if not dn.TITLE_LEN[0] <= len(title) <= dn.TITLE_LEN[1]:
        return f"başlığın uzunluğu {dn.TITLE_LEN[0]}–{dn.TITLE_LEN[1]} hərf olmalıdır"
    if title[-1] in ".?!…":
        return "başlıq nöqtə və ya sual ilə bitir"
    if not dn.LEAD_LEN[0] <= len(lead) <= dn.LEAD_LEN[1]:
        return f"girişin uzunluğu {dn.LEAD_LEN[0]}–{dn.LEAD_LEN[1]} hərf olmalıdır"
    if not 1 <= len(body) <= BODY_MAX or len(body) != len(row.get("body") or []):
        return f"mətn 1–{BODY_MAX} dolu abzas olmalıdır"
    if any(not dn.PARA_LEN[0] <= len(p) <= dn.PARA_LEN[1] for p in body):
        return f"abzasın uzunluğu {dn.PARA_LEN[0]}–{dn.PARA_LEN[1]} hərf olmalıdır"
    text = "\n".join([title, lead, *body])
    if dn._KIRIL.search(text):
        return "kiril hərfi var"
    if "!" in text or "http" in text.lower() or "www." in text.lower():
        return "nida işarəsi və ya keçid var"
    found = dn._NISBI.search(text)
    if found:
        return f"nisbi gün sözü var: «{found.group(0)}»"
    src = row.get("src")
    if not isinstance(src, list) or not 1 <= len(src) <= SRC_MAX or any(
            not isinstance(s, str) or not SRC_LEN[0] <= len(_line(s)) <= SRC_LEN[1] for s in src):
        return f"src: 1–{SRC_MAX} çıxarış, hər biri {SRC_LEN[0]}–{SRC_LEN[1]} hərf"
    corpus = "\n".join(src)
    if about_azerbaijan(text) or about_azerbaijan(corpus):
        return "xarici mənbə, Azərbaycan mövzusu"
    missing = sorted(ox._nums(text) - ox._nums(corpus) - dn.en_nums(corpus))
    if missing:
        return "mətndəki rəqəm mənbə mətnində yoxdur: " + ", ".join(missing)
    try:
        if ox.needs_owner(text):
            return "rəhbərliyin adı keçir: bu növbə ilə verilmir"
    except Exception as e:  # süzgəc işləmirsə xəbər getmir
        return f"rəhbərlik süzgəci xətası: {type(e).__name__}"
    return None


def load(path=None):
    """Növbə faylının sətirləri. Fayl yoxdursa və ya pozulubsa boş siyahı."""
    try:
        doc = json.loads(pathlib.Path(path or NOVBE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = doc.get("items") if isinstance(doc, dict) and doc.get("v") == 1 else None
    return rows if isinstance(rows, list) else []


def rows(path=None):
    """[(sətir, səbəb və ya None)]: id-si olan sətirlər, fayldakı sıra ilə. Təkrar id-nin ikinci sətri rədd edilir."""
    out, seen = [], set()
    for row in load(path):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not _ID.fullmatch(row["id"]):
            continue
        why = check(row)
        if row["id"] in seen:
            why = TEKRAR
        seen.add(row["id"])
        out.append((row, why))
    return out


# --- Qısa videolar ---------------------------------------------------------------------------------------------------
# Sahib, 2026-11-19: «tiktok stilini düzəlt. videoların bəzilərinə yazı tərcümə ehtiyac olmaya bilər… gündə 40».
# Növbə faylının "reels" siyahısı: yazısız videolar (mətn yazılmır, tərcümə yoxdur). Yazıcı (x_yazici.py) doldurur,
# yeniləyici (updater.update_reels) reels() ilə data/reels.json-a yazır, sayt yalnız «Qısa videolar» açılanda oxuyur.
# Sətir: id, handle, post, video, poster, w, h (xəbər sətri ilə eyni qaydalar), at (paylaşımın vaxtı, ISO UTC),
# src (orijinal mətn: yalnız Azərbaycan süzgəci üçün, sayta çıxmır).
REELS_DAYS = 7    # sahib, 2026-11-19: «günə 100 yeni video et» — lentdə ən təzə 200 video (~2 gün), ən çox 7 günlük
REELS_MAX = 1000  # sahib 2026-11-22: «video sayı 1000 olsun» (2026-11-20: «çox sayda olmasıdır») — gündə 300–800 gəlir, lent ~2 günü tutur
REELS_KEEP = REELS_MAX + REELS_MAX // 5   # növbə faylı (keep_reels): sayt süzgəcindən (köhnə klip, eyni video) sonra da REELS_MAX qalsın


def _at(value):
    try:
        at = datetime.datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return at if at.tzinfo else None


def reel_check(row):
    """Qısa video sətri göstərilə bilməzsə səbəbi, yoxsa None (qırmızı xətt 2: Azərbaycan mövzusu düşür)."""
    if not isinstance(row, dict):
        return "sətir lüğət deyil"
    ident = row.get("id")
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        return "id yararsızdır (paylaşımın nömrəsi)"
    handle = _REEL_HANDLE.get(str(row.get("handle") or "").lower())
    if not handle:
        return "hesab cədvəldə yoxdur"
    m = _POST.fullmatch(str(row.get("post") or ""))
    if not m or m.group(1).lower() != handle.lower() or m.group(2) != ident:
        return "post ünvanı https://x.com/<hesab>/status/<id> olmalıdır"
    if not _url_ok(row.get("video"), "video.twimg.com", ".mp4"):
        return "video ünvanı video.twimg.com-da mp4 olmalıdır"
    if not _url_ok(row.get("poster"), "pbs.twimg.com"):
        return "poster ünvanı pbs.twimg.com-da olmalıdır"
    if not (_size(row.get("w")) and _size(row.get("h"))):
        return f"w və h {SIZE[0]}–{SIZE[1]} arası tam ədəd olmalıdır"
    if _at(row.get("at")) is None:
        return "at: paylaşımın vaxtı (ISO, saat qurşağı ilə)"
    src = row.get("src")
    if not isinstance(src, list) or not 1 <= len(src) <= SRC_MAX or any(not isinstance(s, str) or len(s) > SRC_LEN[1] for s in src):
        return f"src: 1–{SRC_MAX} çıxarış"
    if about_azerbaijan("\n".join(src)):
        return "xarici mənbə, Azərbaycan mövzusu"
    if _ARMENIA.search("\n".join(src)):
        return "xarici mənbə, Ermənistan mövzusu"
    if "sinif" in row and row["sinif"] not in ("h", "u"):
        return "sinif «h» və ya «u» olmalıdır"
    for k in ("c", "ru", "en"):   # azərbaycanca izah və oxucunun dilində (rus, ingilis) izah: eyni qayda
        if k in row and izah_check(row[k]):
            return f"{k}: {izah_check(row[k])}" if k != "c" else izah_check(row[k])
    for k in _COUNT:
        if k in row and (type(row[k]) is not int or row[k] < 0):
            return f"{k}: mənfi olmayan tam ədəd (X-in sayı)"
    if "vt" in row and _at(row["vt"]) is None:
        return "vt: sayların vaxtı (ISO, saat qurşağı ilə)"
    return None


def load_reels(path=None):
    try:
        doc = json.loads(pathlib.Path(path or NOVBE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = doc.get("reels") if isinstance(doc, dict) and doc.get("v") == 1 else None
    return rows if isinstance(rows, list) else []


_MEDIA = re.compile(r"/(?:ext_tw_video|amplify_video|tweet_video)/(\d{6,25})/")
_TW_EPOCH_MS = 1288834974657
# Hadisə videosunun özü ən çox bu qədər köhnə ola bilər (sahib 2026-11-22: «həm yeni, həm maraqlı hadisələr»). X media nömrəsi
# yüklənmə vaxtını saxlayır: 2026-11-23 lentində videoların 9%-i illər əvvəlki klipin təzə paylaşımı idi (məs. 2022-07-13). Usta işi
# vaxtdan asılı deyil, ona bu hədd yoxdur.
REEL_VIDEO_DAYS = 3


def video_key(url):
    """Videonun açarı: X media nömrəsi (eyni video başqa paylaşımda, başqa ölçü və ?tag= ilə də bir açardır), yoxdursa sorğusuz ünvan.
    lent.js vkey ilə eynidir: izlənmiş video başqa ünvanla «təzə» kimi qayıtmır."""
    m = _MEDIA.search(str(url or ""))
    return m.group(1) if m else str(url or "").split("?")[0]


def video_at(url):
    """X videosunun yüklənmə vaxtı (media nömrəsi snowflake-dir) və ya None."""
    m = _MEDIA.search(str(url or ""))
    if not m:
        return None
    return datetime.datetime.fromtimestamp(((int(m.group(1)) >> 22) + _TW_EPOCH_MS) / 1000, datetime.timezone.utc)


def stale_event(row, now):
    """Hadisə videosunun özü REEL_VIDEO_DAYS-dan köhnədirsə (köhnə klipin təzə paylaşımı) True."""
    va = video_at(row.get("video"))
    return sinif(row) == "h" and va is not None and va < now - datetime.timedelta(days=REEL_VIDEO_DAYS)


def balance(rows, n=REELS_MAX, cls=lambda r: r["q"]):
    """Ən çox n sətir (ən yenisi əvvəl verilir): usta işi USTA_PAY qədəri, qalanı hadisə; bir sinif çatmasa yer o birindən dolur
    (sahib 2026-11-22: 60% hadisə, 40% usta işi). Usta işinin mənbəyi azdır: o, REELS_DAYS boyu saxlanır, hadisə isə ən təzəsi."""
    u = [r for r in rows if cls(r) == "u"]
    h = [r for r in rows if cls(r) != "u"]
    keep_h = h[:n - min(len(u), round(n * USTA_PAY))]
    keep = {id(r) for r in keep_h + u[:n - len(keep_h)]}
    return [r for r in rows if id(r) in keep]


def reels(now, path=None):
    """Saytın qısa video lenti: yoxlamadan keçən, son REELS_DAYS günün videoları, ən yenisi əvvəl. Paylaşımın mətni (src) çıxmır.
    Sətir: id, a (hesab), n (hesabın adı), u (mp4), i (poster), w, h, t (vaxt), q (sinif: h/u); v — baxış sayı (lent.js ən çox
    baxılanı önə qoyur); c — Azərbaycan dilində izah (varsa), ru/en — rus və ingilis oxucusu üçün izah (varsa); p: 1 — birinci dərəcəli mənbə (VIDEOLENT_ONDE). Eyni video (media
    nömrəsi) bir dəfə; köhnə klipin təzə paylaşımı hadisə deyil; REEL_MIN_VIEWS-dan az baxılan video yoxdur; usta işi USTA_PAY qədər."""
    floor, out, seen = now - datetime.timedelta(days=REELS_DAYS), [], set()
    rows = [r for r in load_reels(path) if not reel_check(r) and floor <= _at(r["at"]) <= now + datetime.timedelta(hours=1)]
    for row in sorted(rows, key=lambda r: _at(r["at"]), reverse=True):
        # İzah məcburi deyil (sahib 2026-11-23: «Alınmırsa izah lazım deyil»). Baxış sayı bilinən və REEL_MIN_VIEWS-dan az olan video
        # «boş»dur; sayı hələ bilinməyən köhnə sətir qalır, lent onu ən sona qoyur (yazıcı sayları yeniləyir).
        key = video_key(row["video"])
        if stale_event(row, now) or empty(row) or row["id"] in seen or key in seen or row["handle"].lower() in _CIXAN:
            continue
        seen.update((row["id"], key))
        h = _REEL_HANDLE[row["handle"].lower()]
        out.append({"id": row["id"], "a": h, "n": ADLAR[h], "m": movzu(h), "u": row["video"], "i": row["poster"],
                    "w": row["w"], "h": row["h"], "t": _at(row["at"]).astimezone(datetime.timezone.utc).isoformat(timespec="seconds"),
                    "q": sinif(row), **({"v": row["v"]} if "v" in row else {}), **({"p": 1} if onde(h) else {}),
                    **{k: row[k] for k in ("c", "ru", "en") if row.get(k)}})
    return balance(out)


def keep_reels(rows, now):
    """Növbə faylında saxlanan qısa video sətirləri (x_yazici): son REELS_DAYS günün videoları, ən çox REELS_KEEP. Sıra qorunur.
    Çox olanda əvvəl ən köhnə hadisə videoları düşür, usta işi (REELS_KEEP × USTA_PAY) bütün həftə qalır — əvvəl fayl son 1000
    sətri saxlayırdı və usta işi 2 gündən sonra silinirdi (2026-11-23 lentində 11%). Çıxarılmış hesabın (CIXAN) sətri silinir."""
    floor = now - datetime.timedelta(days=REELS_DAYS)
    ok = [r for r in rows if isinstance(r, dict) and (_at(r.get("at")) or floor) > floor
          and str(r.get("handle") or "").lower() not in _CIXAN]
    newest = sorted(ok, key=lambda r: _at(r.get("at")), reverse=True)
    keep = {id(r) for r in balance(newest, REELS_KEEP, sinif)}
    return [r for r in ok if id(r) in keep]



def credit(handle):
    h = _HANDLE[str(handle).lower()]
    return f"{HESABLAR[h]} (X, @{h})"


def item(row, day):
    """Yoxlamadan keçmiş sətirdən dərc hissəsinin xəbəri (bu günün tarixi ilə)."""
    return {"kind": row["kind"], "key": KEY + row["id"], "title": _line(row["title"]), "lead": _line(row["lead"]),
            "body": dn._body(row), "credit": credit(row["handle"]), "link": row["post"],
            "image": row.get("poster") or "", "video": row.get("video") or "", "vw": str(row.get("w") or ""), "vh": str(row.get("h") or ""),
            "topic": NOVLER[row["kind"]], "slot": row["slot"], "date": day.isoformat(), "worth": True}


def items(root, now, fetch=None, done=None, path=None):
    """Bu günün növbədəki xəbərləri. Sorğu yoxdur; root, fetch istifadə olunmur (imza başqa modullarla eynidir)."""
    now = now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)
    today, done, out = now.date(), set(done or ()), []
    for row, why in rows(path):
        key = KEY + row["id"]
        span = dn.window(row)
        if key in done or why == TEKRAR or span is None or not span[0] <= today <= span[1]:
            continue
        if why:
            out.append(ox._no(str(row.get("kind") or "x-maraqli"), key, _line(row.get("title")) or row["id"], why,
                              _line(row.get("handle")), str(row.get("post") or ""), "video", str(row.get("slot") or "12:00")))
        else:
            out.append(item(row, today))
    return sorted(out, key=lambda x: (x["slot"], x["key"]))


def sinaq(root, now=None, fetch=None, path=None):
    """Nümunələr (Markdown): bu günün xəbərləri və növbə faylının bütün sətirləri. Sorğu yoxdur."""
    now = now or datetime.datetime.now(BAKU)
    now = now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)
    today = now.date()
    md = ["## X-dən videolu xəbərlər: sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Növbə faylı oxunur, sorğu yoxdur; sayta heç nə yazılmır.", "",
          f"### Bu gün, {ox.day_text(today)}", ""]
    todays = items(root, now, path=path)
    for it in todays:
        if it.get("worth"):
            md += ox.render(it) + [f"> Növ: {it['kind']}, video: {it['video']}, slot: {it['slot']}.", ""]
        else:
            md += [f"> **Dərc olunmur** ({it['key']}): {it['why']}", ""]
    if not todays:
        md += [f"> {ox.day_text(today)} üçün növbədə xəbər yoxdur.", ""]
    md += ["### Növbə faylı", "", "| id | günlər | slot | hesab | vəziyyət |", "|---|---|---|---|---|"]
    all_rows = rows(path)
    for row, why in all_rows:
        span = dn.window(row)
        days = f"{span[0]:%d.%m}–{span[1]:%d.%m}" if span else "?"
        state = why or ("keçib" if span and span[1] < today else "növbədə")
        md.append(f"| {row['id']} | {days} | {row.get('slot', '')} | {row.get('handle', '')} | {state} |")
    if not all_rows:
        md.append("| (boşdur) | | | | |")
    return md + [""]


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(dn._arg(argv, "--root") or pathlib.Path(__file__).parent)
    now = dn._arg(argv, "--now")
    now = datetime.datetime.fromisoformat(now) if now else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
