import Foundation

// Lent xarici mənbədir: bir sətirin zədəli olması bütün faylı sındırmamalıdır.
struct LossyArray<Element: Decodable>: Decodable {
    var values: [Element] = []
    private struct Skip: Decodable {}
    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        while !c.isAtEnd {
            if let v = try? c.decode(Element.self) { values.append(v) }
            else if (try? c.decode(Skip.self)) == nil { break }
        }
    }
}

extension KeyedDecodingContainer {
    func text(_ key: Key) -> String? {
        if let s = try? decodeIfPresent(String.self, forKey: key) { return s }
        if let i = try? decodeIfPresent(Int.self, forKey: key) { return String(i) }
        if let d = try? decodeIfPresent(Double.self, forKey: key) { return String(d) }
        return nil
    }
    func number(_ key: Key) -> Double? {
        if let d = try? decodeIfPresent(Double.self, forKey: key) { return d }
        if let s = try? decodeIfPresent(String.self, forKey: key) { return Double(s) }
        return nil
    }
    func integer(_ key: Key) -> Int? { number(key).flatMap { $0.isFinite ? Int($0) : nil } }
    func flag(_ key: Key) -> Bool { (try? decodeIfPresent(Bool.self, forKey: key)) ?? false }
    func lossy<T: Decodable>(_ key: Key, as: T.Type = T.self) -> [T] {
        (try? decodeIfPresent(LossyArray<T>.self, forKey: key))?.values ?? []
    }
}

/// Eyni xəbəri yazan digər mənbə.
public struct AltSource: Codable, Hashable, Sendable, Identifiable {
    public var source: String
    public var sourceUrl: String
    public var publishedAt: String
    public var imageUrl: String
    public var title: String
    public var lang: String
    public var id: String { sourceUrl }

    public init(source: String, sourceUrl: String, publishedAt: String = "", imageUrl: String = "", title: String = "", lang: String = "") {
        self.source = source; self.sourceUrl = sourceUrl; self.publishedAt = publishedAt
        self.imageUrl = imageUrl; self.title = title; self.lang = lang
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        source = c.text(.source) ?? ""
        sourceUrl = c.text(.sourceUrl) ?? ""
        publishedAt = c.text(.publishedAt) ?? ""
        imageUrl = c.text(.imageUrl) ?? ""
        title = c.text(.title) ?? ""
        lang = c.text(.lang) ?? ""
    }
}

public struct Article: Codable, Identifiable, Hashable, Sendable {
    public var id: String
    public var title: String
    public var summary: String
    public var category: String
    public var source: String
    public var sourceUrl: String
    public var publishedAt: String
    public var imageUrl: String
    public var lang: String
    public var author: String
    public var video: Bool
    public var alts: [AltSource]

    /// Ekrana hazır başlıq və xülasə (bir dəfə hesablanır, hər kartda regex işləmir).
    public private(set) var cleanTitle: String
    public private(set) var cleanSummary: String
    public private(set) var date: Date?

    enum CodingKeys: String, CodingKey {
        case id, title, summary, category, source, sourceUrl, publishedAt, imageUrl, lang, author, video, alts
    }

