import SwiftUI
import UlduzCore
import WebKit

struct ServicesView: View {
    @Environment(AppModel.self) private var model
    @Environment(Router.self) private var router

    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $router.servicesPath) {
            List {
                Section("Gündəlik") {
                    row("Bazar və çevirici", "chart.line.uptrend.xyaxis", .markets)
                    row("Hava", "cloud.sun.fill", .weather)
                    row("Namaz vaxtları", "moon.stars.fill", .prayer)
                    row("Tıxac və yollar", "car.fill", .traffic)
                }
                Section("İdman və video") {
                    row("Futbol və cədvəllər", "sportscourt.fill", .football)
                    row("Video xəbərlər", "play.rectangle.fill", .videos)
                }
                Section("Tətbiq") {
                    row("Tənzimləmələr", "gearshape.fill", .settings)
                    row("Mənbə vəziyyəti", "dot.radiowaves.left.and.right", .sources)
                    row("Haqqımızda", "info.circle.fill", .about)
                }
            }
            .screenBackground()
            .navigationTitle("Xidmətlər")
            .withRoutes()
        }
    }

    private func row(_ title: String, _ symbol: String, _ route: Route) -> some View {
        NavigationLink(value: route) {
            Label {
                Text(ui: title)
            } icon: {
                Image(systemName: symbol).foregroundStyle(Theme.gold)
            }
        }
        .listRowBackground(Theme.card)
    }
}

// MARK: - Bazar

struct MarketsView: View {
    @Environment(AppModel.self) private var model
    @State private var amount = "100"
    @State private var from = "USD"
    @State private var to = "AZN"
    @FocusState private var amountFocused: Bool

    private let columns = [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)]

    private var result: String {
        let value = Double(amount.replacingOccurrences(of: ",", with: ".")) ?? 0
        guard let out = Converter.convert(max(0, value), from: from, to: to, items: model.markets) else { return "—" }
        return Format.number(out, decimals: to == "AZN" || to == "BTC" ? (to == "BTC" ? 6 : 2) : 4)
    }

    private var unofficial: Bool { model.markets.contains(where: \.isUnofficial) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                converter
                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(model.markets) { MarketChip(item: $0, fills: true) }
                }
                if unofficial {
                    Text("Valyuta: AMB rəsmi məzənnəsi hazırda alınmır, bazar məzənnəsi göstərilir.")
                        .font(.footnote)
                        .foregroundStyle(Theme.gold)
                }
                Text("Valyuta AMB-nin rəsmi məzənnəsidir (alınmayanda bazar məzənnəsi, nişanla). Neft və bitcoin Yahoo Finance, qızıl və gümüş gold-api.com. Maliyyə məsləhəti deyil.")
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
            }
            .padding(16)
        }
        .scrollDismissesKeyboard(.interactively)
        .refreshable { await model.refresh() }
        .screenBackground()
        .navigationTitle("Bazar")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Bitdi") { amountFocused = false }
            }
        }
    }

    private var converter: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Çevirici").font(.headline)
            TextField("Məbləğ", text: $amount)
                .keyboardType(.decimalPad)
                .focused($amountFocused)
                .textFieldStyle(.roundedBorder)
                .accessibilityLabel("Məbləğ")
            HStack {
                picker("Nədən", selection: $from)
                Button {
                    let previous = from
                    from = to
                    to = previous
                } label: {
                    Image(systemName: "arrow.left.arrow.right")
                }
                .accessibilityLabel("Valyutaları dəyiş")
                picker("Nəyə", selection: $to)
            }
            Text(result)
                .font(.title2.weight(.bold))
                .monospacedDigit()
                .foregroundStyle(Theme.gold)
                .frame(maxWidth: .infinity, alignment: .trailing)
        }
        .padding(14)
        .cardStyle()
    }

    private func picker(_ title: String, selection: Binding<String>) -> some View {
        Picker(title, selection: selection) {
            Text("AZN").tag("AZN")
            ForEach(model.markets) { Text(ui: $0.label).tag($0.id) }
        }
        .pickerStyle(.menu)
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Hava

struct WeatherView: View {
    @Environment(AppModel.self) private var model
    @State private var filter = ""

    private var rows: [WeatherNow] {
        let q = TextTools.fold(filter)
        return q.isEmpty ? model.weatherAll : model.weatherAll.filter { TextTools.fold($0.city).contains(q) }
    }

    var body: some View {
        List {
            if let w = model.weatherHere, filter.isEmpty {
                Section {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Image(systemName: w.symbol)
                                .symbolRenderingMode(.multicolor)
                                .font(.system(size: 44))
                            VStack(alignment: .leading) {
                                Text("\(w.temp)°").font(.largeTitle.weight(.bold))
                                HStack(spacing: 4) {
                                    Text(ui: w.city)
                                    Text(verbatim: "·")
                                    Text(ui: w.label)
                                }
                                .font(.subheadline)
                                .foregroundStyle(Theme.muted)
                            }
                        }
                        Text("Hiss olunan \(w.feels)° · Rütubət %\(w.humidity) · Külək \(w.wind) km/s · Təzyiq \(w.pressure) hPa · Yağıntı \(String(format: "%.1f", w.precipitation)) mm")
                            .font(.footnote)
                            .foregroundStyle(Theme.muted)
                    }
                    .padding(.vertical, 4)
                    .accessibilityElement(children: .combine)
                    .listRowBackground(Theme.card)
                }
            }
            Section("Bütün şəhərlər") {
                if model.weatherAll.isEmpty { ProgressView().frame(maxWidth: .infinity).listRowBackground(Theme.card) }
                ForEach(rows) { w in
                    Button {
                        model.cityName = w.city
                    } label: {
                        HStack {
                            Image(systemName: w.symbol).symbolRenderingMode(.multicolor).frame(width: 28)
                            Text(ui: w.city)
                            if w.city == model.cityName { Image(systemName: "checkmark").foregroundStyle(Theme.gold) }
                            Spacer()
                            Text(ui: w.label).font(.caption).foregroundStyle(Theme.muted)
                            Text("\(w.temp)°").fontWeight(.semibold).monospacedDigit()
                        }
                    }
                    .buttonStyle(.plain)
                    .listRowBackground(Theme.card)
                }
            }
        }
        .screenBackground()
        .searchable(text: $filter, prompt: "Şəhər axtar")
        .navigationTitle("Hava")
        .navigationBarTitleDisplayMode(.inline)
        .task { await model.loadAllWeather() }
    }
}

