import Observation
import SwiftUI
import UlduzCore
import WidgetKit

/// Ana səhifənin hazır blokları: hər yenilənmədə arxa planda bir dəfə hesablanır.
struct HomeContent: Sendable {
    var breaking: [Article] = []
    var hero: [Article] = []
    var prez: [Article] = []
    var latest: [Article] = []
    var sections: [(category: NewsCategory, articles: [Article])] = []
    var videos: [Article] = []

    static func build(_ all: [Article], language: String, sectionOrder: [String], sectionsOff: Set<String>, now: Date = Date()) -> HomeContent {
        let lang = language.isEmpty ? nil : language
        let m = Ranking.filtered(all, language: lang)
        let hero = Ranking.heroPick(m.filter { $0.category != "prezident" }, need: Ranking.heroCount, now: now)
        let used = Set(hero.prefix(Ranking.heroOnly).map(\.id))
        let remaining = m.filter { !used.contains($0.id) && $0.category != "prezident" }
        var sections: [(category: NewsCategory, articles: [Article])] = []
        for slug in sectionOrder where !sectionsOff.contains(slug) {
            guard let category = Catalog.category(slug) else { continue }
            // İdman bütün dillərdə göstərilir: dil süzgəci bu bölməyə tətbiq edilmir.
            let list = (slug == "idman" ? all : remaining).filter { $0.category == slug }
            if !list.isEmpty { sections.append((category, Array(list.prefix(12)))) }
        }
        return HomeContent(
            breaking: Array(m.filter { $0.isWithinHour(now: now) }.prefix(12)),
            hero: hero,
            prez: Ranking.prezHome(m, now: now),
            latest: remaining,
            sections: sections,
            videos: Array(m.filter(\.video).prefix(15))
        )
    }
}

enum ThemeChoice: String, CaseIterable, Identifiable {
    case system, dark, light
    var id: String { rawValue }
    var label: String {
        switch self {
        case .system: return "Telefon kimi"
        case .dark: return "Qaranlıq"
        case .light: return "İşıqlı"
        }
    }
    var scheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .dark: return .dark
        case .light: return .light
        }
    }
}

private enum Key {
    static let language = "8ulduz-lang"
    static let theme = "8ulduz-theme"
    static let city = "8ulduz-city"
    static let direct = "8ulduz-direct"
    static let reader = "8ulduz-reader"
    static let notify = "8ulduz-notify"
    static let order = "8ulduz-sects-order"
    static let off = "8ulduz-sects-off"
    static let saved = "8ulduz-saved"
    static let recent = "8ulduz-recent"
}

@MainActor
@Observable
final class AppModel {
    // QIRMIZI XƏTT 1: lent dəqiqədə bir yazılır, tətbiq saytla eyni 30 saniyədən bir yoxlayır (assets/app.js POLL_MS).
    static let pollInterval: Duration = .seconds(30)
    private static let fullFeedEvery: TimeInterval = 10 * 60
    private static let secondaryEvery: TimeInterval = 5 * 60
    private static let sportsEvery: TimeInterval = 30 * 60
    private static let weatherEvery: TimeInterval = 30 * 60
    private static let policyEvery: TimeInterval = 6 * 3600
    private static let widgetEvery: TimeInterval = 15 * 60
    private static let latestEvery: TimeInterval = 90
    private static let overlayKeep: TimeInterval = 30 * 60
    private static let archiveEvery: TimeInterval = 30 * 60
    private static let noArchive: Set<String> = ["video", "sondeqiqe", "prezident"]
    private static let holdOffset: CGFloat = -400

    // Lent
    private(set) var articles: [Article] = []
    private(set) var home = HomeContent()
    private(set) var isFirstLoadDone = false
    private(set) var loadFailed = false
    private(set) var isOffline = false
    private(set) var lastSync: Date?
    private(set) var pendingNewCount = 0
    private(set) var status: FeedStatus?

