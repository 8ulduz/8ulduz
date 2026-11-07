import Foundation

// Komanda və liqa məlumatı: data/futbol/ (updater.py, update_team_pages). Məntiq assets/komanda.js ilədir.

public struct TeamSeason: Decodable, Hashable, Sendable, Identifiable {
    public let key: String
    public let label: String
    public var id: String { key }
    enum CodingKeys: String, CodingKey { case key, label }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        key = c.text(.key) ?? ""
        label = c.text(.label) ?? key
    }
}

public struct TeamLeague: Decodable, Hashable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let short: String
    public let source: String
    public let sport: String
    public let cup: Bool
    public let reserve: Bool
    public let teams: [String]
    public let ready: [TeamSeason]
    public let squads: [String]

    enum CodingKeys: String, CodingKey { case id, name, short, source, sport, cup, reserve, teams, ready, heyet }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.text(.id) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "id yoxdur"))
        }
        self.id = id
        name = c.text(.name) ?? id
        short = c.text(.short) ?? name
        source = c.text(.source) ?? ""
        sport = c.text(.sport) ?? "football"
        cup = c.flag(.cup)
        reserve = c.flag(.reserve)
        teams = c.lossy(.teams)
        ready = c.lossy(.ready)
        squads = c.lossy(.heyet)
    }

    /// Faylın adı: cari mövsüm `<id>.json`, qalanları `<id>-<mövsüm>.json`.
    public func path(season key: String? = nil) -> String {
        guard let key, let current = ready.first?.key, key != current else { return "futbol/\(id).json" }
        return "futbol/\(id)-\(key).json"
    }

    public var isLocal: Bool { source == "pfl.az" }
    public var isBasketball: Bool { sport == "basketball" }
}

public struct TeamIndex: Decodable, Sendable {
    public let leagues: [TeamLeague]
    public let checked: [String: String]

    enum CodingKeys: String, CodingKey { case leagues, checked }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let all: [TeamLeague] = c.lossy(.leagues)
        leagues = all.filter { !$0.ready.isEmpty }
        checked = (try? c.decodeIfPresent([String: String].self, forKey: .checked)) ?? [:]
    }

    public func league(_ id: String) -> TeamLeague? { leagues.first { $0.id == id } }

    /// Komandanın digər yarışları (Kubok, Çempionlar Liqası). Əvəzedicilər ayrı komandadır, oyunları qarışmır.
    public func otherLeagues(_ league: TeamLeague, team: String) -> [TeamLeague] {
        if league.reserve { return [] }
        return leagues.filter { $0.id != league.id && !$0.reserve && $0.sport == league.sport && $0.teams.contains(team) }
    }
}

public struct TeamInfo: Decodable, Hashable, Sendable {
    public let name: String
    public let short: String
    public let logo: String
    public var shownName: String { short.isEmpty ? name : short }
    enum CodingKeys: String, CodingKey { case name, short, logo }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = c.text(.name) ?? ""
        short = c.text(.short) ?? ""
        logo = c.text(.logo) ?? ""
    }
}

public struct TeamRow: Decodable, Hashable, Sendable, Identifiable {
    public let team: String
    public let pos: Int
    public let played: Int?
    public let won: Int?
    public let drawn: Int?
    public let lost: Int?
    public let goalsFor: Int?
    public let goalsAgainst: Int?
    public let goalDiff: Int?
    public let points: Int?
    public let pct: Double?
    public let gamesBehind: String?
    public let color: String
    public let note: String
    public var id: String { team }

    enum CodingKeys: String, CodingKey { case team, pos, p, w, d, l, gf, ga, gd, pts, pct, gb, color, note }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let team = c.text(.team) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "team yoxdur"))
        }
        self.team = team
        pos = c.integer(.pos) ?? 0
        played = c.integer(.p); won = c.integer(.w); drawn = c.integer(.d); lost = c.integer(.l)
        goalsFor = c.integer(.gf); goalsAgainst = c.integer(.ga); goalDiff = c.integer(.gd); points = c.integer(.pts)
        pct = c.number(.pct); gamesBehind = c.text(.gb)
        color = c.text(.color) ?? ""
        note = c.text(.note) ?? ""
    }
}