// MARK: - Namaz

struct PrayerView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        List {
            Section {
                Picker("Şəhər", selection: $model.cityName) {
                    ForEach(Catalog.cities) { Text(ui: $0.name).tag($0.name) }
                }
                .listRowBackground(Theme.card)
            }
            if let day = model.prayer, day.city == model.cityName {
                let next = day.next()
                Section {
                    ForEach(day.times) { time in
                        HStack {
                            Image(systemName: time.symbol).foregroundStyle(Theme.gold).frame(width: 28)
                            Text(ui: time.label).fontWeight(time.id == next?.id ? .bold : .regular)
                            Spacer()
                            Text(time.time).fontWeight(.semibold).monospacedDigit()
                            if time.id == next?.id { Pill(text: "NÖVBƏTİ", color: Theme.green) }
                        }
                        .listRowBackground(Theme.card)
                    }
                } footer: {
                    Text(day.hijri.isEmpty ? "Mənbə: aladhan.com" : "\(day.hijri) · Mənbə: aladhan.com")
                }
            } else {
                ProgressView().frame(maxWidth: .infinity).listRowBackground(Color.clear)
            }
        }
        .screenBackground()
        .navigationTitle("Namaz vaxtları")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Futbol

struct FootballView: View {
    @Environment(AppModel.self) private var model
    @State private var leagueID: String?
    @State private var pane = "results"
    @State private var groupIndex = 0

