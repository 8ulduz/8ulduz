import SwiftUI
import UlduzCore

struct SectionsView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router

    private let columns = [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)]

    /// Bu dildə xəbəri olmayan bölmə gizlənir. İdman bütün dillərdədir (assets/dil.js `emptySections`).
    private var shown: [NewsCategory] {
        guard model.interfaceLanguage != "az" else { return Catalog.categories }
        return Catalog.categories.filter { $0.slug == "idman" || model.count(forSection: $0.slug) > 0 }
    }

    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $router.sectionsPath) {
            ScrollView {
                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(shown) { category in
                        NavigationLink(value: Route.section(category.slug)) {
                            SectionTile(category: category)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(16)
            }
            .refreshable { await model.refresh() }
            .screenBackground()
            .navigationTitle("Bölmələr")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { LanguageMenu() }
            }
            .withRoutes()
        }
    }
}

private struct SectionTile: View {
    let category: NewsCategory

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Image(systemName: category.symbol)
                .font(.title3)
                .foregroundStyle(Theme.color(forCategory: category.slug))
                .frame(width: 40, height: 40)
                .background(Theme.color(forCategory: category.slug).opacity(0.15), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            Text(ui: category.label)
                .font(.subheadline.weight(.bold))
                .lineLimit(2)
                .multilineTextAlignment(.leading)
            Text(ui: category.description)
                .font(.caption)
                .foregroundStyle(Theme.muted)
                .lineLimit(3)
                .multilineTextAlignment(.leading)
        }
        .frame(maxWidth: .infinity, minHeight: 112, alignment: .topLeading)
        .padding(12)
        .contentShape(Rectangle())
        .cardStyle()
        .accessibilityElement(children: .combine)
    }
}

struct SectionFeedView: View {
    @Environment(AppModel.self) private var model
    let slug: String

    private static let pageSize = 48
    @State private var shown = SectionFeedView.pageSize
    @State private var club: String?
    @State private var openTab: String?
    @State private var list: [Article] = []
    @State private var isLoaded = false

    private var category: NewsCategory? { Catalog.category(slug) }
    private var tabs: [Topic] { Topics.tabs(forSection: slug) }

    private var note: String? {
        switch slug {
        case "idman": return "Bütün dillərdə idman xəbərləri. Alt bölməni və ya komandanı seçin: son xəbərlər açılır."
        case "bolgeler": return "Bölgəni, sonra şəhər və ya rayonu seçin: son xəbərlər açılır."
        default: return category?.description
        }
    }

