import SwiftUI
import UlduzCore

private struct HomeOffsetKey: PreferenceKey {
    static var defaultValue: CGFloat { 0 }
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}

struct HomeView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router

    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $router.homePath) {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: 0) {
                        GeometryReader { geo in
                            Color.clear.preference(key: HomeOffsetKey.self, value: geo.frame(in: .named("home")).minY)
                        }
                        .frame(height: 0)
                        .id("top")

                        content
                    }
                }
                .coordinateSpace(name: "home")
                .onPreferenceChange(HomeOffsetKey.self) { value in
                    Task { @MainActor in model.homeOffsetChanged(value) }
                }
                .refreshable { await model.refresh() }
                .screenBackground()
                .overlay(alignment: .top) {
                    if model.pendingNewCount > 0 {
                        Button {
                            model.applyPending()
                            withAnimation { proxy.scrollTo("top", anchor: .top) }
                        } label: {
                            Label("\(model.pendingNewCount) yeni xəbər", systemImage: "arrow.up")
                                .font(.footnote.weight(.bold))
                                .padding(.horizontal, 14)
                                .padding(.vertical, 8)
                                .foregroundStyle(.black.opacity(0.85))
                                .background(Theme.gold, in: Capsule())
                                .shadow(radius: 6)
                        }
                        .buttonStyle(.plain)
                        .padding(.top, 8)
                        .transition(.move(edge: .top).combined(with: .opacity))
                    }
                }
                .animation(.snappy, value: model.pendingNewCount)
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Image("Logo")
                        .resizable()
                        .scaledToFit()
                        .frame(height: 22)
                        .accessibilityLabel("8ulduz")
                }
                ToolbarItem(placement: .topBarTrailing) { LanguageMenu() }
            }
            .withRoutes()
        }
    }

    @ViewBuilder
    private var content: some View {
        if model.articles.isEmpty {
            VStack(spacing: 16) {
                FeedErrorBanner()
                if model.loadFailed {
                    EmptyStateView(symbol: "wifi.slash", title: "Lent yüklənmədi", message: "İnternet bağlantınızı yoxlayıb yenidən cəhd edin.")
                } else {
                    SkeletonFeed()
                }
            }
            .padding(.top, 12)
        } else {
            LazyVStack(alignment: .leading, spacing: 22) {
                StatusLine()
                FeedErrorBanner()
                if !model.home.breaking.isEmpty { BreakingTicker(items: model.home.breaking) }
                MarketStrip()
                ServiceChips()
                HeroCarousel(items: model.home.hero)
                if !model.home.prez.isEmpty { PrezBlock(items: model.home.prez) }
                LatestBlock(items: model.home.latest)
                ForEach(model.home.sections, id: \.category.slug) { section in
                    CategoryStrip(category: section.category, items: section.articles)
                }
                VideoStrip()
                HomeFooter()
            }
            .padding(.vertical, 8)
        }
    }
}

private struct StatusLine: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        TimelineView(.periodic(from: .now, by: 30)) { context in
            // Status təzə olsa da bu ekrana yeni məlumat çatmayıbsa «indicə» yazılmasın.
            let checked = ISODate.parse(model.status?.checkedAt)
            let stale = checked.map { context.date.timeIntervalSince($0) > 5 * 60 } ?? false
            HStack(spacing: 6) {
                Text(Format.today(context.date))
                Spacer()
                if let sync = model.lastSync {
                    Circle()
                        .fill(model.isOffline || stale ? Theme.red : Theme.green)
                        .frame(width: 7, height: 7)
                    if stale {
                        Text("Xəbər lenti köhnəlib")
                    } else {
                        Text("Yeniləndi: \(Format.ago(sync, now: context.date))")
                    }
                }
            }
            .font(.caption)
            .foregroundStyle(Theme.muted)
            .padding(.horizontal, 16)
        }
    }
}

/// «Son dəqiqə» sətri. Hərəkət azaldılıbsa keçid animasiyasız olur.
private struct BreakingTicker: View {
    let items: [Article]
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var index = 0