    private var league: League? {
        model.leagues.first { $0.id == leagueID } ?? model.leagues.first
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if model.leagues.isEmpty {
                    EmptyStateView(symbol: "sportscourt", title: "Məlumat yoxdur", message: "Cədvəllər hazırda alınmadı. Bir az sonra yenidən baxın.")
                } else {
                    leaguePicker
                }
                if let league {
                    HStack {
                        Text(line(league))
                            .font(.footnote)
                            .foregroundStyle(Theme.muted)
                        Spacer()
                        Button(league.source.isEmpty ? "Mənbə" : league.source) { Browser.open(league.link) }
                            .font(.footnote.weight(.semibold))
                    }
                    if league.isWorld { worldPane(league) } else { localPane(league) }
                }
            }
            .padding(16)
        }
        .refreshable { await model.refresh() }
        .screenBackground()
        .navigationTitle("Nəticələr və bombardirlər")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func line(_ league: League) -> String {
        var parts = [league.title]
        if !league.season.isEmpty { parts.append(league.season) }
        if !league.asOf.isEmpty { parts.append(Format.gamesUntil(league.asOf)) }
        if league.stale { parts.append("köhnə məlumat") }
        return parts.joined(separator: " · ")
    }

    private var leaguePicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(model.leagues) { item in
                    Button {
                        leagueID = item.id
                        groupIndex = 0
                    } label: {
                        Text(item.short)
                            .font(.footnote.weight(.semibold))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 7)
                            .foregroundStyle(item.id == league?.id ? Color.black.opacity(0.85) : Color.primary)
                            .background(item.id == league?.id ? Theme.gold : Theme.card2, in: Capsule())
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    @ViewBuilder
    private func worldPane(_ league: League) -> some View {
        if league.groups.count > 1 {
            Picker("Qrup", selection: $groupIndex) {
                ForEach(Array(league.groups.enumerated()), id: \.offset) { index, group in
                    Text(group.shownName).tag(index)
                }
            }
            .pickerStyle(.segmented)
        }
        if league.groups.indices.contains(groupIndex) {
            StandingsTable(rows: league.groups[groupIndex].rows, basketball: league.isBasketball, leagueSlug: Topics.slug(league.short))
        } else if let first = league.groups.first {
            StandingsTable(rows: first.rows, basketball: league.isBasketball, leagueSlug: Topics.slug(league.short))
        }
    }

    @ViewBuilder
    private func localPane(_ league: League) -> some View {
        Picker("Bölmə", selection: $pane) {
            Text("Nəticələr").tag("results")
            Text("Təqvim").tag("fixtures")
            if !league.groups.isEmpty { Text("Cədvəl").tag("table") }
            Text("Bombardirlər").tag("scorers")
        }
        .pickerStyle(.segmented)
        switch pane {
        case "fixtures":
            games(league.fixtures, round: league.roundNext, empty: "Növbəti tur hələ elan olunmayıb.")
        case "table":
            if let group = league.groups.first {
                StandingsTable(rows: group.rows, basketball: false, leagueSlug: Topics.slug(league.short))
            } else {
                games(league.results, round: league.roundPlayed, empty: "Nəticə hələ yoxdur.")
            }
        case "scorers":
            scorers(league.scorers)
        default:
            games(league.results, round: league.roundPlayed, empty: "Nəticə hələ yoxdur.")
        }
    }

    @ViewBuilder
    private func games(_ list: [Game], round: String?, empty: String) -> some View {
        if list.isEmpty {
            Text(empty).font(.footnote).foregroundStyle(Theme.muted)
        } else {
            if let round, !round.isEmpty {
                Text(Int(round) != nil ? "\(Format.ordinal(round)) tur" : round)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Theme.muted)
            }
            VStack(spacing: 8) {
                ForEach(list) { game in
                    VStack(spacing: 4) {
                        HStack {
                            Text(Catalog.clubAz(game.home))
                                .fontWeight(.semibold)
                                .frame(maxWidth: .infinity, alignment: .trailing)
                            Text(game.played ? "\(game.homeScore ?? "–") : \(game.awayScore ?? "–")" : "–")
                                .fontWeight(.bold)
                                .monospacedDigit()
                                .foregroundStyle(Theme.gold)
                                .frame(minWidth: 44)
                            Text(Catalog.clubAz(game.away))
                                .fontWeight(.semibold)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .font(.footnote)
                        Text([Format.shortDateTime(game.date), game.stadium].filter { !$0.isEmpty }.joined(separator: " · "))
                            .font(.caption2)
                            .foregroundStyle(Theme.muted)
                    }
                    .padding(10)
                    .accessibilityElement(children: .combine)
                    .cardStyle()
                }
            }
        }
    }

    @ViewBuilder
    private func scorers(_ list: [Scorer]) -> some View {
        if list.isEmpty {
            Text("Bombardir siyahısı alınmadı.").font(.footnote).foregroundStyle(Theme.muted)
        } else {
            VStack(spacing: 0) {
                ForEach(Array(list.enumerated()), id: \.element.id) { index, scorer in
                    HStack {
                        Text("\(index + 1)").foregroundStyle(Theme.muted).monospacedDigit().frame(width: 24, alignment: .leading)
                        Text(scorer.name).fontWeight(.semibold)
                        Text(Catalog.clubAz(scorer.club)).foregroundStyle(Theme.muted).lineLimit(1)
                        Spacer()
                        Text("\(scorer.goals) qol").fontWeight(.bold).monospacedDigit()
                    }
                    .font(.footnote)
                    .padding(.vertical, 8)
                    .accessibilityElement(children: .combine)
                    if index < list.count - 1 { Divider() }
                }
            }
            .padding(.horizontal, 12)
            .cardStyle()
        }
    }
}

