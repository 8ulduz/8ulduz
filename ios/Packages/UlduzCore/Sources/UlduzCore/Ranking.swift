import Foundation

/// Ana səhifənin seçimləri (app.js `heroPick`, `prezHome`, `rankBySources`, axtarış, yol xəbərləri).
public enum Ranking {
    private static let hour: TimeInterval = 3600
    private static let day: TimeInterval = 24 * 3600
    private static let appointment = Rx("təyin (?:edil|olun)|vəzifə(?:sin|y)[əd]|(?:vəzifə(?:sin)?|iş)d[əa]n azad|назначен|освобожд[её]н от должности|appointed|dismissed", caseInsensitive: true)
    private static let wordSplit = Rx("[^\\p{L}\\p{N}]+")

    public static func byDate(_ list: [Article]) -> [Article] {
        list.sorted { ($0.date ?? .distantPast) > ($1.date ?? .distantPast) }
    }

    public static func filtered(_ list: [Article], language: String?) -> [Article] {
        guard let language, !language.isEmpty else { return list }
        return list.filter { $0.language == language }
    }

    private static func isAppointment(_ a: Article) -> Bool { appointment.test(a.title) }

    public static func rankBySources(_ list: [Article]) -> [Article] {
        let scored: [(article: Article, n: Int)] = list.map { ($0, $0.sourceCount + (isAppointment($0) ? 2 : 0)) }
        return scored.sorted { $0.n != $1.n ? $0.n > $1.n : $0.article.publishedAt > $1.article.publishedAt }.map(\.article)
    }

    private static func heroWords(_ a: Article) -> Set<String> {
        let spaced = wordSplit.replace(TextTools.azLowercased(a.title), with: " ")
        return Set(spaced.split(separator: " ").map(String.init).filter { $0.count >= 5 })
    }

    static func diverse(_ ranked: [Article], need: Int) -> [Article] {
        var out: [Article] = []
        var seen: [Set<String>] = []
        for a in ranked {
            let w = heroWords(a)
            if seen.contains(where: { $0.intersection(w).count >= 2 }) { continue }
            out.append(a)
            seen.append(w)
            if out.count >= need { break }
        }
        for a in ranked where out.count < need && !out.contains(where: { $0.id == a.id }) { out.append(a) }
        return out
    }

    /// Son 18 saatın ən çox mənbədə çıxan xəbərləri; kifayət etməsə 48 saat, sonra bütün lent.
    public static func heroPick(_ list: [Article], need: Int = 6, now: Date = Date()) -> [Article] {
        for hours in [18.0, 48.0] {
            let cut = now.addingTimeInterval(-hours * hour)
            let limit = now.addingTimeInterval(5 * 60)
            let pool = list.filter { a in
                guard let d = a.date else { return false }
                return d >= cut && d <= limit
            }
            if pool.count >= need { return diverse(rankBySources(pool), need: need) }
        }
        return diverse(rankBySources(list), need: need)
    }

    private static let firstLadyTerms = ["mehriban", "məhriban", "мехрибан", "birinci xanım", "birinci xanim", "first lady",
                                         "first vice-president", "first vice president", "birinci vitse-prezident", "первой леди", "первая леди"]

    public static func isFirstLady(_ a: Article) -> Bool {
        let t = TextTools.azLowercased(a.title)
        return firstLadyTerms.contains { t.contains($0) }
    }

    /// Əsas blok: Prezident və Birinci xanım qrupları görünür, sıra ən yenidən köhnəyə (app.js `prezHome`).
    public static func prezHome(_ list: [Article], now: Date = Date()) -> [Article] {
        let official = NewsPipeline.officialSources, state = NewsPipeline.stateSources
        let prez = list.filter { $0.category == "prezident" && (official.contains($0.source) || state.contains($0.source)) }
        func age(_ a: Article) -> TimeInterval { a.date.map { now.timeIntervalSince($0) } ?? .infinity }
        func isLady(_ a: Article) -> Bool { a.source == "Mehriban Əliyeva" || isFirstLady(a) }
        var perSource: [String: Int] = [:]
        func capped(_ l: [Article]) -> [Article] {
            var kept: [Article] = []
            for a in l {
                if official.contains(a.source) { kept.append(a); continue }
                let count = (perSource[a.source] ?? 0) + 1
                perSource[a.source] = count
                if count <= 3 { kept.append(a) }
            }
            return kept
        }
        let president = capped(byDate(prez.filter { !isLady($0) && age($0) < 21 * day }))
        let lady = capped(byDate(prez.filter { isLady($0) && age($0) < 60 * day }))
        let head = 4
        let ladyKeep = lady.isEmpty ? 0 : min(lady.count, 2)
        let presHead = min(president.count, head - ladyKeep)
        let ladyHead = min(lady.count, head - presHead)
        let first = Array(president.prefix(presHead)) + Array(lady.prefix(ladyHead))
        let rest = Array(president.dropFirst(presHead)) + Array(lady.dropFirst(ladyHead))
        return byDate(Array((first + rest).prefix(12)))
    }

