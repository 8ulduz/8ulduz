import ImageIO
import SwiftUI
import UIKit
import UlduzCore

// MARK: - Şəkillər

/// Mənbə şəkilləri: hotlink qadağası və sınıq keçid adi haldır, ona görə növbəti namizəd sınanır, sonda loqo qalır.
final class ImageLoader: @unchecked Sendable {
    static let shared = ImageLoader()
    private let memory = NSCache<NSURL, UIImage>()
    private let session: URLSession

    private init() {
        memory.totalCostLimit = 96 * 1024 * 1024
        let config = URLSessionConfiguration.default
        config.urlCache = URLCache.shared
        config.requestCachePolicy = .returnCacheDataElseLoad
        config.httpCookieStorage = nil
        config.httpShouldSetCookies = false
        config.timeoutIntervalForRequest = 15
        session = URLSession(configuration: config)
    }

    func clear() { memory.removeAllObjects() }

    func cached(_ urls: [URL]) -> UIImage? {
        for url in urls {
            if let hit = memory.object(forKey: url as NSURL) { return hit }
        }
        return nil
    }

    func load(_ urls: [URL], maxPixel: CGFloat) async -> UIImage? {
        for url in urls {
            if Task.isCancelled { return nil }
            if let hit = memory.object(forKey: url as NSURL) { return hit }
            guard let (data, response) = try? await session.data(from: url),
                  let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode),
                  let image = Self.downsample(data, maxPixel: maxPixel) else { continue }
            let cost = (image.cgImage?.bytesPerRow ?? 0) * (image.cgImage?.height ?? 0)
            memory.setObject(image, forKey: url as NSURL, cost: cost)
            return image
        }
        return nil
    }

    private static func downsample(_ data: Data, maxPixel: CGFloat) -> UIImage? {
        let sourceOptions = [kCGImageSourceShouldCache: false] as CFDictionary
        guard let source = CGImageSourceCreateWithData(data as CFData, sourceOptions) else { return nil }
        let options = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceThumbnailMaxPixelSize: maxPixel,
        ] as CFDictionary
        guard let image = CGImageSourceCreateThumbnailAtIndex(source, 0, options) else { return nil }
        return UIImage(cgImage: image)
    }
}

struct RemoteImage: View {
    let urls: [URL]
    var category: String = "gundem"
    var maxPixel: CGFloat = 900

    @State private var image: UIImage?
    @State private var finished = false

    var body: some View {
        Color.clear
            .overlay {
                if let image {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFill()
                        .transition(.opacity)
                } else {
                    ImagePlaceholder(category: category, loading: !finished)
                }
            }
            .clipped()
            .task(id: urls) {
                if let hit = ImageLoader.shared.cached(urls) {
                    image = hit
                    return
                }
                image = nil
                finished = false
                let loaded = await ImageLoader.shared.load(urls, maxPixel: maxPixel)
                if Task.isCancelled { return }
                withAnimation(.easeOut(duration: 0.2)) {
                    image = loaded
                    finished = true
                }
            }
            .accessibilityHidden(true)
    }
}

struct ImagePlaceholder: View {
    let category: String
    var loading = false

    var body: some View {
        ZStack {
            LinearGradient(colors: [Theme.color(forCategory: category).opacity(0.28), Theme.card2], startPoint: .topLeading, endPoint: .bottomTrailing)
            if !loading {
                Image(systemName: Catalog.category(category)?.symbol ?? "newspaper.fill")
                    .font(.title2)
                    .foregroundStyle(Theme.color(forCategory: category).opacity(0.7))
            }
        }
    }
}

// MARK: - Xəbər elementləri

struct Pill: View {
    let text: String
    var color: Color = Theme.muted
    var filled = false

    var body: some View {
        Text(text)
            .font(.caption2.weight(.bold))
            .lineLimit(1)
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .foregroundStyle(filled ? Color.black.opacity(0.85) : color)
            .background(filled ? color : color.opacity(0.14), in: Capsule())
    }
}

struct ArticleBadges: View {
    @Environment(AppModel.self) private var model
    let article: Article
    var showCategory = true