public struct TeamTable: Decodable, Hashable, Sendable, Identifiable {
    public let name: String
    public let rows: [TeamRow]
    public var id: String { name + (rows.first?.team ?? "") }
    enum CodingKeys: String, CodingKey { case name, rows }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = c.text(.name) ?? ""
        rows = c.lossy(.rows)
    }
}

public struct TeamGame: Decodable, Hashable, Sendable, Identifiable {
    public enum Outcome: Sendable { case win, draw, loss }

    public let home: String
    public let away: String
    public let homeScore: Int?
    public let awayScore: Int?
    public let date: String
    public let played: Bool
    public let stadium: String
    public let round: String
    public let penalties: String
    public let state: String
    public let dateOnly: Bool
    public var id: String { "\(home)|\(away)|\(date)|\(round)" }

    enum CodingKeys: String, CodingKey { case home, away, hs, `as`, date, played, stadium, round, pen, state, day }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        home = c.text(.home) ?? ""
        away = c.text(.away) ?? ""
        homeScore = c.integer(.hs)
        awayScore = c.integer(.as)
        date = c.text(.date) ?? ""
        played = c.flag(.played)
        stadium = c.text(.stadium) ?? ""
        round = c.text(.round) ?? ""
        penalties = c.text(.pen) ?? ""
        state = c.text(.state) ?? ""
        dateOnly = c.flag(.day)
    }

    public func outcome(for team: String) -> Outcome? {
        guard played, let homeScore, let awayScore else { return nil }
        let mine = home == team ? homeScore : awayScore, other = home == team ? awayScore : homeScore
        return mine > other ? .win : mine < other ? .loss : .draw
    }

    public func opponent(of team: String) -> String { home == team ? away : home }

    /// Oyunun vəziyyəti (komanda.js `gameCard`).
    public func stateText(now: Date = Date()) -> String {
        if played { return penalties.isEmpty ? "Bitib" : "Pen. \(penalties)" }
        if state == "live" { return "Oyun gedir" }
        if state == "off" { return "Təxirə salınıb" }
        if let d = ISODate.parse(date), d < now { return "Nəticə gözlənilir" }
        return ""
    }

    public var roundText: String {
        if round.isEmpty { return "" }
        return Int(round) != nil ? Format.round(round) : round
    }

    public var whenText: String {
        if date.isEmpty { return "Vaxtı elan olunmayıb" }
        let text = Format.shortDateTime(date)
        return dateOnly ? String(text.split(separator: ",").first ?? "") : text
    }

    static func byKick(_ a: TeamGame, _ b: TeamGame) -> Bool {
        (a.date.isEmpty ? "9999" : a.date) < (b.date.isEmpty ? "9999" : b.date)
    }
}

public struct LeagueDoc: Decodable, Sendable {
    public let id: String
    public let name: String
    public let short: String
    public let source: String
    public let url: String
    public let sourceURL: String
    public let sport: String
    public let asOf: String
    public let season: String
    public let teams: [String: TeamInfo]
    public let groups: [TeamTable]
    public let games: [TeamGame]
    private let byTeam: [String: [TeamGame]]