    public init(id: String, title: String, summary: String = "", category: String = "gundem", source: String, sourceUrl: String,
                publishedAt: String = "", imageUrl: String = "", lang: String = "az", author: String = "", video: Bool = false, alts: [AltSource] = []) {
        self.id = id; self.title = title; self.summary = summary; self.category = category; self.source = source
        self.sourceUrl = sourceUrl; self.publishedAt = publishedAt; self.imageUrl = imageUrl; self.lang = lang
        self.author = author; self.video = video; self.alts = alts
        cleanTitle = TextTools.tidy(title)
        cleanSummary = TextTools.tidy(summary)
        date = ISODate.parse(publishedAt)
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.text(.id), let title = c.text(.title) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "id və title məcburidir"))
        }
        self.init(id: id, title: title, summary: c.text(.summary) ?? "", category: c.text(.category) ?? "gundem",
                  source: c.text(.source) ?? "", sourceUrl: c.text(.sourceUrl) ?? "", publishedAt: c.text(.publishedAt) ?? "",
                  imageUrl: c.text(.imageUrl) ?? "", lang: c.text(.lang) ?? "", author: c.text(.author) ?? "",
                  video: c.flag(.video), alts: c.lossy(.alts))
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id); try c.encode(title, forKey: .title); try c.encode(summary, forKey: .summary)
        try c.encode(category, forKey: .category); try c.encode(source, forKey: .source); try c.encode(sourceUrl, forKey: .sourceUrl)
        try c.encode(publishedAt, forKey: .publishedAt); try c.encode(imageUrl, forKey: .imageUrl); try c.encode(lang, forKey: .lang)
        try c.encode(author, forKey: .author); try c.encode(video, forKey: .video); try c.encode(alts, forKey: .alts)
    }

    /// Lentdə dil yazılmayanda mətndən təyin olunur (app.js `langOf`).
    public var language: String {
        if !lang.isEmpty { return lang }
        let s = title + " " + summary
        if s.range(of: "[а-яА-Я]", options: .regularExpression) != nil { return "ru" }
        if s.range(of: "[əƏ]", options: .regularExpression) != nil { return "az" }
        if s.range(of: "[ığİ]", options: .regularExpression) != nil { return "tr" }
        return "az"
    }

    public var sourceCount: Int { 1 + alts.count }

    /// sesqazeti.az keçidləri Sia.az lentindən gəlir, oxucuya öz adı ilə göstərilir.
    public var shownSource: String {
        TextTools.host(of: sourceUrl) == "sesqazeti.az" ? "Sesqazeti.az" : source
    }

    public var isFresh: Bool { isFresh(now: Date()) }
    public func isFresh(now: Date) -> Bool {
        guard let date else { return false }
        let age = now.timeIntervalSince(date)
        return age >= 0 && age < 15 * 60
    }
    public func isWithinHour(now: Date = Date()) -> Bool {
        guard let date else { return false }
        let age = now.timeIntervalSince(date)
        return age >= 0 && age < 3600
    }

    func withImage(_ url: String) -> Article {
        var copy = self
        copy.imageUrl = url
        return copy
    }
}

public struct NewsFeed: Decodable, Sendable {
    public var updatedAt: String?
    public var articles: [Article]
    enum CodingKeys: String, CodingKey { case updatedAt, articles }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        updatedAt = c.text(.updatedAt)
        guard c.contains(.articles) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "articles yoxdur"))
        }
        articles = c.lossy(.articles)
    }
}

/// og.json: keçid → şəkil. Faylda xidməti sahələr də var (`_meta`), yalnız sətir dəyərlər götürülür.
public struct OgImages: Decodable, Sendable {
    public var images: [String: String] = [:]
    private struct AnyKey: CodingKey {
        var stringValue: String
        var intValue: Int? { nil }
        init?(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { nil }
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AnyKey.self)
        for key in c.allKeys {
            if let url = try? c.decode(String.self, forKey: key) { images[key.stringValue] = url }
        }
    }
}

public struct FeedStatus: Decodable, Sendable, Equatable {
    public var checkedAt: String?
    public var ok: Bool
    public var degraded: Bool
    public var successfulSources: Int?
    public var totalSources: Int?
    enum CodingKeys: String, CodingKey { case checkedAt, ok, degraded, successfulSources, totalSources }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        checkedAt = c.text(.checkedAt)
        ok = c.flag(.ok); degraded = c.flag(.degraded)
        successfulSources = c.integer(.successfulSources); totalSources = c.integer(.totalSources)
    }
}

public struct MarketItem: Decodable, Identifiable, Hashable, Sendable {
    public var id: String
    public var label: String
    public var unit: String
    public var dec: Int
    public var value: Double
    public var change: Double?
    public var changePct: Double?
    public var src: String
    public var asOf: String
    public var stale: Bool

    enum CodingKeys: String, CodingKey { case id, label, unit, dec, value, change, changePct, src, asOf, stale }