    var body: some View {
        HStack(spacing: 5) {
            if article.isFresh { Pill(text: "SON DƏQİQƏ", color: Theme.red, filled: true) }
            if showCategory { Pill(text: Catalog.label(article.category), color: Theme.color(forCategory: article.category)) }
            if article.sourceCount > 1 { Pill(text: "\(article.sourceCount) MƏNBƏ", color: Theme.gold, filled: true) }
            if article.video { Pill(text: "▶ VİDEO", color: Theme.red) }
            if model.language.isEmpty, let badge = Catalog.languages.first(where: { $0.code == article.language })?.badge {
                Pill(text: badge)
            }
        }
    }
}

struct ArticleMeta: View {
    let article: Article

    var body: some View {
        HStack(spacing: 6) {
            Text(article.shownSource)
                .fontWeight(.semibold)
                .lineLimit(1)
            Spacer(minLength: 4)
            Text(Format.ago(article.date))
                .lineLimit(1)
                .monospacedDigit()
        }
        .font(.caption)
        .foregroundStyle(Theme.muted)
    }
}

struct StarButton: View {
    @Environment(AppModel.self) private var model
    let article: Article
    var compact = false

    var body: some View {
        let on = model.isSaved(article)
        Button {
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
            model.toggleSave(article)
        } label: {
            Image(systemName: on ? "star.fill" : "star")
                .font(compact ? .footnote.weight(.semibold) : .subheadline.weight(.semibold))
                .foregroundStyle(on ? Theme.gold : .white)
                .frame(width: compact ? 30 : 34, height: compact ? 30 : 34)
                .background(.black.opacity(0.45), in: Circle())
                .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(on ? "Saxlanmışlardan çıxar" : "Yadda saxla")
    }
}

/// Karta toxunanda: önizləmə ekranı və ya (Tənzimləmələrdə seçilibsə) birbaşa mənbə.
struct ArticleLink<Content: View>: View {
    @Environment(AppModel.self) private var model
    let article: Article
    @ViewBuilder var content: () -> Content

    var body: some View {
        Group {
            if model.opensSourceDirectly {
                Button { Browser.open(article.sourceUrl, reader: model.opensInReaderMode) } label: { content() }
            } else {
                NavigationLink(value: Route.article(article)) { content() }
            }
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button {
                Browser.open(article.sourceUrl, reader: model.opensInReaderMode)
            } label: {
                Label("Mənbədə oxu", systemImage: "safari")
            }
            Button {
                model.toggleSave(article)
            } label: {
                model.isSaved(article)
                    ? Label("Saxlanmışlardan çıxar", systemImage: "star.slash")
                    : Label("Yadda saxla", systemImage: "star")
            }
            if let url = TextTools.webURL(article.sourceUrl) {
                ShareLink(item: url, subject: Text(article.cleanTitle), message: Text(article.cleanTitle)) {
                    Label("Paylaş", systemImage: "square.and.arrow.up")
                }
            }
        }
    }
}

/// Siyahı kartı: solda şəkil, sağda başlıq.
struct ArticleRow: View {
    @Environment(AppModel.self) private var model
    let article: Article
    var showCategory = true

