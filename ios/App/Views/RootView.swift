import SwiftUI
import UlduzCore

struct RootView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        @Bindable var router = router
        TabView(selection: $router.tab) {
            HomeView()
                .tabItem { Label("Əsas", systemImage: "house.fill") }
                .tag(AppTab.home)
            SectionsView()
                .tabItem { Label("Bölmələr", systemImage: "square.grid.2x2.fill") }
                .tag(AppTab.sections)
            SearchView()
                .tabItem { Label("Axtar", systemImage: "magnifyingglass") }
                .tag(AppTab.search)
            SavedView()
                .tabItem { Label("Seçilmişlər", systemImage: "star.fill") }
                .tag(AppTab.saved)
            ServicesView()
                .tabItem { Label("Xidmətlər", systemImage: "ellipsis.circle.fill") }
                .tag(AppTab.services)
        }
        .tint(Theme.gold)
        .preferredColorScheme(model.theme.scheme)
        // Tətbiq ekranda olduqca 30 saniyəlik dövrə işləyir; arxa plana keçəndə ləğv olunur, qayıdanda dərhal yoxlanır.
        // `.active` şərti olmaz: sistem pəncərəsi və İdarə mərkəzi altında tətbiq `.inactive`-dir, amma görünür.
        .task(id: scenePhase == .background) {
            if scenePhase != .background { await model.foregroundLoop() }
        }
        .onChange(of: router.pendingArticle?.id) { _, _ in openPending() }
        .onChange(of: model.articles.isEmpty) { _, _ in openPending() }
        .onChange(of: model.isFirstLoadDone) { _, _ in openPending() }
    }

    /// Vidcet və bildiriş: xəbər lentdədirsə önizləmə, artıq yoxdursa icazəli mənbə keçidi açılır.
    private func openPending() {
        guard let pending = router.pendingArticle else { return }
        if let article = model.article(id: pending.id) {
            router.pendingArticle = nil
            if model.opensSourceDirectly {
                Browser.open(article.sourceUrl, reader: model.opensInReaderMode)
            } else {
                router.show(.article(article), in: .home)
            }
        } else if model.isFirstLoadDone {
            router.pendingArticle = nil
            if model.allowsExternalLink(pending.url) {
                Browser.open(pending.url, reader: model.opensInReaderMode)
            }
        }
    }
}
