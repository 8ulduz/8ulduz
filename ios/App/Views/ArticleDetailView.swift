import SwiftUI
import UlduzCore

/// Xəbərin önizləməsi (assets/app.js `articleView`): tam mətn yalnız mənbənin öz saytında açılır.
struct ArticleDetailView: View {
    @Environment(AppModel.self) private var model
    let article: Article

    private var related: [Article] {
        Array(model.articles.filter { $0.category == article.category && $0.id != article.id && $0.language == article.language }.prefix(5))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                let images = article.imageCandidates(og: model.og)
                if !images.isEmpty {
                    RemoteImage(urls: images, category: article.category, maxPixel: 1400)
                        .frame(height: 240)
                        .frame(maxWidth: .infinity)
                        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                }
                ArticleBadges(article: article)
                Text(article.cleanTitle)
                    .font(.title2.weight(.bold))
                    .textSelection(.enabled)
                HStack(spacing: 6) {
                    Text(article.shownSource).fontWeight(.semibold)
                    if !article.author.isEmpty { Text("· \(TextTools.tidy(article.author))") }
                    Spacer()
                    Text(Format.ago(article.date))
                }
                .font(.footnote)
                .foregroundStyle(Theme.muted)
                if !article.cleanSummary.isEmpty {
                    Text(article.cleanSummary)
                        .font(.body)
                        .lineSpacing(3)
                        .textSelection(.enabled)
                }
                Button {
                    Browser.open(article.sourceUrl, reader: model.opensInReaderMode)
                } label: {
                    Label("Xəbərin tam mətnini mənbədə oxu", systemImage: "safari")
                        .font(.subheadline.weight(.bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 13)
                        .foregroundStyle(.black.opacity(0.85))
                        .background(Theme.gold, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
                .buttonStyle(.plain)

                sources

                if !related.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        SectionHeader(title: "Bu bölmədən") {
                            MoreLink(route: .section(article.category))
                        }
                        ForEach(related) { ArticleRow(article: $0, showCategory: false) }
                    }
                }
            }
            .padding(16)
        }
        .screenBackground()
        .navigationTitle(Text(ui: Catalog.label(article.category)))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button {
                    model.toggleSave(article)
                } label: {
                    Image(systemName: model.isSaved(article) ? "star.fill" : "star")
                }
                .accessibilityLabel(model.isSaved(article) ? "Saxlanmışlardan çıxar" : "Yadda saxla")
                if let url = article.shareURL {
                    ShareLink(item: url, subject: Text(article.cleanTitle), message: Text(verbatim: "\(article.cleanTitle)\n\n8ulduz.az"))
                }
            }
        }
    }

    private var sources: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Bu xəbərin mənbələri (\(article.sourceCount))")
                .font(.title3.weight(.bold))
                .accessibilityAddTraits(.isHeader)
            sourceRow(name: article.shownSource, url: article.sourceUrl, date: article.date)
            ForEach(article.alts) { alt in
                sourceRow(name: alt.source, url: alt.sourceUrl, date: ISODate.parse(alt.publishedAt))
            }
        }
    }

    private func sourceRow(name: String, url: String, date: Date?) -> some View {
        Button {
            Browser.open(url, reader: model.opensInReaderMode)
        } label: {
            HStack {
                Text(name)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(Format.ago(date))
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
                Image(systemName: "arrow.up.right")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(Theme.gold)
            }
            .padding(12)
            .contentShape(Rectangle())
            .cardStyle()
        }
        .buttonStyle(.plain)
    }
}