    // Digər məlumat
    private(set) var markets: [MarketItem] = []
    private(set) var videoItems: [VideoItem] = []
    private(set) var socialPosts: [SocialPost] = []
    private(set) var sourceRows: [SourceStatus] = []
    private(set) var leagues: [League] = []
    private(set) var weatherHere: WeatherNow?
    private(set) var weatherAll: [WeatherNow] = []
    private(set) var prayer: PrayerDay?
    private(set) var og: [String: String] = [:]
    private(set) var saved: [Article] = []
    private(set) var recentSearches: [String] = []
    private(set) var archives: [String: [Article]] = [:]
    @ObservationIgnored let teams = TeamStore()

    // Seçimlər
    var language: String {
        didSet {
            store(language, Key.language)
            Format.language = interfaceLanguage
            shareLanguage()
            rebuildHome()
        }
    }
    var theme: ThemeChoice { didSet { store(theme.rawValue, Key.theme) } }
    var cityName: String { didSet { store(cityName, Key.city); Task { await loadCityServices() } } }
    var opensSourceDirectly: Bool { didSet { store(opensSourceDirectly, Key.direct) } }
    var opensInReaderMode: Bool { didSet { store(opensInReaderMode, Key.reader) } }
    private(set) var notificationsOn: Bool
    private(set) var sectionOrder: [String]
    private(set) var sectionsOff: Set<String>

    @ObservationIgnored private let client = FeedClient()
    @ObservationIgnored private var policy: ContentPolicy = .bundled()
    @ObservationIgnored private var football: [League] = []
    @ObservationIgnored private var sports: [League] = []
    @ObservationIgnored private var rawNews: [Article] = []
    @ObservationIgnored private var feedUpdatedAt: String?
    /// Dəqiqəlik gələn xəbərlər: main 10 dəqiqədən bir yazılır, tam lentdə hələ olmaya bilərlər, itməsinlər.
    @ObservationIgnored private var overlay: [(article: Article, at: Date)] = []
    @ObservationIgnored private var deadLinks: Set<String> = []
    @ObservationIgnored private var isPartial = false
    @ObservationIgnored private var publishToken = 0
    @ObservationIgnored private var latestAt = Date.distantPast
    @ObservationIgnored private var archiveAt: [String: Date] = [:]
    @ObservationIgnored private var newsStamp: String?
    @ObservationIgnored private var newsCheckedAt = Date.distantPast
    @ObservationIgnored private var ogLoadedAt = Date.distantPast
    @ObservationIgnored private var secondaryAt = Date.distantPast
    @ObservationIgnored private var sportsAt = Date.distantPast
    @ObservationIgnored private var weatherAt = Date.distantPast
    @ObservationIgnored private var policyAt = Date.distantPast
    @ObservationIgnored private var widgetsAt = Date.distantPast
    @ObservationIgnored private var polling = false
    @ObservationIgnored private var started = false
    @ObservationIgnored private var holdingUpdates = false
    @ObservationIgnored private var pendingArticles: [Article]?
    @ObservationIgnored private var pendingHome: HomeContent?

    init() {
        let d = UserDefaults.standard
        language = d.object(forKey: Key.language) == nil ? "az" : (d.string(forKey: Key.language) ?? "az")
        theme = ThemeChoice(rawValue: d.string(forKey: Key.theme) ?? "") ?? .system
        cityName = d.string(forKey: Key.city) ?? "Bakı"
        opensSourceDirectly = d.bool(forKey: Key.direct)
        opensInReaderMode = d.bool(forKey: Key.reader)
        notificationsOn = d.bool(forKey: Key.notify)
        let known = Catalog.orderableSlugs
        var order = (d.stringArray(forKey: Key.order) ?? known).filter { known.contains($0) }
        for slug in known where !order.contains(slug) { order.append(slug) }
        sectionOrder = order
        sectionsOff = Set(d.stringArray(forKey: Key.off) ?? [])
        recentSearches = d.stringArray(forKey: Key.recent) ?? []
        if let data = d.data(forKey: Key.saved), let list = try? JSONDecoder().decode([Article].self, from: data) {
            saved = list
        }
        Format.language = interfaceLanguage
        shareLanguage()
    }

