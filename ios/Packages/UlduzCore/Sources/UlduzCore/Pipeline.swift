import Foundation

/// Xam lentdən ekrandakı lentə (app.js `publishNews`): qayda, birləşdirmə, şəkillər.
public enum NewsPipeline {
    static let hour: TimeInterval = 3600
    static let groupWindow: TimeInterval = 36 * hour
    static let officialSources: Set<String> = ["Prezident.az", "Mehriban Əliyeva"]
    static let stateSources: Set<String> = ["AZƏRTAC", "AZƏRTAC (Regionlar)", "Cross Media", "Xalq qəzeti", "Azərbaycan qəzeti", "Yeni Azərbaycan", "Baku TV",
                                            "APA", "Report", "Trend", "Azernews", "Day.Az", "News.az", "Xezerxeber"]
    private static let stopWords: Set<String> = Set("ve ile the and for from or bir bu da de ki veya icin olan və ilə də o üçün ya news xəbər xeber".split(separator: " ").map(String.init))

    public static func publish(raw: [Article], og: [String: String], policy: ContentPolicy) -> [Article] {
        let withImages = raw.map { a -> Article in
            guard a.imageUrl.isEmpty, let image = og[a.sourceUrl], !image.isEmpty else { return a }
            return a.withImage(image)
        }
        let allowed = policy.clean(withImages)
        var merged = collapseExact(cluster(allowed))
        for i in merged.indices where merged[i].imageUrl.isEmpty && !merged[i].alts.isEmpty {
            let alts = merged[i].alts
            if let alt = alts.first(where: { !$0.imageUrl.isEmpty }) {
                merged[i].imageUrl = alt.imageUrl
            } else if let alt = alts.first(where: { !(og[$0.sourceUrl] ?? "").isEmpty }) {
                merged[i].imageUrl = og[alt.sourceUrl] ?? ""
            }
        }
        return Ranking.byDate(merged)
    }

    /// `latest.json`-dan gələn yenilər, artıq lentdə olan keçidlər çıxılmaqla (app.js `loadLatest`).
    public static func novel(_ latest: [Article], against raw: [Article]) -> [Article] {
        var known = Set<String>()
        known.reserveCapacity(raw.count * 2)
        for a in raw {
            known.insert(a.sourceUrl)
            for alt in a.alts { known.insert(alt.sourceUrl) }
        }
        return latest.filter { !known.contains($0.sourceUrl) }
    }

    // MARK: - Oxşar başlıqlar

    static func titleTokens(_ s: String) -> [String] {
        TextTools.normTitle(s).split(separator: " ").map(String.init).filter { t in
            t.count > 2 && !stopWords.contains(t) && !t.allSatisfy(\.isNumber)
        }
    }

    static func shingles(_ toks: [String]) -> Set<String> {
        if toks.count < 3 { return toks.isEmpty ? [] : [toks.joined(separator: " ")] }
        var out = Set<String>()
        for i in 0...(toks.count - 3) { out.insert(toks[i..<(i + 3)].joined(separator: " ")) }
        return out
    }

    private static func jaccard(_ a: Set<String>, _ b: Set<String>) -> Double {
        guard !a.isEmpty, !b.isEmpty else { return 0 }
        let inter = a.intersection(b).count
        return Double(inter) / Double(a.count + b.count - inter)
    }

    static func titlesSimilar(_ toks: [String], _ sh: Set<String>, _ other: [String], _ otherSh: Set<String>) -> Bool {
        let a = Set(toks), b = Set(other)
        guard a.count >= 3, b.count >= 3 else { return false }
        let inter = a.intersection(b).count
        let tj = jaccard(a, b), sj = jaccard(sh, otherSh)
        let shorter = a.count <= b.count ? a : b, longer = a.count <= b.count ? b : a
        let cont = Double(shorter.intersection(longer).count) / Double(shorter.count)
        let ratio = Double(min(a.count, b.count)) / Double(max(a.count, b.count))
        if inter >= 4 && tj >= 0.55 { return true }
        if inter >= 3 && (tj >= 0.75 || sj >= 0.45) && ratio >= 0.5 { return true }
        if cont >= 0.86 && inter >= 4 && ratio >= 0.62 { return true }
        return false
    }

    static func preferPrimary(_ a: Article, _ b: Article) -> Article {
        let ao = officialSources.contains(a.source), bo = officialSources.contains(b.source)
        if ao != bo { return ao ? a : b }
        if a.imageUrl.isEmpty != b.imageUrl.isEmpty { return a.imageUrl.isEmpty ? b : a }
        if a.summary.count != b.summary.count { return a.summary.count > b.summary.count ? a : b }
        return a.publishedAt >= b.publishedAt ? a : b
    }

    private static func altOf(_ a: Article) -> AltSource {
        AltSource(source: a.source, sourceUrl: a.sourceUrl, publishedAt: a.publishedAt, imageUrl: a.imageUrl, title: a.title, lang: a.lang)
    }