    var body: some View {
        let current = items[min(index, items.count - 1)]
        ArticleLink(article: current) {
            HStack(spacing: 10) {
                Label("SON DƏQİQƏ", systemImage: "bolt.fill")
                    .font(.caption2.weight(.heavy))
                    .labelStyle(.titleAndIcon)
                    .foregroundStyle(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(Theme.red, in: Capsule())
                    .fixedSize()
                Text(current.cleanTitle)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .id(current.id)
                    .transition(.opacity)
            }
            .padding(10)
            .contentShape(Rectangle())
            .cardStyle()
        }
        .padding(.horizontal, 16)
        .task(id: items.map(\.id)) {
            index = 0
            guard items.count > 1 else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(5))
                if Task.isCancelled { return }
                if reduceMotion {
                    index = (index + 1) % items.count
                } else {
                    withAnimation(.easeInOut(duration: 0.35)) { index = (index + 1) % items.count }
                }
            }
        }
    }
}

struct MarketChip: View {
    let item: MarketItem
    var fills = false

    // Valyutanın bayrağı, qalanının simvolu (assets/app.js `MARKET_ICON`).
    private static let icons = ["USD": "🇺🇸", "EUR": "🇪🇺", "RUB100": "🇷🇺", "TRY100": "🇹🇷", "CNY": "🇨🇳", "BRENT": "🛢", "WTI": "🛢", "XAU": "🥇", "XAG": "🥈", "BTC": "₿"]

    private var tint: Color {
        guard item.hasChange, let pct = item.changePct, pct != 0 else { return Theme.muted }
        return pct > 0 ? Theme.green : Theme.red
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 4) {
                if let icon = Self.icons[item.id] { Text(verbatim: icon) }
                Text(ui: item.label)
            }
            .font(.caption2.weight(.semibold))
            .foregroundStyle(Theme.muted)
            .lineLimit(1)
            HStack(alignment: .firstTextBaseline, spacing: 2) {
                Text(item.valueText)
                    .font(.subheadline.weight(.bold))
                    .monospacedDigit()
                Text(item.symbol)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(Theme.gold)
            }
            .lineLimit(1)
            Group {
                if item.hasChange, let pct = item.changePct {
                    Text("\(pct > 0 ? "↑" : pct < 0 ? "↓" : "•") %\(String(format: "%.2f", abs(pct)))")
                } else {
                    Text(ui: item.unit != "AZN" ? "qiymət" : item.isUnofficial ? "bazar" : "məzənnə")
                }
            }
            .font(.caption2.weight(.semibold))
            .monospacedDigit()
            .foregroundStyle(tint)
        }
        .frame(minWidth: 84, maxWidth: fills ? .infinity : nil, alignment: .leading)
        .padding(10)
        .cardStyle()
        .accessibilityElement(children: .combine)
    }
}

private struct MarketStrip: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        if !model.markets.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(spacing: 8) {
                    ForEach(model.markets) { item in
                        NavigationLink(value: Route.markets) { MarketChip(item: item) }
                            .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
            }
        }
    }
}

private struct ServiceChips: View {
    @Environment(AppModel.self) private var model

    // Ad tərcümə olunur, dəyər (dərəcə, saat) olduğu kimi qalır.
    private func chip(_ symbol: String, _ title: String, value: String? = nil, _ route: Route, tint: Color) -> some View {
        NavigationLink(value: route) {
            HStack(spacing: 6) {
                Image(systemName: symbol).symbolRenderingMode(.multicolor).foregroundStyle(tint)
                Text(ui: title).lineLimit(1)
                if let value { Text(value).lineLimit(1) }
            }
            .font(.footnote.weight(.semibold))
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Theme.card2, in: Capsule())
            .overlay(Capsule().strokeBorder(Theme.border, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                if let w = model.weatherHere {
                    chip(w.symbol, w.city, value: "\(w.temp)°", .weather, tint: Theme.gold)
                }
                if let p = model.prayer, let next = p.next() {
                    chip("moon.stars.fill", next.label, value: next.time, .prayer, tint: Theme.green)
                }
                chip(Ranking.bakuRushHour() ? "exclamationmark.triangle.fill" : "car.fill", Ranking.bakuRushHour() ? "Pik saat" : "Tıxac", .traffic,
                     tint: Ranking.bakuRushHour() ? Theme.red : Theme.muted)
                chip("sportscourt.fill", "Futbol", .football, tint: Theme.green)
            }
            .padding(.horizontal, 16)
        }
    }
}