    /// Sayt seçilən dildə açılır (assets/dil.js). Xəbər mətni tərcümə olunmur; «Bütün dillər» azərbaycanca qalır.
    var interfaceLanguage: String { ["ru", "tr", "en"].contains(language) ? language : "az" }

    private func store(_ value: Any, _ key: String) { UserDefaults.standard.set(value, forKey: key) }

    /// Vidcet də eyni dildə göstərsin.
    private func shareLanguage() { DiskStore.shared.write(Data(language.utf8), to: "language") }

    var city: City { Catalog.cities.first { $0.name == cityName } ?? Catalog.cities[0] }

    // MARK: - Açılış və dövrə

    /// Keşdəki son lent dərhal ekrana çıxır, sonra şəbəkə yoxlanır.
    func start() async {
        guard !started else { return }
        started = true
        if let cachedRules = await client.cachedPolicy() { policy = cachedRules }
        if let cachedOg: OgImages = await client.cached("og.json") { og = cachedOg.images }
        if let cached: NewsFeed = await client.cached("latest.json") { deadLinks = Set(cached.dead) }
        if let cached: NewsFeed = await client.cached("news.json") {
            rawNews = cached.articles
            feedUpdatedAt = cached.updatedAt
            await publish()
        }
        if let cached: MarketsFeed = await client.cached("markets.json") { markets = cached.items }
        if let cached: FootballFeed = await client.cached("football.json") { football = cached.leagues }
        if let cached: SportsFeed = await client.cached("sports.json") { sports = cached.leagues }
        leagues = football + sports
    }

    /// Tətbiq önəndə işləyir. Arxa planda məlumat xərclənmir, qayıdanda dərhal yoxlanır.
    func foregroundLoop() async {
        await start()
        await refreshPolicyIfDue()
        await poll(force: true)
        await loadSecondaryIfDue()
        while !Task.isCancelled {
            try? await Task.sleep(for: Self.pollInterval)
            if Task.isCancelled { break }
            await poll()
            await loadSecondaryIfDue()
        }
    }

    func refresh() async {
        await poll(force: true)
        secondaryAt = .distantPast
        await loadSecondaryIfDue()
    }

    // Dəqiqəlik yoxlama yüngül status.json ilə gedir; news.json yalnız lazım olanda çəkilir (assets/app.js `pollNews`).
    private func poll(force: Bool = false) async {
        guard !polling else { return }
        polling = true
        defer { polling = false }
        if let loaded = try? await client.load("status.json", as: FeedStatus.self, force: force) {
            status = loaded.value
        }
        let stamp = status?.checkedAt
        let fullDue = Date().timeIntervalSince(newsCheckedAt) >= Self.fullFeedEvery
        if force || articles.isEmpty || loadFailed || stamp == nil || fullDue {
            // İlk açılışda keş boşdur: ekran 100 xəbərlik yüngül fayldan dolur, tam lent arxada gəlir.
            async let first: Void = loadFirst()
            await loadNews(force: force)
            await first
            await loadLatest(force: force)
        } else if stamp != newsStamp || Date().timeIntervalSince(latestAt) >= Self.latestEvery {
            await loadLatest(force: false)
        }
    }

    private func loadFirst() async {
        guard rawNews.isEmpty, language == "az",
              let loaded = try? await client.load("first.json", as: NewsFeed.self),
              rawNews.isEmpty, !loaded.value.articles.isEmpty else { return }
        if og.isEmpty { og = loaded.value.og }
        rawNews = loaded.value.articles
        isPartial = true
        await publish()
    }

    private func loadNews(force: Bool) async {
        let stamp = status?.checkedAt
        do {
            let loaded = try await client.load("news.json", as: NewsFeed.self, force: force)
            if Task.isCancelled { return }
            noteOrigin(loaded.origin)
            loadFailed = false
            newsStamp = stamp
            newsCheckedAt = Date()
            await loadOgIfDue()
            if loaded.value.updatedAt == feedUpdatedAt && !isPartial && !rawNews.isEmpty && !articles.isEmpty { return }
            let inFull = NewsPipeline.knownLinks(loaded.value.articles)
            let now = Date()
            overlay = overlay.filter { !inFull.contains($0.article.sourceUrl) && now.timeIntervalSince($0.at) < Self.overlayKeep }
            rawNews = overlay.map { $0.article } + loaded.value.articles
            isPartial = false
            feedUpdatedAt = loaded.value.updatedAt
            await publish()
        } catch {
            if Task.isCancelled { return }
            loadFailed = true
            isOffline = true
        }
        isFirstLoadDone = true
    }

