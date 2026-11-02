import Observation
import SafariServices
import SwiftUI
import UlduzCore

enum AppTab: Hashable {
    case home, sections, search, saved, services
}

enum Route: Hashable {
    case article(Article)
    case section(String)
    case markets, weather, prayer, football, footballOverview, videos, traffic, sources, settings, sectionEditor, about
    case league(id: String, season: String?)
    case team(league: String, team: String, season: String?)
}

@MainActor
@Observable
final class Router {
    static let shared = Router()

    var tab: AppTab = .home
    var homePath: [Route] = []
    var sectionsPath: [Route] = []
    var searchPath: [Route] = []
    var savedPath: [Route] = []
    var servicesPath: [Route] = []
    var searchFocusRequest = 0

    /// Vidcet və bildirişdən gələn xəbər: model lenti yükləyəndən sonra açılır.
    var pendingArticle: (id: String, url: String)?

    private init() {}

    func openArticle(id: String, url: String) {
        pendingArticle = (id, url)
    }

    func show(_ route: Route, in tab: AppTab) {
        self.tab = tab
        switch tab {
        case .home: homePath = [route]
        case .sections: sectionsPath = [route]
        case .search: searchPath = [route]
        case .saved: savedPath = [route]
        case .services: servicesPath = [route]
        }
    }

    func focusSearch() {
        tab = .search
        searchPath = []
        searchFocusRequest += 1
    }

    func open(shortcut type: String) {
        switch type {
        case "az.ulduz8.app.gundem": show(.section("gundem"), in: .sections)
        case "az.ulduz8.app.idman": show(.section("idman"), in: .sections)
        case "az.ulduz8.app.secilmis": tab = .saved
        case "az.ulduz8.app.axtar": focusSearch()
        default: break
        }
    }

    /// `ulduz8://xeber/<id>?u=<keçid>`, `ulduz8://bolme/<slug>`, `ulduz8://secilmis`, `ulduz8://axtar`, `ulduz8://bazar`.
    func open(url: URL) {
        guard url.scheme == "ulduz8" else { return }
        let parts = url.pathComponents.filter { $0 != "/" }
        switch url.host ?? "" {
        case "xeber":
            let link = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first { $0.name == "u" }?.value ?? ""
            if let id = parts.first { openArticle(id: id, url: link) }
        case "bolme":
            if let slug = parts.first, Catalog.category(slug) != nil { show(.section(Catalog.canonical(slug)), in: .sections) }
        case "secilmis": tab = .saved
        case "axtar": focusSearch()
        case "bazar": show(.markets, in: .services)
        default: tab = .home
        }
    }
}

/// Xəbərin mənbəsi tətbiqin içində açılan Safari pəncərəsində açılır.
@MainActor
enum Browser {
    private static var top: UIViewController? {
        let scene = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .first { $0.activationState == .foregroundActive }
        var vc = scene?.keyWindow?.rootViewController
        while let next = vc?.presentedViewController { vc = next }
        return vc
    }

    static func open(_ url: URL, reader: Bool = false) {
        guard let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https", url.host != nil else { return }
        let config = SFSafariViewController.Configuration()
        config.entersReaderIfAvailable = reader
        let safari = SFSafariViewController(url: url, configuration: config)
        safari.dismissButtonStyle = .close
        safari.preferredControlTintColor = UIColor(Theme.gold)
        top?.present(safari, animated: true)
    }

    static func open(_ string: String?, reader: Bool = false) {
        if let url = TextTools.webURL(string) { open(url, reader: reader) }
    }
}

extension View {
    func withRoutes() -> some View {
        navigationDestination(for: Route.self) { RouteView(route: $0) }
    }
}

struct RouteView: View {
    let route: Route

    var body: some View {
        switch route {
        case .article(let article): ArticleDetailView(article: article)
        case .section(let slug): SectionFeedView(slug: slug)
        case .markets: MarketsView()
        case .weather: WeatherView()
        case .prayer: PrayerView()
        case .football: LeagueHubView()
        case .footballOverview: FootballView()
        case .league(let id, let season): LeagueView(id: id, season: season)
        case .team(let league, let team, let season): TeamView(leagueID: league, team: team, season: season)
        case .videos: VideosView()
        case .traffic: TrafficView()
        case .sources: SourcesView()
        case .settings: SettingsView()
        case .sectionEditor: SectionEditorView()
        case .about: AboutView()
        }
    }
}
