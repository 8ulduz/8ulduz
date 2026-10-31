import Foundation

/// QIRMIZI XƏTT 2 (docs/qirmizi-xetler.md). Qaydalar yalnız bir yerdədir: assets/content-policy.js.
/// Tətbiq həmin faylı özü ilə gətirir (`ContentPolicy.bundled`) və saytdan yeniləyir, buna görə qayda tətbiqdə ayrıca saxlanmır.
public struct ContentPolicy: Sendable {
    struct Rules: Decodable, Sendable {
        var azSources: [String: [String]]
        var worldSources: [String: [String]]
        var sportSources: [String]?
        var videoChannels: [String]?
        var blockedHosts: [String]
        var azTerms: String
        var leaderTerms: String
    }

    public enum ParseError: Error { case noObject }

    private let rules: Rules
    private let azTerms: Rx
    private let leaderTerms: Rx

    public init(javascript: String) throws {
        guard let marker = javascript.range(of: "CONTENT_POLICY"),
              let open = javascript[marker.upperBound...].firstIndex(of: "{"),
              let close = javascript.lastIndex(of: "}"), open < close else { throw ParseError.noObject }
        let json = Data(javascript[open...close].utf8)
        rules = try JSONDecoder().decode(Rules.self, from: json)
        azTerms = Rx(rules.azTerms, caseInsensitive: true)
        leaderTerms = Rx(rules.leaderTerms, caseInsensitive: true)
    }

    /// Qayda faylı oxunmursa xarici mənbədən heç nə buraxılmır, sayt mənbələri də siyahısız olduğu üçün düşür.
    public static var failClosed: ContentPolicy {
        try! ContentPolicy(javascript: #"CONTENT_POLICY = {"azSources":{},"worldSources":{},"blockedHosts":[],"azTerms":"","leaderTerms":""}"#)
    }

    /// Tətbiqə yığımda qoyulan nüsxə.
    public static func bundled(in bundle: Bundle = .main) -> ContentPolicy {
        guard let url = bundle.url(forResource: "content-policy", withExtension: "js"),
              let text = try? String(contentsOf: url, encoding: .utf8),
              let policy = try? ContentPolicy(javascript: text) else { return .failClosed }
        return policy
    }

    /// `azTerms` tətbiqin regex mühərrikində açılmasa yoxlama işləmir: xarici mənbə xəbəri ümumiyyətlə düşmür.
    private var regexReady: Bool { azTerms.isValid && leaderTerms.isValid }

    private func matches(_ rx: Rx, _ text: String) -> Bool {
        rx.test(text) || rx.test(TextTools.azLowercased(text))
    }

    private func onHost(_ host: String, _ domains: [String]) -> Bool {
        domains.contains { host == $0 || host.hasSuffix("." + $0) }
    }

    private func domains(for source: String) -> [String]? {
        rules.azSources[source] ?? rules.worldSources[source]
    }

    private func isWorld(_ source: String) -> Bool { rules.worldSources[source] != nil }

    private func isSportSource(_ source: String) -> Bool { rules.sportSources?.contains(source) ?? false }

    private func isHTTP(_ url: String) -> Bool {
        let lower = url.lowercased()
        return lower.hasPrefix("http://") || lower.hasPrefix("https://")
    }

    /// app.js `removedSource`.
    func removedSource(name: String, url: String) -> Bool {
        if ["azadlıq", "azadliq", "azadliq.org"].contains(TextTools.azLowercased(name)) { return true }
        let host = TextTools.host(of: url)
        return host == "azadliq.org" || host.hasSuffix(".azadliq.org")
    }

    /// app.js `sourceForbidden`: siyahıda olmayan mənbə, qadağan sayt və ya keçidi başqa sayta aparan xəbər.
    public func sourceForbidden(source: String, url: String) -> Bool {
        let host = TextTools.host(of: url)
        guard isHTTP(url), !onHost(host, rules.blockedHosts), let domains = domains(for: source) else { return true }
        return !onHost(host, domains)
    }

    /// app.js `policyViolation`.
    public func violation(source: String, url: String, title: String, summary: String, category: String) -> Bool {
        if removedSource(name: source, url: url) || sourceForbidden(source: source, url: url) { return true }
        guard isWorld(source) else { return false }
        guard regexReady else { return true }
        let text = "\(title) \(summary)"
        let sport = category == "idman" && isSportSource(source)
        return matches(sport ? leaderTerms : azTerms, text)
    }

    public func violation(_ a: Article) -> Bool {
        violation(source: a.source, url: a.sourceUrl, title: a.title, summary: a.summary, category: a.category)
    }

    /// app.js `altForbidden`: əlavə mənbənin öz başlığı da, əsas xəbərin mövzusu da yoxlanır.
    public func altForbidden(primary a: Article, alt: AltSource) -> Bool {
        if removedSource(name: alt.source, url: alt.sourceUrl) || sourceForbidden(source: alt.source, url: alt.sourceUrl) { return true }
        guard isWorld(alt.source) else { return false }
        guard regexReady else { return true }
        if violation(source: alt.source, url: alt.sourceUrl, title: alt.title, summary: "", category: a.category) { return true }
        if a.category == "idman" && isSportSource(alt.source) { return false }
        return matches(azTerms, "\(a.title) \(a.summary)")
    }

    /// Lenti ekrana buraxmazdan əvvəlki son qapı.
    public func clean(_ articles: [Article]) -> [Article] {
        articles.compactMap { a -> Article? in
            guard !violation(a) else { return nil }
            var copy = a
            copy.alts = a.alts.filter { !altForbidden(primary: a, alt: $0) }
            return copy
        }
    }

    public func allowsVideo(channel: String) -> Bool {
        guard let list = rules.videoChannels, !list.isEmpty else { return true }
        return list.contains(channel)
    }

    /// Xarici keçid (vidcet, bildiriş) yalnız icazəli mənbəyə apara bilər.
    public func allowsExternalLink(_ url: String) -> Bool {
        guard isHTTP(url) else { return false }
        let host = TextTools.host(of: url)
        if onHost(host, rules.blockedHosts) { return false }
        return rules.azSources.values.contains { onHost(host, $0) } || rules.worldSources.values.contains { onHost(host, $0) }
    }
}