    private func loadLatest(force: Bool) async {
        guard !rawNews.isEmpty, let loaded = try? await client.load("latest.json", as: NewsFeed.self, force: force) else { return }
        if Task.isCancelled { return }
        noteOrigin(loaded.origin)
        newsStamp = status?.checkedAt
        latestAt = Date()
        let dead = Set(loaded.value.dead)
        let deadChanged = dead != deadLinks
        deadLinks = dead
        let fresh = NewsPipeline.novel(loaded.value.articles, against: rawNews)
        let gotImage = NewsPipeline.fillImages(from: loaded.value.articles, into: &rawNews)
        guard !fresh.isEmpty || gotImage || deadChanged else { return }
        if !fresh.isEmpty {
            let at = Date()
            overlay = fresh.map { (article: $0, at: at) } + overlay
            rawNews = fresh + rawNews
        }
        await publish()
    }

    private func noteOrigin(_ origin: FeedClient.Origin) {
        isOffline = origin == .cache
        if origin != .cache {
            lastSync = Date()
            loadFailed = false
        }
    }

    private func loadOgIfDue() async {
        guard Date().timeIntervalSince(ogLoadedAt) >= 60 else { return }
        if let loaded = try? await client.load("og.json", as: OgImages.self) {
            og = loaded.value.images
            ogLoadedAt = Date()
        }
    }

    private func refreshPolicyIfDue() async {
        guard Date().timeIntervalSince(policyAt) >= Self.policyEvery else { return }
        policyAt = Date()
        guard let fresh = await client.refreshPolicy() else { return }
        policy = fresh
        if !rawNews.isEmpty { await publish() }
    }

    private func loadSecondaryIfDue() async {
        let now = Date()
        if now.timeIntervalSince(secondaryAt) >= Self.secondaryEvery {
            secondaryAt = now
            async let marketsLoad = try? client.load("markets.json", as: MarketsFeed.self)
            async let socialLoad = try? client.load("social.json", as: SocialFeed.self)
            async let sourcesLoad = try? client.load("sources.json", as: SourcesFeed.self)
            async let videoLoad = try? client.load("video.json", as: VideoFeed.self)
            async let footballLoad = try? client.load("football.json", as: FootballFeed.self)
            if let v = await marketsLoad?.value, !v.items.isEmpty { markets = v.items }
            if let v = await socialLoad?.value { socialPosts = v.posts }
            if let v = await sourcesLoad?.value { sourceRows = v.sources }
            if let v = await videoLoad?.value { videoItems = v.items.filter { policy.allowsVideo(channel: $0.channel) } }
            if let v = await footballLoad?.value { football = v.leagues }
        }
        if now.timeIntervalSince(sportsAt) >= Self.sportsEvery {
            sportsAt = now
            if let v = try? await client.load("sports.json", as: SportsFeed.self) { sports = v.value.leagues }
        }
        leagues = football + sports
        if now.timeIntervalSince(weatherAt) >= Self.weatherEvery {
            weatherAt = now
            await loadCityServices()
        }
    }

    private func loadCityServices() async {
        let current = city
        if let list = try? await Services.weather(cities: [current]), let first = list.first, current == city { weatherHere = first }
        if let day = try? await Services.prayer(city: current), current == city { prayer = day }
    }

    func loadAllWeather() async {
        guard weatherAll.isEmpty else { return }
        if let list = try? await Services.weather(cities: Catalog.cities) {
            weatherAll = list.sorted { $0.city.compare($1.city, locale: Locale(identifier: "az")) == .orderedAscending }
        }
    }

    // MARK: - Lentin dərci

