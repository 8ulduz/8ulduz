import ImageIO
import SwiftUI
import UIKit
import UlduzCore
import WidgetKit

@main
struct UlduzWidgetBundle: WidgetBundle {
    var body: some Widget {
        HeadlinesWidget()
        MarketsWidget()
    }
}

private enum Brand {
    static let background = Color(red: 0.03, green: 0.04, blue: 0.08)
    static let gold = Color(red: 0.98, green: 0.74, blue: 0.14)
    static let muted = Color.white.opacity(0.62)
    static let green = Color(red: 0.06, green: 0.73, blue: 0.51)
    static let red = Color(red: 0.94, green: 0.27, blue: 0.27)
}

/// Yeniləmə vaxtına iOS qərar verir (təxminən 15 dəqiqədən bir). Dəqiqəlik axın tətbiqin özündədir.
private enum WidgetData {
    static let refreshEvery: TimeInterval = 15 * 60

    static func headlines() async -> [Article] {
        let client = FeedClient()
        var policy = ContentPolicy.bundled()
        if let cached = await client.cachedPolicy() { policy = cached }
        let list: [Article]
        if let loaded = try? await client.load("latest.json", as: NewsFeed.self) {
            list = loaded.value.articles
        } else {
            let cached: NewsFeed? = await client.cached("news.json")
            list = cached?.articles ?? []
        }
        let language = DiskStore.shared.read("language").flatMap { String(data: $0, encoding: .utf8) } ?? "az"
        return Ranking.byDate(Ranking.filtered(policy.clean(list), language: language.isEmpty ? nil : language))
    }

    static func markets() async -> [MarketItem] {
        let client = FeedClient()
        return (try? await client.load("markets.json", as: MarketsFeed.self))?.value.items ?? []
    }

    /// Vidcet şəkli şəbəkədən özü yükləyə bilmir: kiçildilmiş nüsxə qrafikə qoyulur.
    static func image(for article: Article?) async -> UIImage? {
        guard let article else { return nil }
        for url in article.imageCandidates().prefix(3) {
            var request = URLRequest(url: url)
            request.timeoutInterval = 6
            guard let (data, response) = try? await URLSession.shared.data(for: request),
                  (response as? HTTPURLResponse)?.statusCode == 200,
                  let source = CGImageSourceCreateWithData(data as CFData, nil) else { continue }
            let options = [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceCreateThumbnailWithTransform: true,
                kCGImageSourceThumbnailMaxPixelSize: 520,
            ] as CFDictionary
            if let cg = CGImageSourceCreateThumbnailAtIndex(source, 0, options) { return UIImage(cgImage: cg) }
        }
        return nil
    }

    static func link(_ article: Article) -> URL {
        var parts = URLComponents()
        parts.scheme = "ulduz8"
        parts.host = "xeber"
        parts.path = "/" + article.id
        parts.queryItems = [URLQueryItem(name: "u", value: article.sourceUrl)]
        return parts.url ?? URL(string: "ulduz8://home")!
    }
}

// MARK: - Son xəbərlər

struct HeadlinesEntry: TimelineEntry {
    let date: Date
    let articles: [Article]
    let image: UIImage?
}

struct HeadlinesProvider: TimelineProvider {
    private static var sample: [Article] {
        (1...6).map {
            Article(id: "\($0)", title: "Son xəbərin başlığı burada görünəcək", source: "8ulduz", sourceUrl: "https://8ulduz.az/", publishedAt: ISO8601DateFormatter().string(from: Date()))
        }
    }

    func placeholder(in context: Context) -> HeadlinesEntry {
        HeadlinesEntry(date: Date(), articles: Self.sample, image: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (HeadlinesEntry) -> Void) {
        if context.isPreview {
            completion(placeholder(in: context))
            return
        }
        Task { completion(await entry(family: context.family)) }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<HeadlinesEntry>) -> Void) {
        Task {
            let current = await entry(family: context.family)
            completion(Timeline(entries: [current], policy: .after(Date().addingTimeInterval(WidgetData.refreshEvery))))
        }
    }

    private func entry(family: WidgetFamily) async -> HeadlinesEntry {
        let list = await WidgetData.headlines()
        let wantsImage = family == .systemSmall || family == .systemMedium || family == .systemLarge
        let image = wantsImage ? await WidgetData.image(for: list.first) : nil
        return HeadlinesEntry(date: Date(), articles: Array(list.prefix(6)), image: image)
    }
}

private struct HeadlineLine: View {
    let article: Article

    var body: some View {
        Link(destination: WidgetData.link(article)) {
            VStack(alignment: .leading, spacing: 2) {
                Text(article.cleanTitle)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text("\(article.shownSource) · \(Format.ago(article.date))")
                    .font(.caption2)
                    .foregroundStyle(Brand.muted)
                    .lineLimit(1)
            }
        }
    }
}

private struct BrandHeader: View {
    var body: some View {
        HStack(spacing: 4) {
            Image("Mark")
                .resizable()
                .frame(width: 16, height: 16)
                .clipShape(RoundedRectangle(cornerRadius: 4))
            Text("Son xəbərlər")
                .font(.caption2.weight(.heavy))
                .foregroundStyle(Brand.gold)
            Spacer(minLength: 0)
        }
    }
}

