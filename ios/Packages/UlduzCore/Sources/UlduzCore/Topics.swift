import Foundation

public struct TopicGroup: Decodable, Sendable, Identifiable {
    public let group: String
    public let items: [Topic]
    public var id: String { group + (items.first?.name ?? "") }

    public func filtered(_ keep: (Topic) -> Bool) -> TopicGroup {
        TopicGroup(group: "", items: items.filter(keep))
    }
}

/// İdman və bölgə düyməsi (app.js `SPORT_TABS`, `REGION_TABS`).
public struct Topic: Decodable, Sendable, Identifiable {
    public let name: String
    public let label: String?
    public let keys: [String]
    public let stems: [String]
    public let not: [String]
    public let sources: [String]
    public let skip: [String]
    public let must: [String]
    public let mustSites: [String]
    public let quoted: String?
    public let groups: [TopicGroup]

    public var id: String { name }
    public var shownName: String { label ?? name }

    enum CodingKeys: String, CodingKey { case name, label, keys, stems, not, sources, skip, must, mustSites, quoted, groups }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = try c.decode(String.self, forKey: .name)
        label = try c.decodeIfPresent(String.self, forKey: .label)
        keys = try c.decodeIfPresent([String].self, forKey: .keys) ?? []
        stems = try c.decodeIfPresent([String].self, forKey: .stems) ?? []
        not = try c.decodeIfPresent([String].self, forKey: .not) ?? []
        sources = try c.decodeIfPresent([String].self, forKey: .sources) ?? []
        skip = try c.decodeIfPresent([String].self, forKey: .skip) ?? []
        must = try c.decodeIfPresent([String].self, forKey: .must) ?? []
        mustSites = try c.decodeIfPresent([String].self, forKey: .mustSites) ?? []
        quoted = try c.decodeIfPresent(String.self, forKey: .quoted)
        groups = try c.decodeIfPresent([TopicGroup].self, forKey: .groups) ?? []
    }
}

/// Xəbərin mətni bir dəfə hazırlanır: Futbol düyməsi hər xəbəri 20 komanda ilə yoxlayır.
public struct TopicText: Sendable {
    let raw: String
    let text: String
    let source: String

    public init(_ a: Article) {
        raw = TextTools.decodeEntities(a.title + " " + a.summary)
        text = " \(Topics.key(raw)) "
        source = a.source
    }

    init(title: String, source: String = "") {
        raw = TextTools.decodeEntities(title)
        text = " \(Topics.key(raw)) "
        self.source = source
    }
}

/// assets/app.js `clubMatches`.
public enum Topics {
    public enum Scope: Sendable { case sport, region }

    private struct Tree: Decodable {
        var SPORT_TEAMS: [TopicGroup] = []
        var SPORT_TABS: [Topic] = []
        var REGION_TABS: [Topic] = []
    }

    private static let tree: Tree = (try? JSONDecoder().decode(Tree.self, from: Data(TopicData.json.utf8))) ?? Tree()

    public static var sportTeams: [TopicGroup] { tree.SPORT_TEAMS }
    public static var sportTabs: [Topic] { tree.SPORT_TABS }
    public static var regionTabs: [Topic] { tree.REGION_TABS }

    /// Alt başlığı olan bölmələr.
    public static func tabs(forSection slug: String) -> [Topic] {
        switch slug {
        case "idman": return sportTabs
        case "bolgeler": return regionTabs
        default: return []
        }
    }

    private static let spaces = Rx("[^\\p{L}\\p{N}]+")

    static func key(_ s: String) -> String {
        spaces.replace(TextTools.fold(s), with: " ").trimmingCharacters(in: .whitespaces)
    }

    /// Komanda səhifəsinin ünvanı: updater.py-dakı `team_slug` ilə eyni.
    public static func slug(_ s: String) -> String { key(s).replacingOccurrences(of: " ", with: "-") }