    private func publish() async {
        let raw = rawNews, images = og, rules = policy, lang = language, order = sectionOrder, off = sectionsOff, dead = deadLinks
        publishToken += 1
        let token = publishToken
        let (list, content) = await Task.detached(priority: .userInitiated) { () -> ([Article], HomeContent) in
            let list = NewsPipeline.publish(raw: raw, og: images, policy: rules, dead: dead)
            return (list, HomeContent.build(list, language: lang, sectionOrder: order, sectionsOff: off))
        }.value
        // Sonra başlayan dərc əvvəl bitibsə köhnə nəticə onun üstünə yazılmasın.
        guard token == publishToken else { return }
        isFirstLoadDone = true
        BreakingNotifier.markSeen(list)
        reloadWidgetsIfDue()
        if holdingUpdates && !articles.isEmpty {
            // Oxucu aşağıdadırsa ekran dəyişmir; «Yeni xəbərlər» düyməsi görünür.
            let known = Set(articles.map(\.id))
            pendingNewCount = list.filter { !known.contains($0.id) }.count
            pendingArticles = list
            pendingHome = content
        } else {
            show(list, content)
        }
    }

    private func show(_ list: [Article], _ content: HomeContent) {
        articles = list
        home = content
        pendingArticles = nil
        pendingHome = nil
        pendingNewCount = 0
    }

    func homeOffsetChanged(_ offset: CGFloat) {
        let hold = offset < Self.holdOffset
        guard hold != holdingUpdates else { return }
        holdingUpdates = hold
        if !hold { applyPending() }
    }

    func applyPending() {
        if let list = pendingArticles, let content = pendingHome { show(list, content) }
    }

    private func rebuildHome() {
        guard !articles.isEmpty else { return }
        let list = articles, lang = language, order = sectionOrder, off = sectionsOff
        Task {
            let content = await Task.detached(priority: .userInitiated) {
                HomeContent.build(list, language: lang, sectionOrder: order, sectionsOff: off)
            }.value
            home = content
        }
    }

    private func reloadWidgetsIfDue() {
        guard Date().timeIntervalSince(widgetsAt) >= Self.widgetEvery else { return }
        widgetsAt = Date()
        WidgetCenter.shared.reloadAllTimelines()
    }

    // MARK: - Süzgəc və axtarış

    func article(id: String) -> Article? {
        if let hit = articles.first(where: { $0.id == id }) ?? saved.first(where: { $0.id == id }) { return hit }
        for rows in archives.values {
            if let hit = rows.first(where: { $0.id == id }) { return hit }
        }
        return nil
    }

    // MARK: - Bölmə arxivi

    /// Arxiv dəyişəndə siyahılar yenidən hesablanır.
    var archiveStamp: Int { archives.values.reduce(0) { $0 + $1.count } }

    /// Lent gündüz 2-3 saat əhatə edir, bölmə səhifəsi və axtarış isə 5 gün (app.js `loadArchive`). Yalnız lazım olanda yüklənir.
    func loadArchive(_ slug: String) async {
        guard !Self.noArchive.contains(slug), Catalog.category(slug) != nil else { return }
        if let at = archiveAt[slug], Date().timeIntervalSince(at) < Self.archiveEvery { return }
        archiveAt[slug] = Date()
        // Ekrandan çıxmaq yüklənməni kəsməsin: fayl qayıdanda hazır olsun.
        let feed = self.client
        let loaded = await Task { try? await feed.load("arxiv/\(slug).json", as: NewsFeed.self) }.value
        if let loaded {
            archives[slug] = policy.clean(loaded.value.articles)
        } else {
            archiveAt[slug] = nil
        }
    }

    func loadAllArchives() async {
        await withTaskGroup(of: Void.self) { group in
            for category in Catalog.categories {
                group.addTask { await self.loadArchive(category.slug) }
            }
        }
    }

    func allowsExternalLink(_ url: String) -> Bool { policy.allowsExternalLink(url) }

