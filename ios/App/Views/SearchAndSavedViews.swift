import SwiftUI
import UlduzCore

struct SearchView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router
    @State private var query = ""
    @State private var results: [Article] = []
    @State private var searchedQuery = ""
    @State private var isActive = false

    private var hasQuery: Bool { !Ranking.searchWords(query).isEmpty }

    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $router.searchPath) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    if hasQuery {
                        resultsList
                    } else {
                        suggestions
                    }
                }
                .padding(16)
            }
            .scrollDismissesKeyboard(.interactively)
            .screenBackground()
            .navigationTitle("Axtar")
            .searchable(text: $query, isPresented: $isActive, placement: .navigationBarDrawer(displayMode: .always), prompt: "Xəbər axtar…")
            .onSubmit(of: .search) { model.noteSearch(query) }
            .task(id: searchKey) { await runSearch() }
            .onChange(of: router.searchFocusRequest) { _, _ in isActive = true }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { LanguageMenu() }
            }
            .withRoutes()
        }
    }

    private var searchKey: String { "\(query)|\(model.language)|\(model.articles.count)" }

    /// Hər hərfdə axtarış işləməsin; nəticə arxa planda hesablanır.
    private func runSearch() async {
        let text = query
        guard !Ranking.searchWords(text).isEmpty else {
            results = []
            searchedQuery = ""
            return
        }
        try? await Task.sleep(for: .milliseconds(220))
        if Task.isCancelled { return }
        let pool = model.searchPool
        let found = await Task.detached(priority: .userInitiated) { Ranking.search(text, in: pool) }.value
        if Task.isCancelled { return }
        results = found
        searchedQuery = text
    }

    @ViewBuilder
    private var resultsList: some View {
        if !results.isEmpty {
            Text("\(results.count) nəticə. Uyğunluğa görə sıralanıb.")
                .font(.footnote)
                .foregroundStyle(Theme.muted)
            ForEach(results.prefix(60)) { ArticleRow(article: $0) }
        } else if searchedQuery == query {
            EmptyStateView(symbol: "magnifyingglass", title: "Nəticə tapılmadı", message: "Başqa sözlərlə yoxlayın və ya dil süzgəcini dəyişin.")
        }
    }

    @ViewBuilder
    private var suggestions: some View {
        if !model.recentSearches.isEmpty {
            SectionHeader(title: "Son axtarışlar") {
                Button("Təmizlə") { model.clearRecentSearches() }
                    .font(.footnote.weight(.semibold))
            }
            ForEach(model.recentSearches, id: \.self) { item in
                Button {
                    query = item
                } label: {
                    Label(item, systemImage: "clock.arrow.circlepath")
                        .font(.subheadline)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 6)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
        } else {
            EmptyStateView(symbol: "magnifyingglass", title: "Xəbər axtarın",
                           message: "Başlıq, xülasə və mənbə adına görə axtarılır. «qarabag», «ilham eliyev» kimi yazılışlar da tapılır.")
        }
    }
}

struct SavedView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router

    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $router.savedPath) {
            ScrollView {
                let items = model.visibleSaved
                LazyVStack(spacing: 10) {
                    if items.isEmpty {
                        EmptyStateView(symbol: "star", title: "Saxlanmış xəbər yoxdur",
                                       message: "Xəbərin üzərindəki ulduza basın, sonra burada oxuyun. Seçilmişlər yalnız telefonunuzda saxlanır.")
                    }
                    ForEach(items) { ArticleRow(article: $0) }
                }
                .padding(16)
            }
            .screenBackground()
            .navigationTitle("Seçilmişlər")
            .withRoutes()
        }
    }
}