    enum CodingKeys: String, CodingKey {
        case id, name, short, source, url, source_url, sport, asof, season, teams, groups, games
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.text(.id) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "id yoxdur"))
        }
        self.id = id
        name = c.text(.name) ?? id
        short = c.text(.short) ?? name
        source = c.text(.source) ?? ""
        url = c.text(.url) ?? ""
        sourceURL = c.text(.source_url) ?? ""
        sport = c.text(.sport) ?? "football"
        asOf = c.text(.asof) ?? ""
        season = c.text(.season) ?? ""
        teams = (try? c.decodeIfPresent([String: TeamInfo].self, forKey: .teams)) ?? [:]
        groups = c.lossy(.groups)
        games = c.lossy(.games)
        var map: [String: [TeamGame]] = [:]
        for game in games {
            map[game.home, default: []].append(game)
            map[game.away, default: []].append(game)
        }
        byTeam = map
    }

    public var isBasketball: Bool { sport == "basketball" }

    public func info(_ team: String) -> TeamInfo? { teams[team] }

    public func games(of team: String) -> [TeamGame] { byTeam[team] ?? [] }

    public func form(of team: String, last n: Int = 5) -> [TeamGame.Outcome] {
        games(of: team).filter(\.played).sorted(by: TeamGame.byKick).suffix(n).compactMap { $0.outcome(for: team) }
    }

    public func row(of team: String) -> (row: TeamRow, group: TeamTable)? {
        for group in groups {
            if let row = group.rows.first(where: { $0.team == team }) { return (row, group) }
        }
        return nil
    }

    /// Komanda və qonşuları: baxışdakı qısa cədvəl.
    public func neighbours(of team: String) -> [TeamRow] {
        guard let hit = row(of: team), let at = hit.group.rows.firstIndex(of: hit.row) else { return [] }
        let rows = hit.group.rows
        let from = max(0, min(at - 2, rows.count - 5))
        return Array(rows[from..<min(from + 5, rows.count)])
    }

    /// Cədvəlin zona izahı, cədvəldəki sırası ilə.
    public static func zones(_ rows: [TeamRow]) -> [(note: String, color: String)] {
        var seen = Set<String>()
        var out: [(note: String, color: String)] = []
        for row in rows where !row.note.isEmpty && !row.color.isEmpty && seen.insert(row.note).inserted {
            out.append((noteAz[row.note] ?? row.note, row.color))
        }
        return out
    }

    private static let noteAz = [
        "Champions League": "Çempionlar Liqası", "Champions League qualifying": "Çempionlar Liqasının seçmə mərhələsi",
        "Europa League": "Avropa Liqası", "Europa League qualifying": "Avropa Liqasının seçmə mərhələsi",
        "Conference League": "Konfrans Liqası", "Conference League qualifying": "Konfrans Liqasının seçmə mərhələsi",
        "Relegation": "Aşağı liqaya düşmə", "Relegated": "Aşağı liqaya düşmə", "Relegation playoff": "Aşağı liqa üçün pley-off",
        "Qualifies for round of 16": "1/8 finala çıxış", "Knockout phase playoffs - seeded": "Pley-off (səbətli)",
        "Knockout phase playoffs - unseeded": "Pley-off (səbətsiz)", "Eliminated": "Mübarizədən çıxır",
    ]

    /// Cədvəl hansı günün oyunlarına qədərdir: Vikipediya bəzi liqaları bir neçə gün gec yeniləyir.
    public var asOfText: String { Format.gamesUntil(asOf) }
}

public enum TeamGames {
    /// Oynanmış və qarşıdakı oyunlar. Vaxtı keçib nəticəsi gəlməyən oyun «qarşıdakı» sayılmır, təxirə salınan da.
    public static func split(_ games: [TeamGame], now: Date = Date()) -> (played: [TeamGame], next: [TeamGame]) {
        let sorted = games.sorted(by: TeamGame.byKick)
        let next = sorted.filter { g in
            guard !g.played, g.state != "off" else { return false }
            if g.date.isEmpty { return true }
            return (ISODate.parse(g.date) ?? .distantPast) > now
        }
        return (sorted.filter(\.played), next)
    }