    /// Mövzu süzgəci bütün arxivi yoxlayır: hesablama arxa planda gedir (3-cü qırmızı xətt).
    func sectionRows(_ slug: String, club: String?) async -> [Article] {
        let all = articles, rows = archives, lang = language
        return await Task.detached(priority: .userInitiated) {
            Ranking.section(slug, club: club, articles: all, archives: rows, language: lang.isEmpty ? nil : lang)
        }.value
    }

    func count(forSection slug: String) -> Int {
        Ranking.section(slug, club: nil, articles: articles, archives: [:], language: language.isEmpty ? nil : language).count
    }

    /// Axtarış bölmə arxivlərini də görür.
    func searchResults(_ text: String) async -> [Article] {
        let all = articles, rows = archives, lang = language
        return await Task.detached(priority: .userInitiated) {
            var pool = all
            for list in rows.values { pool = NewsPipeline.withArchive(pool, rows: list) }
            return Ranking.search(text, in: pool, language: lang.isEmpty ? nil : lang)
        }.value
    }

    func teamNews(_ team: TeamInfo, _ league: LeagueDoc) async -> [Article] {
        let all = articles, rows = archives["idman"] ?? []
        return await Task.detached(priority: .userInitiated) {
            TeamNews.articles(team: team, league: league, in: NewsPipeline.withArchive(all, rows: rows))
        }.value
    }

    /// İdman menyusunun dünya liqaları (sports.json).
    func worldLeagues(sport: String) -> [League] { leagues.filter { $0.isWorld && $0.sport == sport } }

    func noteSearch(_ query: String) {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard q.count >= 2 else { return }
        recentSearches = Array(([q] + recentSearches.filter { $0 != q }).prefix(8))
        store(recentSearches, Key.recent)
    }

    func clearRecentSearches() {
        recentSearches = []
        store(recentSearches, Key.recent)
    }

    // MARK: - Seçilmişlər

    func isSaved(_ a: Article) -> Bool { saved.contains { $0.id == a.id } }

    func toggleSave(_ a: Article) {
        if isSaved(a) { saved.removeAll { $0.id == a.id } }
        else { saved.insert(a, at: 0) }
        if saved.count > 200 { saved = Array(saved.prefix(200)) }
        persistSaved()
    }

    private func persistSaved() {
        if let data = try? JSONEncoder().encode(saved) { store(data, Key.saved) }
    }

    /// Köhnə yaddaş da eyni qaydadan keçir (assets/app.js `savedView`).
    var visibleSaved: [Article] { saved.filter { !policy.violation($0) } }

    // MARK: - Bölmələrin sırası

    func moveSections(from: IndexSet, to: Int) {
        sectionOrder.move(fromOffsets: from, toOffset: to)
        store(sectionOrder, Key.order)
        rebuildHome()
    }

    func setSection(_ slug: String, visible: Bool) {
        if visible { sectionsOff.remove(slug) } else { sectionsOff.insert(slug) }
        store(Array(sectionsOff), Key.off)
        rebuildHome()
    }

    func resetSections() {
        sectionOrder = Catalog.orderableSlugs
        sectionsOff = []
        store(sectionOrder, Key.order)
        store([String](), Key.off)
        rebuildHome()
    }

    // MARK: - Bildiriş və yaddaş

    /// İcazə verilməsə `false` qayıdır.
    func setNotifications(_ on: Bool) async -> Bool {
        guard on else {
            notificationsOn = false
            store(false, Key.notify)
            return true
        }
        let granted = await BreakingNotifier.requestPermission()
        notificationsOn = granted
        store(granted, Key.notify)
        if granted { BreakingNotifier.schedule() }
        return granted
    }

    func clearAllData() {
        saved = []
        recentSearches = []
        let d = UserDefaults.standard
        for key in [Key.saved, Key.recent, Key.language, Key.theme, Key.city, Key.direct, Key.reader, Key.order, Key.off] {
            d.removeObject(forKey: key)
        }
        language = "az"
        theme = .system
        opensSourceDirectly = false
        opensInReaderMode = false
        sectionOrder = Catalog.orderableSlugs
        sectionsOff = []
        rebuildHome()
        URLCache.shared.removeAllCachedResponses()
        ImageLoader.shared.clear()
    }
}