private struct HeroCarousel: View {
    let items: [Article]

    var body: some View {
        if !items.isEmpty {
            TabView {
                ForEach(items) { article in
                    HeroCard(article: article)
                        .padding(.horizontal, 16)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .always))
            .frame(height: 340)
        }
    }
}

/// Sahibin qərarı: blokda həmişə 44 xəbər. Şəkil kart ekrana yaxınlaşanda yüklənir.
private struct PrezBlock: View {
    let items: [Article]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Zuğulba Xronikası")
                        .font(.title3.weight(.bold))
                        .accessibilityAddTraits(.isHeader)
                    Text("Son \(items.count) xəbər")
                        .font(.caption)
                        .foregroundStyle(Theme.muted)
                }
                Spacer()
                MoreLink(route: .section("prezident"))
            }
            .padding(.horizontal, 16)
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(alignment: .top, spacing: 10) {
                    ForEach(items) { article in
                        ArticleMiniCard(article: article, tag: Ranking.isFirstLady(article) ? "Birinci xanım" : nil)
                    }
                }
                .padding(.horizontal, 16)
            }
        }
    }
}

private struct LatestBlock: View {
    let items: [Article]
    @State private var bySources = false
    @State private var count = 8

    private var ranked: [Article] { bySources ? Ranking.rankBySources(items) : items }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeader(title: "Son xəbərlər")
            Picker("Sıralama", selection: $bySources) {
                Text("Ən yeni").tag(false)
                Text("Ən çox mənbədə").tag(true)
            }
            .pickerStyle(.segmented)
            let list = ranked
            ForEach(list.prefix(count)) { article in
                ArticleRow(article: article)
            }
            if list.count > count {
                Button {
                    count += 12
                } label: {
                    Text("Daha çox xəbər")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Theme.card2, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 16)
    }
}

private struct CategoryStrip: View {
    let category: NewsCategory
    let items: [Article]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionHeader(title: category.label) {
                MoreLink(route: .section(category.slug))
            }
            .padding(.horizontal, 16)
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(alignment: .top, spacing: 10) {
                    ForEach(items) { ArticleMiniCard(article: $0) }
                }
                .padding(.horizontal, 16)
            }
        }
    }
}

struct VideoCard: View {
    let item: VideoItem
    var width: CGFloat? = 216

    var body: some View {
        Button {
            if let url = item.watchURL { Browser.open(url) }
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                RemoteImage(urls: [item.imageUrl].compactMap { TextTools.webURL($0) }, category: "video", maxPixel: 520)
                    .aspectRatio(16 / 9, contentMode: .fit)
                    .overlay {
                        Image(systemName: "play.circle.fill")
                            .font(.largeTitle)
                            .foregroundStyle(.white, .black.opacity(0.45))
                    }
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.channel)
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(Theme.gold)
                    Text(item.title)
                        .font(.footnote.weight(.semibold))
                        .multilineTextAlignment(.leading)
                        .lineLimit(3)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(.horizontal, 10)
                .padding(.bottom, 10)
            }
            .frame(width: width)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .cardStyle()
        }
        .buttonStyle(.plain)
    }
}

private struct VideoStrip: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        if !model.videoItems.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                SectionHeader(title: "Video xəbərlər") {
                    MoreLink(route: .videos)
                }
                .padding(.horizontal, 16)
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(alignment: .top, spacing: 10) {
                        ForEach(model.videoItems.prefix(8)) { VideoCard(item: $0) }
                    }
                    .padding(.horizontal, 16)
                }
            }
        }
    }
}

private struct HomeFooter: View {
    var body: some View {
        VStack(spacing: 8) {
            Text("Xəbər mətnlərinin hüququ müvafiq mənbələrə aiddir.")
                .font(.caption)
                .foregroundStyle(Theme.muted)
            NavigationLink(value: Route.about) {
                Text("Haqqımızda")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Theme.gold)
            }
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
    }
}
