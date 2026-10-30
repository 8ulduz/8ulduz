// QIRMIZI XƏTT 2 (docs/qirmizi-xetler.md): lentə yalnız bu siyahıdakı mənbələr düşür.
// Həm updater.py (content_policy.py), həm brauzer (app.js) bu faylı oxuyur; Dəyər təmiz JSON olmalıdır, şərhlərdə fiqurlu mötərizə işlətməyin.
window.CONTENT_POLICY = {
  "azSources": {
    "AZƏRTAC": ["azertag.az"], "AZƏRTAC (Regionlar)": ["azertag.az"], "APA": ["apa.az"], "APA Sport": ["apasport.az"],
    "Sportinfo": ["sportinfo.az"], "Oxu.az": ["oxu.az"], "Publika.az": ["publika.az"], "Lent.az": ["lent.az"],
    "Axar.az": ["axar.az"], "Olke.az": ["olke.az"], "Yenicag.az": ["yenicag.az"], "AzVision.az": ["azvision.az"],
    "Moderator.az": ["moderator.az"], "Bizim.Media": ["bizim.media"], "Reyting.az": ["reyting.az"],
    "News24.az": ["news24.az"], "Anews.az": ["anews.az"], "Aznews.az": ["aznews.az"], "Zim.az": ["zim.az"],
    "Konkret.az": ["konkret.az"], "525.az": ["525.az"], "İki Sahil": ["ikisahil.az"], "Femida.az": ["femida.az"],
    "Ordu.az": ["ordu.az"], "Azpolitika.info": ["azpolitika.info"], "Marja.az": ["marja.az"], "Banco.az": ["banco.az"],
    "Media.az": ["media.az"], "Report": ["report.az"], "Trend": ["trend.az"], "Trend RU": ["trend.az"],
    "Milli.az": ["milli.az"], "Qafqazinfo": ["qafqazinfo.az"], "Modern.az": ["modern.az"], "Teleqraf": ["teleqraf.az"],
    "Day.Az": ["day.az"], "Azernews": ["azernews.az"], "News.az": ["news.az"], "Vesti.az": ["vesti.az"],
    "İnterPress": ["interpress.az"], "Kulis.az": ["kulis.az"], "Sia.az": ["sia.az", "sestv.az", "sesqazeti.az"],
    "Sesqazeti.az": ["sesqazeti.az"], "Haqqin.az": ["haqqin.az"], "Metbuat": ["metbuat.az"],
    "Tia.az": ["tia.az", "tribuna.az"], "Günün Səsi": ["gununsesi.info"], "Xezerxeber": ["xezerxeber.az"],
    "Minval": ["minval.az"], "Bakupost": ["bakupost.az"], "Banker.az": ["banker.az"], "Cross Media": ["crossmedia.az"],
    "Xalq qəzeti": ["xalqqazeti.az"], "Yeni Azərbaycan": ["yeniazerbaycan.com"], "Azərbaycan qəzeti": ["azerbaijan-news.az"],
    "Baku TV": ["baku.tv"], "Prezident.az": ["president.az"], "Mehriban Əliyeva": ["mehriban-aliyeva.az"]
  },
  "worldSources": {
    "BBC News": ["bbc.co.uk", "bbc.com"], "Al Jazeera": ["aljazeera.com"], "Daily Sabah": ["dailysabah.com"],
    "Euronews": ["euronews.com"], "Hürriyet": ["hurriyet.com.tr"], "Sabah TR": ["sabah.com.tr"], "Habertürk": ["haberturk.com"],
    "Milliyet": ["milliyet.com.tr"], "CNN Türk": ["cnnturk.com"], "TRT Haber": ["trthaber.com"], "Yeni Şafak": ["yenisafak.com"],
    "AA": ["aa.com.tr"], "TRT Spor": ["trthaber.com", "trtspor.com.tr"], "NTV Spor": ["ntvspor.net"], "TASS": ["tass.ru", "tass.com"],
    "Interfax": ["interfax.ru"], "Championat": ["championat.com"], "Sport.ru": ["sport.ru"], "Match TV": ["matchtv.ru"]
  },
  "blockedHosts": ["azadliq.org", "azadliq.info", "meydan.tv", "abzas.org", "abzas.net", "toplum.tv", "mikroskopmedia.com", "turan.az", "musavat.com"],
  "azTerms": "azerbaijan|azerbaycan|azərbaycan|azerbaidjan|aserbaidschan|азербайдж|aliyev|алиев|əliyev|(?<![a-zçəğıöşü])baku(?![a-zçəğıöşü])|bakü|(?<![а-я])баку(?![а-я])|(?<![a-zçəğıöşü])bakı(?:da|dan|nın|ya|nı)?(?![a-zçəğıöşü])|nakhchivan|нахичеван|naxçıvan|nahçıvan|karabakh|karabağ|карабах|qarabağ|stepanakert|степанакерт|khankendi|xankəndi|ханкенди|zangezur|zengezur|зангезур|shusha|şuşa|шуша|gəncə|гянджа|sumgait|sumqayıt|сумгаит|(?<![a-zçəğıöşü])azeri(?![a-zçəğıöşü])|азери|milli məclis|milli mejlis|hajiyev|hacıyev|bayramov|байрамов|socar|сокар",
  "leaderTerms": "aliyev|алиев|əliyev|azerbaijan.{0,12}president|president.{0,12}azerbaijan|президент.{0,12}азербайдж|azerbaycan cumhurbaşkan|azərbaycan prezident|hajiyev|hacıyev|bayramov|байрамов"
};