    // MARK: - Axtarış

    public static func searchWords(_ query: String) -> [String] {
        let folded = wordSplit.replace(TextTools.fold(query), with: " ")
        return folded.split(separator: " ").map(String.init).filter { $0.count >= 2 || $0.contains(where: \.isNumber) }
    }

    /// Başlıq 3, xülasə və mənbə adı 1 xal; bütün sözlər varsa əlavə 5 xal (app.js `searchView`).
    public static func search(_ query: String, in list: [Article]) -> [Article] {
        let words = searchWords(query)
        guard !words.isEmpty else { return [] }
        var scored: [(article: Article, score: Int)] = []
        for a in list {
            let title = TextTools.fold(TextTools.decodeEntities(a.title))
            let altNames = a.alts.map(\.source).joined(separator: " ")
            let rest = TextTools.fold(TextTools.decodeEntities(a.summary + " " + a.source + " " + altNames))
            var score = 0
            var hits = 0
            for w in words {
                if title.contains(w) { score += 3; hits += 1 }
                else if rest.contains(w) { score += 1; hits += 1 }
            }
            guard hits > 0 else { continue }
            if hits == words.count { score += 5 }
            scored.append((a, score))
        }
        return scored.sorted { $0.score != $1.score ? $0.score > $1.score : $0.article.publishedAt > $1.article.publishedAt }.map(\.article)
    }

    // MARK: - Klublar

    /// app.js `CLUBS` və `CLUB_EXTRA`.
    public static let clubs: [(name: String, terms: [String])] = [
        ("Qarabağ", ["qarabağ", "qarabag", "qarabakh", "карабах"]), ("Sabah", ["sabah fk", "sabah", "сабах"]),
        ("Neftçi", ["neftçi", "neftci", "neftchi", "нефтчи"]), ("Turan", ["turan", "туран"]), ("Zirə", ["zirə", "zire", "зиря"]),
        ("Sumqayıt", ["sumqayıt fk", "sumqayıt", "сумгаит"]), ("Araz", ["araz", "араз"]), ("Şamaxı", ["şamaxı fk", "şamaxı", "шамахы"]),
        ("Galatasaray", ["galatasaray", "галатасарай"]), ("Fenerbahçe", ["fenerbahçe", "fenerbahce", "fenerbaxca", "фенербахче"]),
        ("Beşiktaş", ["beşiktaş", "besiktas", "бешикташ"]), ("Trabzonspor", ["trabzonspor", "трабзонспор"]),
        ("Başakşehir", ["başakşehir", "basaksehir", "башакшехир"]), ("Samsunspor", ["samsunspor", "самсунспор"]),
        ("Man City", ["manchester city", "man city", "манчестер сити"]), ("Man United", ["manchester united", "man united", "манчестер юнайтед"]),
        ("Liverpool", ["liverpool", "ливерпуль"]), ("Arsenal", ["arsenal", "арсенал"]), ("Chelsea", ["chelsea", "çelsi", "челси"]),
        ("Tottenham", ["tottenham", "тоттенхэм"]), ("Newcastle", ["newcastle", "ньюкасл"]), ("Aston Villa", ["aston villa", "астон вилла"]),
        ("Real Madrid", ["real madrid", "реал мадрид"]), ("Barcelona", ["barcelona", "barselona", "барселона"]),
        ("Atletico", ["atletico", "atletiko", "атлетико"]), ("Sevilla", ["sevilla", "севилья"]), ("Villarreal", ["villarreal", "вильярреал"]),
        ("Valencia", ["valencia", "валенсия"]), ("Bayern", ["bayern", "bavariya", "бавария"]), ("Dortmund", ["dortmund", "дортмунд"]),
        ("Leverkusen", ["leverkusen", "леверкузен"]), ("Leipzig", ["leipzig", "лейпциг"]), ("Frankfurt", ["frankfurt", "франкфурт"]),
        ("Juventus", ["juventus", "yuventus", "ювентус"]), ("Milan", ["milan", "милан"]), ("İnter", ["inter", "интер"]),
        ("Napoli", ["napoli", "наполи"]), ("Roma", ["roma", "рома"]), ("Lazio", ["lazio", "лацио"]), ("Atalanta", ["atalanta", "аталанта"]),
        ("PSG", ["psg", "paris saint", "псж", "paris saint germain"]), ("Marseille", ["marseille", "marsel", "марсель"]), ("Lyon", ["lyon", "лион"]),
        ("Monaco", ["monaco", "монако"]), ("Lille", ["lille", "лилль"]), ("Ajax", ["ajax", "аякс"]), ("Porto", ["porto", "порту"]),
        ("Benfica", ["benfica", "бенфика"]), ("Sporting", ["sporting", "спортинг"]), ("Celtic", ["celtic", "селтик"]),
    ]