    public init(id: String, label: String, unit: String, dec: Int = 2, value: Double, change: Double? = nil, changePct: Double? = nil, src: String = "", asOf: String = "", stale: Bool = false) {
        self.id = id; self.label = label; self.unit = unit; self.dec = dec; self.value = value
        self.change = change; self.changePct = changePct; self.src = src; self.asOf = asOf; self.stale = stale
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.text(.id), let value = c.number(.value) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "id və value məcburidir"))
        }
        self.init(id: id, label: c.text(.label) ?? id, unit: c.text(.unit) ?? "", dec: c.integer(.dec) ?? 2, value: value,
                  change: c.number(.change), changePct: c.number(.changePct), src: c.text(.src) ?? "", asOf: c.text(.asOf) ?? "", stale: c.flag(.stale))
    }

    /// AMB alınmayanda AZN məzənnəsi bazar mənbəyindəndir: dəyişmə faizi göstərilmir, «bazar» yazılır.
    public var isUnofficial: Bool { unit == "AZN" && !src.isEmpty && src != "AMB" }
    public var hasChange: Bool { !isUnofficial && change != nil && changePct != nil }
    public var symbol: String { unit == "AZN" ? "₼" : "$" }
    public var valueText: String { Format.number(value, decimals: dec) }
}

public struct MarketsFeed: Decodable, Sendable {
    public var updatedAt: String?
    public var items: [MarketItem]
    enum CodingKeys: String, CodingKey { case updatedAt, items }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        updatedAt = c.text(.updatedAt)
        items = c.lossy(.items)
    }
}

public enum Converter {
    static func aznRate(_ id: String, _ items: [MarketItem]) -> Double? {
        if id == "AZN" { return 1 }
        guard let item = items.first(where: { $0.id == id }) else { return nil }
        if item.unit == "AZN" { return item.id.hasSuffix("100") ? item.value / 100 : item.value }
        guard let usd = items.first(where: { $0.id == "USD" })?.value, usd != 0 else { return nil }
        return item.value * usd
    }

    /// app.js `convertAmt`: hər şey AZN üzərindən çevrilir.
    public static func convert(_ amount: Double, from: String, to: String, items: [MarketItem]) -> Double? {
        guard let f = aznRate(from, items), let t = aznRate(to, items), f != 0, t != 0 else { return nil }
        return amount * f / t
    }
}

public struct VideoItem: Decodable, Identifiable, Hashable, Sendable {
    public var id: String
    public var title: String
    public var channel: String
    public var videoId: String
    public var url: String
    public var publishedAt: String
    public var imageUrl: String
    enum CodingKeys: String, CodingKey { case id, title, channel, videoId, url, publishedAt, imageUrl }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.text(.id) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "id yoxdur"))
        }
        self.id = id
        title = TextTools.tidy(c.text(.title))
        channel = c.text(.channel) ?? ""
        videoId = c.text(.videoId) ?? ""
        url = c.text(.url) ?? ""
        publishedAt = c.text(.publishedAt) ?? ""
        imageUrl = c.text(.imageUrl) ?? ""
    }
    public var date: Date? { ISODate.parse(publishedAt) }
    public var watchURL: URL? {
        if !videoId.isEmpty { return URL(string: "https://www.youtube.com/watch?v=\(videoId)") }
        return TextTools.webURL(url)
    }
}

public struct VideoFeed: Decodable, Sendable {
    public var items: [VideoItem]
    enum CodingKeys: String, CodingKey { case items }
    public init(from decoder: Decoder) throws {
        items = try decoder.container(keyedBy: CodingKeys.self).lossy(.items)
    }
}

public struct SocialPost: Decodable, Identifiable, Hashable, Sendable {
    public var id: String
    public var name: String
    public var network: String
    public var text: String
    public var url: String
    public var publishedAt: String
    public var imageUrl: String
    enum CodingKeys: String, CodingKey { case id, name, network, text, url, publishedAt, imageUrl }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.text(.id) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "id yoxdur"))
        }
        self.id = id
        name = c.text(.name) ?? ""
        network = c.text(.network) ?? ""
        text = TextTools.tidy(c.text(.text))
        url = c.text(.url) ?? ""
        publishedAt = c.text(.publishedAt) ?? ""
        imageUrl = c.text(.imageUrl) ?? ""
    }
    public var date: Date? { ISODate.parse(publishedAt) }
}