private struct StandingsTable: View {
    let rows: [StandingRow]
    let basketball: Bool
    let leagueSlug: String

    private func cell(_ value: Int?) -> String { value.map(String.init) ?? "–" }

    var body: some View {
        Grid(alignment: .trailing, horizontalSpacing: 6, verticalSpacing: 8) {
            header
            Divider()
            ForEach(rows) { row in
                GridRow {
                    Text("\(row.pos)")
                        .foregroundStyle(Theme.muted)
                        .gridColumnAlignment(.leading)
                    NavigationLink(value: Route.team(league: leagueSlug, team: Topics.slug(row.full), season: nil)) {
                        HStack(spacing: 5) {
                            if let logo = TextTools.webURL(row.logo) {
                                RemoteImage(urls: [logo], category: "idman", maxPixel: 60, contentMode: .fit).frame(width: 16, height: 16)
                            }
                            Text(Catalog.clubAz(row.team)).fontWeight(.semibold).lineLimit(1).minimumScaleFactor(0.8)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .gridColumnAlignment(.leading)
                    if basketball {
                        Text(cell(row.won))
                        Text(cell(row.lost))
                        Text(row.pct.map { String(format: "%.1f", $0 * 100) } ?? "–")
                        Text(row.gamesBehind ?? "-")
                    } else {
                        Text(cell(row.played))
                        Text(cell(row.won))
                        Text(cell(row.drawn))
                        Text(cell(row.lost))
                        Text("\(cell(row.goalsFor)):\(cell(row.goalsAgainst))")
                        Text(cell(row.points)).fontWeight(.bold)
                    }
                }
                .accessibilityElement(children: .combine)
            }
        }
        .font(.caption)
        .monospacedDigit()
        .padding(12)
        .cardStyle()
    }

    @ViewBuilder
    private var header: some View {
        GridRow {
            Text("#").gridColumnAlignment(.leading)
            Text("Komanda").frame(maxWidth: .infinity, alignment: .leading).gridColumnAlignment(.leading)
            if basketball {
                Text("Q")
                Text("M")
                Text("%")
                Text("Geridə")
            } else {
                Text("O")
                Text("Q")
                Text("H")
                Text("M")
                Text("Qol")
                Text("Xal")
            }
        }
        .fontWeight(.semibold)
        .foregroundStyle(Theme.muted)
    }
}

// MARK: - Video

struct VideosView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                if model.videoItems.isEmpty {
                    EmptyStateView(symbol: "play.rectangle", title: "Video lent açılmır", message: "Bir az sonra yenidən baxın.")
                }
                ForEach(model.videoItems) { VideoCard(item: $0, width: nil) }
            }
            .padding(16)
        }
        .refreshable { await model.refresh() }
        .screenBackground()
        .navigationTitle("Video xəbərlər")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Tıxac

/// Waze xəritəsi yalnız düyməyə basanda yüklənir (saytdakı kimi).
private struct WazeMap: UIViewRepresentable {
    let url: URL

    final class Coordinator {
        var requested: URL?
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: .zero, configuration: config)
        view.isOpaque = false
        view.backgroundColor = .clear
        return view
    }

    // Xəritə özü yönləndirə bilər: yalnız ərazi dəyişəndə yenidən yüklənir.
    func updateUIView(_ view: WKWebView, context: Context) {
        guard context.coordinator.requested != url else { return }
        context.coordinator.requested = url
        view.load(URLRequest(url: url))
    }
}