    // Sözün əvvəli və şəkilçisi nəzərə alınır (Qarabağın / Карабаха), «international» isə İnter sayılmır.
    private static let clubMatchers: [String: Rx] = {
        var out: [String: Rx] = [:]
        for club in clubs {
            let keys = club.terms.map { NSRegularExpression.escapedPattern(for: TextTools.fold($0)) }.joined(separator: "|")
            out[club.name] = Rx("(?:^| )(?:\(keys))(?:in|nin|un|nun|a|e|i|u|dan|den|da|de|s|а|у|е|ом|ы|и)?(?: |$)")
        }
        return out
    }()

    public static func clubMatches(_ a: Article, club: String) -> Bool {
        guard let rx = clubMatchers[club] else { return false }
        return rx.test(" \(TextTools.fold(TextTools.decodeEntities(a.title + " " + a.summary))) ")
    }

    // MARK: - Yollar

    public struct RoadItem: Identifiable, Hashable, Sendable {
        public let article: Article
        public let symbol: String
        public var id: String { article.id }
    }

    private static let roadRules: [(symbol: String, rx: Rx)] = [
        ("exclamationmark.triangle.fill", Rx("qəza(?!lı)", caseInsensitive: true)),
        ("xmark.octagon.fill", Rx("(?:yol|küçə|prospekt|körpü|tunel|şose)\\w{0,6}\\s*bağlan|bağlan\\w{0,8}\\s+(?:yol|küçə|prospekt)|yol bağlı|hərəkət\\w{0,4}\\s+məhdudlaş|(?:yol|küçə|prospekt|körpü|tunel|şose)\\w{0,8}.{0,40}təmir|təmir.{0,32}(?:yol|küçə|prospekt|körpü|tunel|şose)", caseInsensitive: true)),
        ("car.2.fill", Rx("tıxac", caseInsensitive: true)),
        ("tram.fill", Rx("metro|avtobus", caseInsensitive: true)),
        ("cloud.rain.fill", Rx("hava xəbərdar|güclü külək|güclü yağış|şaxta|çovğun|dolu yağ|yağış xəbərdar|(?:^|[^\\p{L}])sel(?:[^\\p{L}]|$)", caseInsensitive: true)),
    ]
    private static let roadFallback = Rx("(?:^|[^\\p{L}])(?:BNA|DYP)(?:[^\\p{L}]|$)|yol polisi|nəqliyyatın hərəkət|avtomobil yol", caseInsensitive: true)
    private static let roadLocal = Rx("bakı|bakinin|bakının|abşeron|abseron|sumqayıt|sumqayit|hey[dər]+ əliyev prospekt|hava limanı yolu", caseInsensitive: true)
    private static let roadUnrelated = Rx("qatar|dəmir yolu|helikopter|təyyarə|başsağlığı|təbrik", caseInsensitive: true)

    private static func roadSymbol(_ title: String) -> String? {
        for rule in roadRules where rule.rx.test(title) { return rule.symbol }
        return roadFallback.test(title) ? "car.fill" : nil
    }

    /// Son 2 saatın Bakı və Abşeron yol xəbərləri (app.js `localRoadItems`).
    public static func localRoadItems(_ list: [Article], now: Date = Date()) -> [RoadItem] {
        byDate(list.filter { $0.language == "az" }).compactMap { a -> RoadItem? in
            guard let d = a.date else { return nil }
            let age = now.timeIntervalSince(d)
            guard age >= 0, age < 2 * hour else { return nil }
            let t = a.cleanTitle
            guard roadLocal.test(t), !roadUnrelated.test(t), let symbol = roadSymbol(t) else { return nil }
            return RoadItem(article: a, symbol: symbol)
        }
    }

    /// İş günü 08–10 və 17–20, Bakı vaxtı.
    public static func bakuRushHour(_ date: Date = Date()) -> Bool {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Baku") ?? .current
        let weekday = cal.component(.weekday, from: date), hour = cal.component(.hour, from: date)
        return (2...6).contains(weekday) && ((8..<10).contains(hour) || (17..<20).contains(hour))
    }
}