    /// Tam siyahı aylara bölünür.
    public static func byMonth(_ games: [TeamGame]) -> [(title: String, games: [TeamGame])] {
        var out: [(title: String, games: [TeamGame])] = []
        for game in games.sorted(by: TeamGame.byKick) {
            let title = Format.monthTitle(game.date)
            if out.last?.title == title { out[out.count - 1].games.append(game) }
            else { out.append((title, [game])) }
        }
        return out
    }
}

public struct SquadPlayer: Decodable, Hashable, Sendable, Identifiable {
    public let number: String
    public let position: String
    public let name: String
    public let age: String
    public let flag: String
    public let country: String
    public var id: String { name + number }
    enum CodingKeys: String, CodingKey { case no, pos, name, age, flag, country }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        number = c.text(.no) ?? ""
        position = c.text(.pos) ?? ""
        name = c.text(.name) ?? ""
        age = c.text(.age) ?? ""
        flag = c.text(.flag) ?? ""
        country = c.text(.country) ?? ""
    }
    public static let positions: [(key: String, label: String)] = [("gk", "Qapıçılar"), ("df", "Müdafiəçilər"), ("mf", "Yarımmüdafiəçilər"), ("fw", "Hücumçular"), ("", "Digər")]
}

public struct SquadDoc: Decodable, Sendable {
    public struct Team: Decodable, Sendable {
        public let players: [SquadPlayer]
        public let wiki: String
        enum CodingKeys: String, CodingKey { case players, wiki }
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            players = c.lossy(.players)
            wiki = c.text(.wiki) ?? ""
        }
    }
    public let teams: [String: Team]
    enum CodingKeys: String, CodingKey { case teams }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        teams = (try? c.decodeIfPresent([String: Team].self, forKey: .teams)) ?? [:]
    }
}

public enum TeamNews {
    private static let otherSport = Rx("basketbol|voleybol|həndbol|tennis|cüdo|güləş|boks|futzal|şahmat|шахмат|gimnast|basketball|баскетбол|волейбол", caseInsensitive: true)
    private static let basket = Rx("basketbol|basketball|баскетбол|avroliqa|euroleague|евролиг", caseInsensitive: true)
    private static let suffix = "(?:in|nin|un|nun|ün|nün|ın|nın|a|e|i|u|ya|ye|ni|nu|na|ne|la|le|dan|den|ndan|nden|da|de|nda|nde|nı|nü|s|а|у|е|я|ю|ы|и|ь|ом|ем)?"

    /// Ad birbaşa regex-ə düşür, mövzusu olmayan komanda üçün: böyük hərf saxlanır, ingiliscə «nice» Nitsa sayılmasın.
    static func nameRx(_ names: [String]) -> Rx? {
        let safe = Array(Set(names.filter { $0.count >= 3 })).sorted().map { NSRegularExpression.escapedPattern(for: $0) }.joined(separator: "|")
        return safe.isEmpty ? nil : Rx("(?<![\\p{L}\\p{N}])(?:\(safe))\(suffix)(?![\\p{L}\\p{N}])")
    }

    /// Komandanın xəbərləri: yalnız idman bölməsi və başqa idman növlərinin xəbəri olmadan (komanda.js `newsOf`).
    public static func articles(team: TeamInfo, league: LeagueDoc, in pool: [Article]) -> [Article] {
        let isBasket = league.isBasketball
        let topic = isBasket ? nil : Topics.teamTopic(team.name)
        let rx = topic == nil ? nameRx([team.name, team.short]) : nil
        return Ranking.byDate(pool.filter { a in
            guard a.category == "idman" else { return false }
            if isBasket {
                if league.id == "avroliqa" && !basket.test(TextTools.decodeEntities(a.title + " " + a.summary)) { return false }
            } else if otherSport.test(TextTools.decodeEntities(a.title)) {
                return false
            }
            if let topic { return Topics.matches(a, topic) }
            return rx?.test(TextTools.decodeEntities("\(a.title) \(a.summary)")) ?? false
        })
    }
}
