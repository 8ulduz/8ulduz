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

    /// Karuseldə 15 kart; ilk 6-sı yalnız orada qalır, qalanları aşağıdakı siyahılarda da görünür (app.js `HERO_COUNT`, `HERO_ONLY`).
    public static let heroCount = 15
    public static let heroOnly = 6

    /// Son 18 saatın ən çox mənbədə çıxan xəbərləri; kifayət etməsə 48 saat, sonra bütün lent.
    public static func heroPick(_ list: [Article], need: Int = heroCount, now: Date = Date()) -> [Article] {
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

    /// Sahibin qərarı: blokda həmişə 44 xəbər (app.js `PREZ_COUNT`).
    public static let prezCount = 44
    // Lentə «prezident» sözü ilə yad xəbər də düşür: digər saytlardan yalnız adı keçən xəbər götürülür.
    private static let ourLeaders = Rx("ilham|i̇lham|əliyev|aliyev|алиев|birinci xan|birinci vitse|prezident\\s+administ|azərbaycan\\s+prezident|dövlət başçı", caseInsensitive: true)
    private static func aboutOurLeaders(_ a: Article) -> Bool { ourLeaders.test(a.title) || ourLeaders.test(a.summary) }

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
        // Rəsmi və dövlət saytları 44-ü doldurmursa: əvvəl həmin saytların qalan xəbərləri, sonra digər saytlar.
        // Yad xəbərlə doldurulmur: belə xəbər çatmasa say 44-dən az olar.
        var chosen = Set((first + rest).map(\.id))
        let ours = byDate(list.filter { $0.category == "prezident" && aboutOurLeaders($0) })
        let fill = (byDate(prez) + ours).filter { chosen.insert($0.id).inserted }
        return byDate(Array((first + rest + fill).prefix(prezCount)))
    }

    // MARK: - Axtarış

    public static func searchWords(_ query: String) -> [String] {
        let folded = wordSplit.replace(TextTools.fold(query), with: " ")
        return folded.split(separator: " ").map(String.init).filter { $0.count >= 2 || $0.contains(where: \.isNumber) }
    }

    /// Başlıq 3, xülasə və mənbə adı 1 xal; bütün sözlər varsa əlavə 5 xal (app.js `searchView`).
    public static func search(_ query: String, in list: [Article], language: String? = nil) -> [Article] {
        let words = searchWords(query)
        guard !words.isEmpty else { return [] }
        let topics = Topics.searchTopics(query)
        var scored: [(article: Article, score: Int)] = []
        for a in list {
            // Komanda axtarışı idman kimi bütün dillərdə, ən yenisi üstdə.
            if !topics.isEmpty {
                let text = TopicText(a)
                if topics.contains(where: { Topics.matches(text, $0) }) {
                    scored.append((a, 20))
                    continue
                }
            }
            if let language, !language.isEmpty, a.language != language { continue }
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

    // MARK: - Bölmə

    /// Bölmə səhifəsinin siyahısı (app.js `sectionView`). Əsas lent və 5 günlük arxiv birlikdə.
    public static func section(_ slug: String, club: String?, articles: [Article], archives: [String: [Article]], language: String?, now: Date = Date()) -> [Article] {
        var list: [Article]
        switch slug {
        case "video": list = articles.filter(\.video)
        case "sondeqiqe": list = articles.filter { $0.isWithinHour(now: now) }
        default: list = NewsPipeline.withArchive(articles.filter { $0.category == slug }, rows: archives[slug] ?? [])
        }
        if slug == "idman" {
            if let club { list = list.filter { Topics.matches($0, club) } }
            return byDate(list)
        }
        if slug == "bolgeler", let club {
            // Yer haqqında xəbər başqa bölmədə də ola bilər. «Qəbələ» və «Sabah» həm də futbol klubudur: rayon düyməsində oyun xəbəri olmasın.
            var pool = articles
            for rows in archives.values { pool = NewsPipeline.withArchive(pool, rows: rows) }
            list = pool.filter { $0.category != "idman" && Topics.matches($0, club, scope: .region) }
        }
        return filtered(byDate(list), language: language)
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