struct TrafficView: View {
    @Environment(AppModel.self) private var model
    @State private var areaID = Catalog.trafficAreas[0].id
    @State private var mapOn = false

    private var area: TrafficArea { Catalog.trafficAreas.first { $0.id == areaID } ?? Catalog.trafficAreas[0] }

    var body: some View {
        let items = Ranking.localRoadItems(model.articles)
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if Ranking.bakuRushHour() {
                    Pill(text: "PİK SAAT", color: Theme.red, filled: true)
                }
                Picker("Ərazi", selection: $areaID) {
                    ForEach(Catalog.trafficAreas) { Text(ui: $0.label).tag($0.id) }
                }
                .pickerStyle(.menu)
                Group {
                    if mapOn {
                        WazeMap(url: area.embedURL)
                    } else {
                        Button {
                            mapOn = true
                        } label: {
                            VStack(spacing: 8) {
                                Image(systemName: "map.fill").font(.largeTitle).foregroundStyle(Theme.gold)
                                Text("Canlı xəritəni aç").font(.subheadline.weight(.semibold))
                            }
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .frame(height: 320)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                .cardStyle()
                Button("Waze-də aç") { Browser.open(area.liveURL) }
                    .font(.footnote.weight(.semibold))
                Text("Xəritə Waze-dən açılır. Aşağıda yalnız son 2 saatın Bakı və Abşeron üzrə yol xəbərləri göstərilir; bunlar canlı tıxac ölçüləri deyil.")
                    .font(.footnote)
                    .foregroundStyle(Theme.muted)
                if items.isEmpty {
                    Text("Son 2 saatda yol xəbəri yoxdur.")
                        .font(.footnote)
                        .foregroundStyle(Theme.muted)
                }
                ForEach(items) { item in
                    ArticleLink(article: item.article) {
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: item.symbol).foregroundStyle(Theme.gold).frame(width: 24)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.article.cleanTitle)
                                    .font(.subheadline.weight(.semibold))
                                    .multilineTextAlignment(.leading)
                                ArticleMeta(article: item.article)
                            }
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                        .cardStyle()
                    }
                }
            }
            .padding(16)
        }
        .refreshable { await model.refresh() }
        .screenBackground()
        .navigationTitle("Tıxac və yollar")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Mənbələr

struct SourcesView: View {
    @Environment(AppModel.self) private var model
    @State private var filter = ""

    private var rows: [SourceStatus] {
        let q = TextTools.fold(filter)
        return q.isEmpty ? model.sourceRows : model.sourceRows.filter { TextTools.fold($0.name).contains(q) }
    }

    private func color(_ level: SourceStatus.Level) -> Color {
        switch level {
        case .ok: return Theme.green
        case .warn: return Theme.gold
        case .bad: return Theme.red
        case .unknown: return Theme.muted
        }
    }

    private func label(_ level: SourceStatus.Level) -> String {
        switch level {
        case .ok: return "İşləyir"
        case .warn: return "Zəif"
        case .bad: return "Xəta"
        case .unknown: return "Yoxlama məlumatı yoxdur"
        }
    }

    var body: some View {
        List {
            Section {
                ForEach(rows) { source in
                    let level = source.level()
                    HStack(spacing: 10) {
                        Circle().fill(color(level)).frame(width: 9, height: 9)
                        Text(source.name).font(.subheadline.weight(.semibold))
                        Spacer()
                        VStack(alignment: .trailing, spacing: 2) {
                            Text(label(level))
                            Text("\(source.count ?? 0) xəbər · \(source.okAt == nil ? "uğur yoxdur" : Format.ago(ISODate.parse(source.okAt)))")
                                .foregroundStyle(Theme.muted)
                        }
                        .font(.caption)
                    }
                    .accessibilityElement(children: .combine)
                    .listRowBackground(Theme.card)
                }
            } footer: {
                Text("Yaşıl: son saatlarda xəbər gəlib. Sarı: boş və ya köhnəlmiş uğur. Qırmızı: xəta.")
            }
        }
        .screenBackground()
        .searchable(text: $filter, prompt: "Mənbənin adı…")
        .navigationTitle("Mənbə vəziyyəti")
        .navigationBarTitleDisplayMode(.inline)
    }
}