public struct SocialFeed: Decodable, Sendable {
    public var posts: [SocialPost]
    enum CodingKeys: String, CodingKey { case posts }
    public init(from decoder: Decoder) throws {
        posts = try decoder.container(keyedBy: CodingKeys.self).lossy(.posts)
    }
}

public struct SourceStatus: Decodable, Identifiable, Hashable, Sendable {
    public enum Level: Sendable { case ok, warn, bad, unknown }
    public var name: String
    public var url: String
    public var okAt: String?
    public var count: Int?
    public var error: String?
    public var id: String { name }
    enum CodingKeys: String, CodingKey { case name, url, okAt, count, error }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let name = c.text(.name) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "name yoxdur"))
        }
        self.name = name
        url = c.text(.url) ?? ""
        okAt = c.text(.okAt)
        count = c.integer(.count)
        error = c.text(.error)
    }
    /// app.js `sourceLevel`.
    public func level(now: Date = Date()) -> Level {
        guard let count else { return .unknown }
        let age = ISODate.parse(okAt).map { now.timeIntervalSince($0) } ?? .infinity
        if error == nil && count > 0 && age < 6 * 3600 { return .ok }
        if okAt != nil && age < 36 * 3600 { return .warn }
        return .bad
    }
}

public struct SourcesFeed: Decodable, Sendable {
    public var sources: [SourceStatus]
    enum CodingKeys: String, CodingKey { case sources }
    public init(from decoder: Decoder) throws {
        sources = try decoder.container(keyedBy: CodingKeys.self).lossy(.sources)
    }
}

// MARK: - İdman

public struct StandingRow: Decodable, Hashable, Sendable, Identifiable {
    public var pos: Int
    public var team: String
    public var full: String
    public var logo: String
    public var played: Int?
    public var won: Int?
    public var drawn: Int?
    public var lost: Int?
    public var goalsFor: Int?
    public var goalsAgainst: Int?
    public var goalDiff: Int?
    public var points: Int?
    public var pct: Double?
    public var gamesBehind: String?
    public var color: String
    public var note: String
    public var id: String { "\(pos)-\(team)" }

    enum CodingKeys: String, CodingKey { case pos, team, full, logo, p, w, d, l, gf, ga, gd, pts, pct, gb, color, note }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let team = c.text(.team) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "team yoxdur"))
        }
        self.team = team
        pos = c.integer(.pos) ?? 0
        full = c.text(.full) ?? team
        logo = c.text(.logo) ?? ""
        played = c.integer(.p); won = c.integer(.w); drawn = c.integer(.d); lost = c.integer(.l)
        goalsFor = c.integer(.gf); goalsAgainst = c.integer(.ga); goalDiff = c.integer(.gd); points = c.integer(.pts)
        pct = c.number(.pct); gamesBehind = c.text(.gb)
        color = c.text(.color) ?? ""
        note = c.text(.note) ?? ""
    }
}

public struct Game: Decodable, Hashable, Sendable, Identifiable {
    public var home: String
    public var away: String
    public var homeScore: String?
    public var awayScore: String?
    public var date: String
    public var played: Bool
    public var stadium: String
    public var id: String { "\(home)-\(away)-\(date)" }
    enum CodingKeys: String, CodingKey { case home, away, hs, `as`, date, played, stadium }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        home = c.text(.home) ?? ""
        away = c.text(.away) ?? ""
        homeScore = c.text(.hs)
        awayScore = c.text(.as)
        date = c.text(.date) ?? ""
        played = c.flag(.played)
        stadium = c.text(.stadium) ?? ""
    }
}

public struct Scorer: Decodable, Hashable, Sendable, Identifiable {
    public var name: String
    public var club: String
    public var goals: Int
    public var id: String { name + club }
    enum CodingKeys: String, CodingKey { case name, club, goals }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = c.text(.name) ?? ""
        club = c.text(.club) ?? ""
        goals = c.integer(.goals) ?? 0
    }
}