    private var rowsKey: String {
        "\(slug)|\(club ?? "")|\(model.language)|\(model.articles.first?.id ?? "")|\(model.articles.count)|\(model.archiveStamp)"
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 10) {
                if let note {
                    Text(ui: note)
                        .font(.footnote)
                        .foregroundStyle(Theme.muted)
                }
                if !tabs.isEmpty { subNav }
                if slug == "prezident" { SocialBlock() }
                if isLoaded && list.isEmpty {
                    if club != nil {
                        EmptyStateView(symbol: "newspaper", title: "Bu mövzuda son 5 gündə xəbər tapılmadı.")
                    } else {
                        EmptyStateView(symbol: "newspaper", title: "Hələ xəbər yoxdur", message: "Bu bölmədə xəbər yoxdur. Növbəti yenilənmədə əlavə olunacaq.")
                    }
                }
                ForEach(list.prefix(shown)) { article in
                    ArticleRow(article: article, showCategory: slug == "sondeqiqe" || slug == "video")
                }
                if list.count > shown {
                    Button {
                        shown += Self.pageSize
                    } label: {
                        Text("Daha çox (\(list.count - shown))")
                            .font(.subheadline.weight(.semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(Theme.card2, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(16)
        }
        .refreshable { await model.refresh() }
        .screenBackground()
        .navigationTitle(Text(ui: category?.label ?? slug))
        .navigationBarTitleDisplayMode(.inline)
        .task(id: rowsKey) {
            let rows = await model.sectionRows(slug, club: club)
            if Task.isCancelled { return }
            list = rows
            isLoaded = true
        }
        .task(id: "\(slug)|\(club == nil)") {
            await model.loadArchive(slug)
            if slug == "bolgeler" && club != nil { await model.loadAllArchives() }
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Text("\(list.count)")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(Theme.muted)
                    .monospacedDigit()
                    .accessibilityLabel("\(list.count) xəbər")
            }
        }
    }

    private func select(_ name: String?, opens: Bool) {
        club = name
        if opens || name == nil { openTab = name }
        shown = Self.pageSize
    }

    /// Birinci sətir alt bölmələr, ikinci sətir seçilmiş alt bölmənin liqaları və mövzuları (assets/app.js `navRows`).
    private var subNav: some View {
        VStack(alignment: .leading, spacing: 8) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ChipButton(title: "Hamısı", selected: club == nil && openTab == nil) { select(nil, opens: true) }
                    ForEach(tabs) { tab in
                        ChipButton(title: tab.name, selected: club == tab.name || openTab == tab.name) { select(tab.name, opens: true) }
                    }
                }
            }
            let leagues = subLeagues
            let groups = subGroups(hasLeagues: !leagues.isEmpty)
            if !leagues.isEmpty || !groups.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(groups) { group in
                            if !group.group.isEmpty {
                                Text(ui: group.group).font(.caption.weight(.bold)).foregroundStyle(Theme.muted)
                            }
                            ForEach(group.items) { item in
                                ChipButton(title: item.shownName, selected: club == item.name) { select(item.name, opens: false) }
                            }
                        }
                        ForEach(leagues, id: \.short) { league in
                            NavigationLink(value: Route.league(id: Topics.slug(league.short), season: nil)) {
                                ChipLabel(title: league.label)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    private static let azLeagues = ["Premyer Liqa", "I Liqa", "II Liqa", "Kubok", "Əvəzedicilər"]

    /// Ünvanlar updater.py-dakı `team_world_league` və `_team_sources` ilə eynidir.
    private var subLeagues: [(short: String, label: String)] {
        guard slug == "idman" else { return [] }
        func world(_ sport: String) -> [(short: String, label: String)] {
            model.worldLeagues(sport: sport).map { (short: $0.short, label: $0.title.replacingOccurrences(of: " \\(.*", with: "", options: .regularExpression)) }
        }
        switch openTab ?? "" {
        case "Basketbol": return world("basketball")
        case "Futbol": return Self.azLeagues.map { (short: $0, label: $0) } + world("football")
        default: return []
        }
    }

    private func subGroups(hasLeagues: Bool) -> [TopicGroup] {
        guard let tab = tabs.first(where: { $0.name == openTab }) else { return [] }
        if slug == "idman" {
            if openTab == "Basketbol" && hasLeagues { return [] }
            if openTab == "Futbol" {
                // Cədvəl gəlibsə komandalar liqanın səhifəsindən açılır; məlumat çatana qədər düymələr qalır.
                let worldReady = !model.worldLeagues(sport: "football").isEmpty
                return tab.groups.compactMap { group -> TopicGroup? in
                    if group.group == "Azərbaycan" { return group.filtered { $0.name == "Milli komanda" } }
                    return worldReady ? nil : group
                }
            }
        }
        return tab.groups
    }
}

/// Zuğulba Xronikası bölməsinin rəsmi hesabları və son yazıları (assets/app.js `socialBlock`).
private struct SocialBlock: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Sosial şəbəkələr")
                .font(.headline)
            ForEach(Catalog.profiles) { profile in
                VStack(alignment: .leading, spacing: 6) {
                    Text(profile.who)
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(Theme.muted)
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(profile.links) { link in
                                Button(link.name) { Browser.open(link.url) }
                                    .font(.caption.weight(.semibold))
                                    .buttonStyle(.bordered)
                            }
                        }
                    }
                }
            }
            ForEach(model.socialPosts.prefix(8)) { post in
                Button {
                    Browser.open(post.url)
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(post.network).fontWeight(.bold).foregroundStyle(Theme.gold)
                            Text(post.name)
                            Spacer()
                            Text(Format.ago(post.date))
                        }
                        .font(.caption)
                        .foregroundStyle(Theme.muted)
                        Text(post.text)
                            .font(.footnote)
                            .multilineTextAlignment(.leading)
                            .lineLimit(4)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(10)
                    .contentShape(Rectangle())
                    .cardStyle()
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.bottom, 6)
    }
}

struct SectionEditorView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List {
            Section {
                ForEach(model.sectionOrder, id: \.self) { slug in
                    Toggle(LocalizedStringKey(Catalog.label(slug)), isOn: Binding(
                        get: { !model.sectionsOff.contains(slug) },
                        set: { model.setSection(slug, visible: $0) }
                    ))
                }
                .onMove { model.moveSections(from: $0, to: $1) }
            } footer: {
                Text("Ana səhifədəki bölmələrin sırasını dəyişin, lazım olmayanları söndürün.")
            }
            Section {
                Button("Standart sıraya qaytar") { model.resetSections() }
            }
        }
        .environment(\.editMode, .constant(.active))
        .screenBackground()
        .navigationTitle("Bölmələri tənzimlə")
        .navigationBarTitleDisplayMode(.inline)
    }
}