    var body: some View {
        ArticleLink(article: article) {
            HStack(alignment: .top, spacing: 12) {
                RemoteImage(urls: article.imageCandidates(og: model.og), category: article.category, maxPixel: 420)
                    .frame(width: 104, height: 92)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                VStack(alignment: .leading, spacing: 6) {
                    Text(article.cleanTitle)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                        .multilineTextAlignment(.leading)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                    ArticleBadges(article: article, showCategory: showCategory)
                        .fixedSize()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .clipped()
                    ArticleMeta(article: article)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(10)
            .contentShape(Rectangle())
            .cardStyle()
        }
        .overlay(alignment: .topLeading) {
            StarButton(article: article, compact: true).padding(14)
        }
    }
}

/// Üfüqi zolaq kartı.
struct ArticleMiniCard: View {
    @Environment(AppModel.self) private var model
    let article: Article

    var body: some View {
        ArticleLink(article: article) {
            VStack(alignment: .leading, spacing: 8) {
                RemoteImage(urls: article.imageCandidates(og: model.og), category: article.category, maxPixel: 520)
                    .frame(height: 118)
                    .frame(maxWidth: .infinity)
                    .clipped()
                VStack(alignment: .leading, spacing: 6) {
                    Text(article.cleanTitle)
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(.primary)
                        .multilineTextAlignment(.leading)
                        .lineLimit(3)
                        .frame(maxWidth: .infinity, minHeight: 54, alignment: .topLeading)
                    ArticleMeta(article: article)
                }
                .padding(.horizontal, 10)
                .padding(.bottom, 10)
            }
            .frame(width: 216)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .cardStyle()
        }
    }
}

/// Karusel kartı: şəkil üzərində başlıq.
struct HeroCard: View {
    @Environment(AppModel.self) private var model
    let article: Article

    var body: some View {
        ArticleLink(article: article) {
            RemoteImage(urls: article.imageCandidates(og: model.og), category: article.category, maxPixel: 1200)
                .overlay {
                    LinearGradient(colors: [.clear, .black.opacity(0.88)], startPoint: .center, endPoint: .bottom)
                }
                .overlay(alignment: .bottomLeading) {
                    VStack(alignment: .leading, spacing: 8) {
                        ArticleBadges(article: article, showCategory: false)
                        Text(article.cleanTitle)
                            .font(.title3.weight(.bold))
                            .foregroundStyle(.white)
                            .multilineTextAlignment(.leading)
                            .lineLimit(4)
                            .shadow(radius: 4)
                        HStack(spacing: 6) {
                            Text(article.shownSource).fontWeight(.semibold)
                            Text(Format.ago(article.date))
                        }
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.85))
                    }
                    .padding(16)
                    .padding(.bottom, 22)
                }
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                .contentShape(Rectangle())
        }
        .overlay(alignment: .topTrailing) {
            StarButton(article: article).padding(10)
        }
        .accessibilityElement(children: .contain)
    }
}

// MARK: - Ümumi bloklar

struct SectionHeader<Trailing: View>: View {
    let title: String
    var subtitle: String?
    @ViewBuilder var trailing: () -> Trailing

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.title3.weight(.bold))
                    .accessibilityAddTraits(.isHeader)
                if let subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(Theme.muted)
                }
            }
            Spacer()
            trailing()
        }
    }
}

extension SectionHeader where Trailing == EmptyView {
    init(title: String, subtitle: String? = nil) {
        self.init(title: title, subtitle: subtitle) { EmptyView() }
    }
}

struct MoreLink: View {
    var title = "Hamısı"
    let route: Route

    var body: some View {
        NavigationLink(value: route) {
            HStack(spacing: 2) {
                Text(title)
                Image(systemName: "chevron.right").font(.caption2.weight(.bold))
            }
            .font(.footnote.weight(.semibold))
            .foregroundStyle(Theme.gold)
        }
        .buttonStyle(.plain)
    }
}

struct EmptyStateView: View {
    let symbol: String
    let title: String
    var message: String?

    var body: some View {
        ContentUnavailableView {
            Label(title, systemImage: symbol)
        } description: {
            if let message { Text(message) }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 40)
    }
}

/// Yüklənmə yeri tutucusu (saytın `skeleton`).
struct SkeletonFeed: View {
    var body: some View {
        VStack(spacing: 14) {
            RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Theme.card2).frame(height: 300)
            ForEach(0..<5, id: \.self) { _ in
                RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Theme.card2).frame(height: 112)
            }
        }
        .padding(.horizontal, 16)
        .accessibilityLabel("Xəbərlər yüklənir")
    }
}

struct FeedErrorBanner: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        if model.loadFailed || model.isOffline {
            HStack(spacing: 10) {
                Image(systemName: "wifi.exclamationmark").foregroundStyle(Theme.red)
                Text(model.articles.isEmpty
                     ? "Xəbər lenti yüklənə bilmədi. İnternet bağlantınızı yoxlayın."
                     : "Son yenilənmə alınmadı. Saxlanmış xəbərlər göstərilir.")
                    .font(.footnote)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Button("Yenidən") { Task { await model.refresh() } }
                    .font(.footnote.weight(.semibold))
            }
            .padding(12)
            .cardStyle()
            .padding(.horizontal, 16)
        }
    }
}

extension League {
    var isBasketball: Bool { sport == "basketball" }
}

/// Dil menyusu: ana səhifə və bölmələrin alətlər sətrində.
struct LanguageMenu: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        Menu {
            Picker("Xəbərlərin dili", selection: $model.language) {
                Text("Bütün dillər").tag("")
                ForEach(Catalog.languages) { Text($0.label).tag($0.code) }
            }
        } label: {
            Text(Catalog.languages.first { $0.code == model.language }?.badge ?? "Hamısı")
                .font(.footnote.weight(.bold))
                .foregroundStyle(Theme.gold)
        }
        .accessibilityLabel("Xəbərlərin dili")
    }
}
