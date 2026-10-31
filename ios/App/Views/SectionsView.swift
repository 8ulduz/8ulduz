import SwiftUI
import UlduzCore

struct SectionsView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router

    private let columns = [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)]

    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $router.sectionsPath) {
            ScrollView {
                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(Catalog.categories) { category in
                        NavigationLink(value: Route.section(category.slug)) {
                            SectionTile(category: category, count: model.count(forSection: category.slug))
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
    let count: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Image(systemName: category.symbol)
                .font(.title3)
                .foregroundStyle(Theme.color(forCategory: category.slug))
                .frame(width: 40, height: 40)
                .background(Theme.color(forCategory: category.slug).opacity(0.15), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            Text(category.label)
                .font(.subheadline.weight(.bold))
                .lineLimit(2)
                .multilineTextAlignment(.leading)
            Text("\(count) xəbər")
                .font(.caption)
                .foregroundStyle(Theme.muted)
                .monospacedDigit()
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

    private var category: NewsCategory? { Catalog.category(slug) }

    var body: some View {
        let list = model.list(forSection: slug, club: club)
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 10) {
                if let category {
                    Text(slug == "idman" ? "Bütün dillərdə idman xəbərləri. Dil süzgəci bu bölməyə tətbiq edilmir." : category.description)
                        .font(.footnote)
                        .foregroundStyle(Theme.muted)
                }
                if slug == "idman" { clubPicker }
                if slug == "prezident" { SocialBlock() }
                if list.isEmpty {
                    EmptyStateView(symbol: "newspaper", title: "Hələ xəbər yoxdur", message: "Bu bölmədə xəbər yoxdur. Növbəti yenilənmədə əlavə olunacaq.")
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
        .navigationTitle(category?.label ?? slug)
        .navigationBarTitleDisplayMode(.inline)
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

    private var clubPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                chip("Bütün idman", selected: club == nil) { club = nil }
                ForEach(Ranking.clubs, id: \.name) { item in
                    chip(item.name, selected: club == item.name) { club = item.name }
                }
            }
        }
    }

    private func chip(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.footnote.weight(.semibold))
                .padding(.horizontal, 12)
                .padding(.vertical, 7)
                .foregroundStyle(selected ? Color.black.opacity(0.85) : Color.primary)
                .background(selected ? Theme.gold : Theme.card2, in: Capsule())
        }
        .buttonStyle(.plain)
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
                    Toggle(Catalog.label(slug), isOn: Binding(
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