    private static let suffix = "(?:in|nin|un|nun|a|e|i|u|ya|ye|ni|nu|na|ne|la|le|dan|den|ndan|nden|da|de|nda|nde|s|а|у|е|я|ю|ы|и|ь|ом|ем|еи|ои)?"

    private final class Compiled: @unchecked Sendable {
        let topic: Topic
        let rx: Rx
        let quoted: Rx?
        let not: [String]
        let must: [String]
        var children: [Compiled] = []

        init(_ topic: Topic) {
            self.topic = topic
            // Bir saytın alt bölməsi olan mövzuda söz şərti yoxdursa heç nəyə uyğun gəlməsin.
            var parts = ["\\b\\B"]
            if !topic.keys.isEmpty { parts.append("(?:\(topic.keys.map(Topics.key).joined(separator: "|")))\(Topics.suffix) ") }
            if !topic.stems.isEmpty { parts.append("(?:\(topic.stems.map(Topics.key).joined(separator: "|")))") }
            rx = Rx(" (?:\(parts.joined(separator: "|")))")
            quoted = topic.quoted.map { Rx("[\"«“'‘„]\($0)[\"»”'’]", caseInsensitive: true) }
            not = topic.not.map(Topics.key)
            must = topic.must.map(Topics.key)
        }

        func matches(_ t: TopicText) -> Bool {
            if topic.skip.contains(t.source) { return false }
            if topic.sources.contains(t.source) { return true }
            if not.contains(where: { t.text.contains($0) }) { return false }
            if !must.isEmpty, !topic.mustSites.contains(t.source), !must.contains(where: { t.text.contains(" \($0)") }) { return false }
            if let quoted, quoted.test(t.raw) { return true }
            if rx.test(t.text) { return true }
            return children.contains { $0.matches(t) }
        }
    }

    private static func compile(_ tabs: [Topic]) -> [String: Compiled] {
        var out: [String: Compiled] = [:]
        func add(_ topic: Topic) -> Compiled {
            let item = Compiled(topic)
            item.children = topic.groups.flatMap(\.items).map(add)
            out[topic.name] = item
            return item
        }
        for tab in tabs { _ = add(tab) }
        return out
    }

    private static let sportTopics = compile(sportTabs)
    // «Qarabağ» həm komanda, həm bölgədir: hər bölmə öz siyahısına baxır.
    private static let regionTopics = compile(regionTabs)

    private static func topic(_ name: String, _ scope: Scope) -> Compiled? {
        scope == .sport ? sportTopics[name] : regionTopics[name]
    }

    public static func matches(_ text: TopicText, _ name: String, scope: Scope = .sport) -> Bool {
        topic(name, scope)?.matches(text) ?? false
    }

    public static func matches(_ a: Article, _ name: String, scope: Scope = .sport) -> Bool {
        matches(TopicText(a), name, scope: scope)
    }

    /// Komanda adı axtarılanda yazılışından asılı olmayaraq həmin komandanın xəbərləri gəlir (app.js `searchTopics`).
    public static func searchTopics(_ query: String) -> [String] {
        let text = " \(key(query)) "
        return sportTopics.values
            .filter { (!$0.topic.keys.isEmpty || !$0.topic.stems.isEmpty) && $0.rx.test(text) }
            .map(\.topic.name)
            .sorted()
    }

    private static let teamAlias = ["Internazionale": "İnter", "Paris Saint-Germain": "PSG"]

    /// Komandanın mövzusu; yoxdursa `nil`, onda xəbər adın özü ilə axtarılır (komanda.js `topicFor`).
    public static func teamTopic(_ name: String) -> String? {
        if let alias = teamAlias[name] { return alias }
        let text = TopicText(title: name)
        let topics = sportTeams.flatMap(\.items).filter { $0.name != "Milli komanda" }
        return topics.first { $0.name == name || matches(text, $0.name) }?.name
    }
}