    private struct ClusterItem {
        let date: Date?
        let toks: [String]
        let sh: Set<String>
        let article: Article
    }

    /// updater.py qruplamayıbsa eyni qayda ilə burada birləşir. `alts` gələndə ona etibar olunur.
    static func cluster(_ list: [Article]) -> [Article] {
        if list.isEmpty || list.contains(where: { !$0.alts.isEmpty }) { return list }
        let prepared: [ClusterItem] = list.map { a in
            let toks = titleTokens(a.title)
            return ClusterItem(date: a.date, toks: toks, sh: shingles(toks), article: a)
        }.sorted { ($0.date ?? .distantPast) > ($1.date ?? .distantPast) }

        var clusters: [[ClusterItem]] = []
        for item in prepared {
            var placed = false
            if let date = item.date, item.toks.count >= 3 {
                for i in clusters.indices {
                    guard let head = clusters[i][0].date, abs(date.timeIntervalSince(head)) <= groupWindow else { continue }
                    if clusters[i].contains(where: { $0.article.source == item.article.source }) { continue }
                    let similar = clusters[i].contains { m in
                        guard let md = m.date, abs(date.timeIntervalSince(md)) <= groupWindow else { return false }
                        return titlesSimilar(item.toks, item.sh, m.toks, m.sh)
                    }
                    if similar { clusters[i].append(item); placed = true; break }
                }
            }
            if !placed { clusters.append([item]) }
        }
        var out: [Article] = clusters.map { members in
            var primary = members[0].article
            for m in members.dropFirst() { primary = preferPrimary(primary, m.article) }
            let chosen = primary.sourceUrl
            let alts = members.map(\.article).filter { $0.sourceUrl != chosen }.map(altOf)
            if !alts.isEmpty { primary.alts = alts.sorted { $0.publishedAt > $1.publishedAt } }
            return primary
        }
        out.sort { $0.publishedAt > $1.publishedAt }
        return out
    }

    private struct ExactGroup {
        let key: String
        let date: Date?
        var items: [Article]
    }

    private static func merge(_ items: [Article]) -> Article {
        var primary = items[0]
        for a in items.dropFirst() { primary = preferPrimary(primary, a) }
        var seen: Set<String> = [primary.sourceUrl]
        var alts: [AltSource] = []
        func add(_ alt: AltSource) {
            guard !alt.sourceUrl.isEmpty, seen.insert(alt.sourceUrl).inserted else { return }
            alts.append(alt)
        }
        for a in items {
            if a.sourceUrl != primary.sourceUrl { add(altOf(a)) }
            for alt in a.alts { add(alt) }
        }
        primary.alts = alts.sorted { $0.publishedAt > $1.publishedAt }
        return primary
    }

    /// Eyni başlıq (eyni mənbə adı da olsa) 36 saat içində bir kart olsun (app.js `collapseExact`).
    static func collapseExact(_ list: [Article]) -> [Article] {
        var groups: [ExactGroup] = []
        var byKey: [String: [Int]] = [:]
        for a in list {
            let key = TextTools.normTitle(TextTools.decodeEntities(a.title))
            var target: Int?
            if key.count >= 12, let date = a.date {
                target = byKey[key]?.first { idx in
                    guard let d = groups[idx].date else { return false }
                    return abs(d.timeIntervalSince(date)) <= groupWindow
                }
            }
            if let target {
                groups[target].items.append(a)
            } else {
                groups.append(ExactGroup(key: key, date: a.date, items: [a]))
                byKey[key, default: []].append(groups.count - 1)
            }
        }
        var out: [Article] = groups.map { g in
            g.items.count == 1 && g.items[0].alts.isEmpty ? g.items[0] : merge(g.items)
        }
        out.sort { $0.publishedAt > $1.publishedAt }
        return out
    }
}

public extension Article {
    /// Yüklənə biləcək şəkillər, sıra ilə (app.js `imageCandidates`): xəbərin öz şəkli, sonra digər mənbələrin.
    func imageCandidates(og: [String: String] = [:]) -> [URL] {
        var values: [String] = [imageUrl, og[sourceUrl] ?? ""]
        for alt in alts {
            values.append(alt.imageUrl)
            values.append(og[alt.sourceUrl] ?? "")
        }
        var seen = Set<String>()
        var out: [URL] = []
        for raw in values where !raw.isEmpty {
            let lower = raw.lowercased()
            guard lower.hasPrefix("http://") || lower.hasPrefix("https://") else { continue }
            if lower.hasSuffix("/") || lower.hasSuffix("/resize") { continue }
            // iOS şifrəsiz bağlantını bağlayır: eyni şəkil https ilə sınanır.
            let value = lower.hasPrefix("http://") ? "https://" + String(raw.dropFirst(7)) : raw
            if seen.insert(value).inserted, let url = URL(string: value) { out.append(url) }
        }
        return out
    }
}