public struct TableGroup: Decodable, Hashable, Sendable, Identifiable {
    public var name: String
    public var rows: [StandingRow]
    public var id: String { name }
    enum CodingKeys: String, CodingKey { case name, rows }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = c.text(.name) ?? ""
        rows = c.lossy(.rows)
    }
    public init(name: String, rows: [StandingRow]) { self.name = name; self.rows = rows }
    public static let azNames = ["Eastern Conference": "Şərq", "Western Conference": "Qərb", "League Phase": "Liqa mərhələsi"]
    public var shownName: String { Self.azNames[name] ?? name }
}

/// Azərbaycan liqaları (football.json) və dünya liqaları (sports.json) bir formada.
public struct League: Hashable, Sendable, Identifiable {
    public var id: String
    public var title: String
    public var short: String
    public var season: String
    public var sport: String
    public var isWorld: Bool
    public var stale: Bool
    public var groups: [TableGroup]
    public var results: [Game]
    public var fixtures: [Game]
    public var scorers: [Scorer]
    public var roundPlayed: String?
    public var roundNext: String?
    public var link: String
    public var source: String
}

struct AzLeagueDTO: Decodable {
    var league: String, short: String, season: String, link: String, source: String
    var stale: Bool
    var table: [StandingRow], results: [Game], fixtures: [Game], scorers: [Scorer]
    var roundPlayed: String?, roundNext: String?
    var leagues: [AzLeagueDTO]
    enum CodingKeys: String, CodingKey { case league, short, season, link, source, stale, table, results, fixtures, scorers, roundPlayed, roundNext, leagues }
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        league = c.text(.league) ?? ""; short = c.text(.short) ?? ""; season = c.text(.season) ?? ""
        link = c.text(.link) ?? "https://pfl.az/"; source = c.text(.source) ?? ""
        stale = c.flag(.stale)
        table = c.lossy(.table); results = c.lossy(.results); fixtures = c.lossy(.fixtures); scorers = c.lossy(.scorers)
        roundPlayed = c.text(.roundPlayed); roundNext = c.text(.roundNext)
        leagues = c.lossy(.leagues)
    }
    var hasData: Bool { !table.isEmpty || !results.isEmpty || !fixtures.isEmpty }
    func toLeague(index: Int) -> League {
        League(id: "az-\(index)", title: league, short: short.isEmpty ? league : short, season: season, sport: "football", isWorld: false, stale: stale,
               groups: table.isEmpty ? [] : [TableGroup(name: "Turnir cədvəli", rows: table)], results: results, fixtures: fixtures, scorers: scorers,
               roundPlayed: roundPlayed, roundNext: roundNext, link: link, source: source)
    }
}

public struct FootballFeed: Decodable, Sendable {
    public var leagues: [League]
    public init(from decoder: Decoder) throws {
        let top = try AzLeagueDTO(from: decoder)
        let list = top.leagues.isEmpty ? [top] : top.leagues
        leagues = list.filter(\.hasData).enumerated().map { $1.toLeague(index: $0) }
    }
}

public struct SportsFeed: Decodable, Sendable {
    public var leagues: [League]
    private struct Item: Decodable {
        var id: String, sport: String, name: String, short: String, season: String
        var stale: Bool
        var groups: [TableGroup]
        enum CodingKeys: String, CodingKey { case id, sport, name, short, season, stale, groups }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            id = c.text(.id) ?? UUID().uuidString; sport = c.text(.sport) ?? "football"; name = c.text(.name) ?? ""
            short = c.text(.short) ?? name; season = c.text(.season) ?? ""
            stale = c.flag(.stale); groups = c.lossy(.groups)
        }
    }
    enum CodingKeys: String, CodingKey { case leagues }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let items: [Item] = c.lossy(.leagues)
        leagues = items.filter { !$0.groups.isEmpty }.map {
            League(id: $0.id, title: $0.name, short: $0.short, season: $0.season, sport: $0.sport, isWorld: true, stale: $0.stale,
                   groups: $0.groups, results: [], fixtures: [], scorers: [], roundPlayed: nil, roundNext: nil, link: "https://www.espn.com/", source: "ESPN")
        }
    }
}