struct HeadlinesWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: HeadlinesEntry

    var body: some View {
        switch family {
        case .accessoryInline:
            Text(entry.articles.first?.cleanTitle ?? "8ulduz")
                .widgetURL(entry.articles.first.map(WidgetData.link))
        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 1) {
                Text("8ulduz").font(.caption2.weight(.bold))
                Text(entry.articles.first?.cleanTitle ?? "Xəbərlər yüklənir")
                    .font(.caption)
                    .lineLimit(3)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .widgetURL(entry.articles.first.map(WidgetData.link))
        case .systemSmall:
            small
        case .systemLarge:
            large
        default:
            medium
        }
    }

    private var empty: some View {
        Text("Xəbərlər yüklənir")
            .font(.caption)
            .foregroundStyle(Brand.muted)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var small: some View {
        VStack(alignment: .leading, spacing: 6) {
            BrandHeader()
            if let first = entry.articles.first {
                Text(first.cleanTitle)
                    .font(.footnote.weight(.bold))
                    .foregroundStyle(.white)
                    .lineLimit(5)
                Spacer(minLength: 0)
                Text(Format.ago(first.date))
                    .font(.caption2)
                    .foregroundStyle(Brand.muted)
            } else {
                empty
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .widgetURL(entry.articles.first.map(WidgetData.link))
    }

    private var medium: some View {
        HStack(alignment: .top, spacing: 10) {
            if let image = entry.image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(width: 96)
                    .frame(maxHeight: .infinity)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
            VStack(alignment: .leading, spacing: 6) {
                BrandHeader()
                if entry.articles.isEmpty { empty }
                ForEach(entry.articles.prefix(2)) { HeadlineLine(article: $0) }
                Spacer(minLength: 0)
            }
        }
    }

    private var large: some View {
        VStack(alignment: .leading, spacing: 8) {
            BrandHeader()
            if let image = entry.image, let first = entry.articles.first {
                Link(destination: WidgetData.link(first)) {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFill()
                        .frame(height: 110)
                        .frame(maxWidth: .infinity)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
            if entry.articles.isEmpty { empty }
            ForEach(entry.articles.prefix(entry.image == nil ? 6 : 4)) { HeadlineLine(article: $0) }
            Spacer(minLength: 0)
        }
    }
}

struct HeadlinesWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "az.ulduz8.headlines", provider: HeadlinesProvider()) { entry in
            HeadlinesWidgetView(entry: entry)
                .containerBackground(for: .widget) { Brand.background }
        }
        .configurationDisplayName("Son xəbərlər")
        .description("Lentin ən son xəbərləri.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge, .accessoryRectangular, .accessoryInline])
    }
}

// MARK: - Bazar

struct MarketsEntry: TimelineEntry {
    let date: Date
    let items: [MarketItem]
}

struct MarketsProvider: TimelineProvider {
    private static var sample: [MarketItem] {
        [
            MarketItem(id: "USD", label: "Dollar", unit: "AZN", dec: 4, value: 1.7),
            MarketItem(id: "EUR", label: "Avro", unit: "AZN", dec: 4, value: 1.9),
            MarketItem(id: "BRENT", label: "Brent", unit: "USD", dec: 2, value: 70),
            MarketItem(id: "XAU", label: "Qızıl", unit: "USD", dec: 1, value: 3000),
        ]
    }

    func placeholder(in context: Context) -> MarketsEntry { MarketsEntry(date: Date(), items: Self.sample) }

    func getSnapshot(in context: Context, completion: @escaping (MarketsEntry) -> Void) {
        if context.isPreview {
            completion(placeholder(in: context))
            return
        }
        Task { completion(MarketsEntry(date: Date(), items: await WidgetData.markets())) }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<MarketsEntry>) -> Void) {
        Task {
            let current = MarketsEntry(date: Date(), items: await WidgetData.markets())
            completion(Timeline(entries: [current], policy: .after(Date().addingTimeInterval(WidgetData.refreshEvery))))
        }
    }
}

private struct MarketLine: View {
    let item: MarketItem

    private var tint: Color {
        guard item.hasChange, let pct = item.changePct, pct != 0 else { return Brand.muted }
        return pct > 0 ? Brand.green : Brand.red
    }

    var body: some View {
        HStack(spacing: 4) {
            Text(item.label)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(Brand.muted)
                .lineLimit(1)
            Spacer(minLength: 2)
            Text("\(item.valueText) \(item.symbol)")
                .font(.caption.weight(.bold))
                .foregroundStyle(.white)
                .monospacedDigit()
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Circle().fill(tint).frame(width: 5, height: 5)
        }
    }
}

struct MarketsWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: MarketsEntry

    var body: some View {
        Group {
            if family == .accessoryRectangular {
                VStack(alignment: .leading, spacing: 1) {
                    ForEach(entry.items.prefix(3)) { item in
                        Text("\(item.label) \(item.valueText)\(item.symbol)")
                            .font(.caption2.weight(.semibold))
                            .lineLimit(1)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 4) {
                        Image("Mark")
                            .resizable()
                            .frame(width: 16, height: 16)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                        Text("Bazar")
                            .font(.caption2.weight(.heavy))
                            .foregroundStyle(Brand.gold)
                    }
                    if entry.items.isEmpty {
                        Text("Məlumat yüklənir")
                            .font(.caption)
                            .foregroundStyle(Brand.muted)
                    }
                    if family == .systemSmall {
                        ForEach(entry.items.prefix(5)) { MarketLine(item: $0) }
                    } else {
                        LazyVGrid(columns: [GridItem(.flexible(), spacing: 14), GridItem(.flexible())], spacing: 7) {
                            ForEach(entry.items.prefix(8)) { MarketLine(item: $0) }
                        }
                    }
                    Spacer(minLength: 0)
                }
            }
        }
        .widgetURL(URL(string: "ulduz8://bazar"))
    }
}

struct MarketsWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "az.ulduz8.markets", provider: MarketsProvider()) { entry in
            MarketsWidgetView(entry: entry)
                .containerBackground(for: .widget) { Brand.background }
        }
        .configurationDisplayName("Bazar")
        .description("Valyuta, neft, qızıl və gümüş.")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular])
    }
}
