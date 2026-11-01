import SwiftUI
import UlduzCore

// Liqa və komanda ekranları (assets/komanda.js). Məlumat: pfl.az, Vikipediya, TheSportsDB, OpenLigaDB; mənbə hər ekranda yazılır.

// MARK: - Liqaların siyahısı

struct LeagueHubView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let index = model.teams.index
        List {
            Section {
                row("Nəticələr və bombardirlər", symbol: "list.number", route: .footballOverview)
            }
            if let index {
                group("Azərbaycan liqaları", index.leagues.filter(\.isLocal))
                group("Dünya liqaları", index.leagues.filter { !$0.isLocal && !$0.cup && !$0.isBasketball })
                group("Ölkə kubokları", index.leagues.filter { !$0.isLocal && $0.cup && !$0.isBasketball })
                group("Basketbol", index.leagues.filter(\.isBasketball))
            } else if model.teams.hasFailed("futbol/index.json") {
                Text("Komanda məlumatı açılmadı. İnternet bağlantınızı yoxlayın.")
                    .font(.footnote)
                    .foregroundStyle(Theme.muted)
                    .listRowBackground(Theme.card)
            } else {
                ProgressView().frame(maxWidth: .infinity).listRowBackground(Color.clear)
            }
        }
        .screenBackground()
        .navigationTitle("Futbol və cədvəllər")
        .navigationBarTitleDisplayMode(.inline)
        .task { await model.teams.loadIndex() }
        .refreshable { await model.teams.loadIndex() }
    }

    @ViewBuilder
    private func group(_ title: String, _ leagues: [TeamLeague]) -> some View {
        if !leagues.isEmpty {
            Section {
                ForEach(leagues) { league in
                    NavigationLink(value: Route.league(id: league.id, season: nil)) {
                        Text(league.name)
                    }
                    .listRowBackground(Theme.card)
                }
            } header: {
                Text(ui: title)
            }
        }
    }

    private func row(_ title: String, symbol: String, route: Route) -> some View {
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

// MARK: - Liqa

struct LeagueView: View {
    @Environment(AppModel.self) private var model
    let id: String
    let season: String?

    @State private var chosenSeason: String?

    private var league: TeamLeague? { model.teams.index?.league(id) }
    private var seasonKey: String? { chosenSeason ?? season }
    private var path: String? { league?.path(season: seasonKey) }
    private var doc: LeagueDoc? { path.flatMap { model.teams.leagues[$0] } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if let league, let doc {
                    SeasonPicker(league: league, selection: Binding(get: { seasonKey ?? league.ready.first?.key ?? "" }, set: { chosenSeason = $0 }))
                    if doc.groups.isEmpty {
                        ClubList(doc: doc)
                    } else {
                        ForEach(doc.groups) { group in
                            TableBlock(doc: doc, group: group, highlight: nil, season: nonCurrent(league))
                        }
                    }
                    SourceLine(docs: [doc], checked: model.teams.index?.checked[league.id])
                } else {
                    TeamLoading(failed: path.map { model.teams.hasFailed($0) } ?? model.teams.hasFailed("futbol/index.json"), noLeague: model.teams.index != nil && league == nil)
                }
            }
            .padding(16)
        }
        .refreshable { await load() }
        .screenBackground()
        .navigationTitle(doc?.name ?? league?.name ?? "Liqa")
        .navigationBarTitleDisplayMode(.inline)
        .task(id: "\(id)|\(seasonKey ?? "")|\(model.teams.index == nil)") { await load() }
    }

    private func nonCurrent(_ league: TeamLeague) -> String? {
        seasonKey == league.ready.first?.key ? nil : seasonKey
    }

    private func load() async {
        await model.teams.loadIndex()
        if let path { await model.teams.loadLeague(path) }
    }
}

private struct SeasonPicker: View {
    let league: TeamLeague
    @Binding var selection: String

    var body: some View {
        if league.ready.count > 1 {
            Picker("Mövsüm", selection: $selection) {
                ForEach(league.ready) { Text($0.label).tag($0.key) }
            }
            .pickerStyle(.segmented)
        }
    }
}

private struct ClubList: View {
    let doc: LeagueDoc

    var body: some View {
        let slugs = doc.teams.keys.sorted {
            (doc.teams[$0]?.name ?? "").compare(doc.teams[$1]?.name ?? "", locale: Locale(identifier: "az")) == .orderedAscending
        }
        VStack(spacing: 0) {
            ForEach(slugs, id: \.self) { slug in
                NavigationLink(value: Route.team(league: doc.id, team: slug, season: nil)) {
                    HStack(spacing: 10) {
                        TeamLogo(url: doc.teams[slug]?.logo ?? "", size: 24, name: doc.teams[slug]?.name ?? "")
                        Text(doc.teams[slug]?.name ?? slug).font(.subheadline.weight(.semibold))
                        Spacer()
                        Image(systemName: "chevron.right").font(.caption2.weight(.bold)).foregroundStyle(Theme.muted)
                    }
                    .padding(.vertical, 9)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("team-row")
                Divider()
            }
        }
        .padding(.horizontal, 12)
        .cardStyle()
    }
}

// MARK: - Komanda

struct TeamView: View {
    @Environment(AppModel.self) private var model
    let leagueID: String
    let team: String
    let season: String?

    private enum Tab: String, CaseIterable, Identifiable {
        case overview = "Baxış", games = "Oyunlar", table = "Cədvəl", squad = "Heyət", news = "Xəbərlər"
        var id: String { rawValue }
    }

    @State private var tab = Tab.overview
    @State private var chosenLeague: String?
    @State private var chosenSeason: String?
    @State private var news: [Article] = []
    @State private var newsLoaded = false
    @State private var newsShown = 48

    private var index: TeamIndex? { model.teams.index }
    private var league: TeamLeague? { index?.league(chosenLeague ?? leagueID) }
    private var seasonKey: String? {
        let wanted = chosenSeason ?? season
        return league?.ready.contains { $0.key == wanted } == true ? wanted : league?.ready.first?.key
    }
    private var isCurrent: Bool { seasonKey == league?.ready.first?.key }
    private var path: String? { league?.path(season: seasonKey) }
    private var doc: LeagueDoc? { path.flatMap { model.teams.leagues[$0] } }
    private var others: [TeamLeague] {
        guard let league, let index else { return [] }
        return index.otherLeagues(league, team: team)
    }
    /// Baxışda oyunlar bütün yarışlardan gəlir.
    private var overviewDocs: [LeagueDoc] {
        guard let doc else { return [] }
        return [doc] + (isCurrent ? others.compactMap { model.teams.leagues[$0.path()] } : [])
    }
    private var hasSquad: Bool { isCurrent && league?.squads.contains(team) == true }
    private var hasGames: Bool {
        !(doc?.games.isEmpty ?? true) || (isCurrent && others.contains { $0.cup || !$0.source.hasPrefix("Viki") })
    }
    private var tabs: [Tab] {
        Tab.allCases.filter {
            switch $0 {
            case .games: return hasGames
            case .table: return !(doc?.groups.isEmpty ?? true)
            case .squad: return hasSquad
            default: return true
            }
        }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if let league, let doc, let info = doc.info(team) {
                    header(doc, info)
                    tabBar
                    content(league, doc, info)
                    SourceLine(docs: tab == .overview ? overviewDocs : [doc], checked: index?.checked[league.id])
                } else if let league, let doc {
                    // Bu mövsüm komanda bu yarışda deyil: liqanın cədvəli.
                    Text(doc.season + " · bu mövsüm komanda bu yarışda deyil")
                        .font(.footnote)
                        .foregroundStyle(Theme.muted)
                    ForEach(doc.groups) { TableBlock(doc: doc, group: $0, highlight: nil, season: nil) }
                    if doc.groups.isEmpty { ClubList(doc: doc) }
                    SourceLine(docs: [doc], checked: index?.checked[league.id])
                } else {
                    TeamLoading(failed: path.map { model.teams.hasFailed($0) } ?? model.teams.hasFailed("futbol/index.json"), noLeague: index != nil && league == nil)
                }
            }
            .padding(16)
        }
        .refreshable { await load() }
        .screenBackground()
        .navigationTitle(doc?.info(team)?.name ?? "Komanda")
        .navigationBarTitleDisplayMode(.inline)
        .task(id: "\(chosenLeague ?? leagueID)|\(seasonKey ?? "")|\(index == nil)") { await load() }
        .task(id: "\(doc?.id ?? "")|\(model.archiveStamp)|\(model.articles.count)") { await loadNews() }
    }

    private func load() async {
        await model.teams.loadIndex()
        if let path { await model.teams.loadLeague(path) }
        if isCurrent {
            for other in others { await model.teams.loadLeague(other.path()) }
        }
        if hasSquad, let id = league?.id { await model.teams.loadSquad(id) }
    }

    private func loadNews() async {
        guard let doc, let info = doc.info(team) else { return }
        await model.loadArchive("idman")
        if Task.isCancelled { return }
        news = await model.teamNews(info, doc)
        newsLoaded = true
    }

    private func header(_ doc: LeagueDoc, _ info: TeamInfo) -> some View {
        HStack(spacing: 12) {
            TeamLogo(url: info.logo, size: 56, name: info.name)
            VStack(alignment: .leading, spacing: 3) {
                Text(standing(doc))
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
                Text(info.name)
                    .font(.title2.weight(.bold))
                    .accessibilityAddTraits(.isHeader)
            }
        }
    }

    private func standing(_ doc: LeagueDoc) -> String {
        var text = doc.name
        if let hit = doc.row(of: team) { text += ", \(Format.place(hit.row.pos))" }
        if !isCurrent { text += " · \(doc.season)" }
        return text
    }

    private var tabBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(tabs) { item in
                    ChipButton(title: item.rawValue, selected: item == tab) { tab = item }
                }
            }
        }
    }

    @ViewBuilder
    private func content(_ league: TeamLeague, _ doc: LeagueDoc, _ info: TeamInfo) -> some View {
        switch tabs.contains(tab) ? tab : .overview {
        case .overview: overview(doc, info)
        case .games:
            picker(league)
            let rows = doc.games(of: team)
            if rows.isEmpty {
                note("\(doc.name) oyunları hələ əlavə olunmayıb.")
            } else {
                GameMonths(rows: rows.map { GameRow(game: $0, doc: doc) }, team: team)
            }
        case .table:
            picker(league)
            ForEach(doc.groups) { TableBlock(doc: doc, group: $0, highlight: team, season: isCurrent ? nil : seasonKey) }
        case .squad:
            SquadBlock(leagueID: league.id, team: team, name: info.name)
        case .news:
            newsBlock(info, limit: newsShown)
        }
    }

    @ViewBuilder
    private func picker(_ league: TeamLeague) -> some View {
        let leagues = [league] + others
        if leagues.count > 1 {
            Picker("Yarış", selection: Binding(get: { league.id }, set: { chosenLeague = $0; chosenSeason = nil })) {
                ForEach(leagues) { Text($0.name).tag($0.id) }
            }
            .pickerStyle(.menu)
        }
        SeasonPicker(league: league, selection: Binding(get: { seasonKey ?? "" }, set: { chosenSeason = $0 }))
    }

    @ViewBuilder
    private func overview(_ doc: LeagueDoc, _ info: TeamInfo) -> some View {
        let rows = overviewDocs.flatMap { source in source.games(of: team).map { GameRow(game: $0, doc: source) } }
        let split = TeamGames.split(rows.map(\.game))
        let form = doc.form(of: team)
        if !form.isEmpty {
            SectionHeader(title: "Son nəticələr")
            HStack(spacing: 4) { ForEach(Array(form.enumerated()), id: \.offset) { OutcomeBadge(outcome: $0.element) } }
        }
        if hasGames {
            if isCurrent {
                SectionHeader(title: "Növbəti oyunlar") {
                    Button { tab = .games } label: {
                        Text("Bütün oyunlar").font(.footnote.weight(.semibold)).foregroundStyle(Theme.gold)
                    }
                    .buttonStyle(.plain)
                }
                if split.next.isEmpty {
                    note("Növbəti oyun hələ elan olunmayıb.")
                } else {
                    gameCards(Array(split.next.prefix(3)), rows: rows)
                }
            }
            SectionHeader(title: "Son oyunlar")
            if split.played.isEmpty {
                note("Bu mövsüm hələ oyun olmayıb.")
            } else {
                gameCards(Array(split.played.suffix(3).reversed()), rows: rows)
            }
        }
        if !doc.groups.isEmpty, doc.row(of: team) != nil {
            SectionHeader(title: "Turnir cədvəli") {
                Button { tab = .table } label: {
                    Text("Bütün cədvəl").font(.footnote.weight(.semibold)).foregroundStyle(Theme.gold)
                }
                .buttonStyle(.plain)
            }
            LeagueTable(doc: doc, rows: doc.neighbours(of: team), highlight: team, season: isCurrent ? nil : seasonKey)
        }
        SectionHeader(title: "Xəbərlər") {
            Button { tab = .news } label: {
                Text("Bütün xəbərlər").font(.footnote.weight(.semibold)).foregroundStyle(Theme.gold)
            }
            .buttonStyle(.plain)
        }
        newsBlock(info, limit: 6)
    }

    private func gameCards(_ games: [TeamGame], rows: [GameRow]) -> some View {
        VStack(spacing: 8) {
            ForEach(games) { game in
                if let doc = rows.first(where: { $0.game == game })?.doc {
                    GameCard(game: game, doc: doc, team: team)
                }
            }
        }
    }

    @ViewBuilder
    private func newsBlock(_ info: TeamInfo, limit: Int) -> some View {
        if news.isEmpty {
            if newsLoaded {
                note("\(info.name) haqqında son 5 gündə xəbər tapılmadı.")
            } else {
                ProgressView().frame(maxWidth: .infinity)
            }
        } else {
            LazyVStack(spacing: 10) {
                ForEach(news.prefix(limit)) { ArticleRow(article: $0, showCategory: false) }
            }
            if tab == .news, news.count > limit {
                Button {
                    newsShown += 48
                } label: {
                    Text("Daha çox (\(news.count - limit))")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Theme.card2, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func note(_ text: String) -> some View {
        Text(ui: text).font(.footnote).foregroundStyle(Theme.muted)
    }
}

// MARK: - Hissələr

private struct GameRow: Identifiable {
    let game: TeamGame
    let doc: LeagueDoc
    var id: String { doc.id + game.id }
}

private struct GameMonths: View {
    let rows: [GameRow]
    let team: String

    var body: some View {
        let months = TeamGames.byMonth(rows.map(\.game))
        ForEach(months, id: \.title) { month in
            Text(ui: month.title)
                .font(.subheadline.weight(.bold))
                .accessibilityAddTraits(.isHeader)
            VStack(spacing: 8) {
                ForEach(month.games) { game in
                    if let doc = rows.first(where: { $0.game == game })?.doc {
                        GameCard(game: game, doc: doc, team: team)
                    }
                }
            }
        }
    }
}

private struct GameCard: View {
    let game: TeamGame
    let doc: LeagueDoc
    let team: String

    private func side(_ who: String, _ score: Int?) -> some View {
        let info = doc.info(who)
        return HStack(spacing: 8) {
            TeamLogo(url: info?.logo ?? "", size: 20, name: info?.shownName ?? who)
            Text(info?.shownName ?? who)
                .fontWeight(who == team ? .bold : .regular)
                .lineLimit(1)
            Spacer()
            if game.played { Text(score.map(String.init) ?? "–").fontWeight(.bold).monospacedDigit() }
        }
        .font(.footnote)
    }

    var body: some View {
        NavigationLink(value: Route.team(league: doc.id, team: game.opponent(of: team), season: nil)) {
            VStack(alignment: .leading, spacing: 6) {
                Text(doc.name + (game.roundText.isEmpty ? "" : " · \(game.roundText)"))
                    .font(.caption2)
                    .foregroundStyle(Theme.muted)
                    .lineLimit(1)
                side(game.home, game.homeScore)
                side(game.away, game.awayScore)
                HStack(spacing: 6) {
                    Text(ui: game.whenText)
                    if !game.stateText().isEmpty { Text(ui: game.stateText()).fontWeight(.semibold) }
                    Spacer()
                    if let outcome = game.outcome(for: team) { OutcomeBadge(outcome: outcome) }
                }
                .font(.caption)
                .foregroundStyle(Theme.muted)
            }
            .padding(10)
            .contentShape(Rectangle())
            .cardStyle()
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
    }
}

struct OutcomeBadge: View {
    let outcome: TeamGame.Outcome

    var body: some View {
        let (letter, color): (LocalizedStringKey, Color) = {
            switch outcome {
            case .win: return ("Q", Theme.green)
            case .draw: return ("H", Theme.muted)
            case .loss: return ("M", Theme.red)
            }
        }()
        Text(letter)
            .font(.caption2.weight(.bold))
            .foregroundStyle(.white)
            .frame(width: 20, height: 20)
            .background(color, in: RoundedRectangle(cornerRadius: 5, style: .continuous))
    }
}

struct TeamLogo: View {
    let url: String
    let size: CGFloat
    let name: String

    var body: some View {
        Group {
            if let link = TextTools.webURL(url) {
                RemoteImage(urls: [link], category: "idman", maxPixel: size * 3, contentMode: .fit)
            } else {
                Text(String(name.prefix(1)))
                    .font(.system(size: size * 0.46, weight: .bold))
                    .foregroundStyle(Theme.muted)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Theme.card2, in: Circle())
            }
        }
        .frame(width: size, height: size)
    }
}

private struct TableBlock: View {
    let doc: LeagueDoc
    let group: TeamTable
    let highlight: String?
    let season: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if doc.groups.count > 1, !group.name.isEmpty {
                Text(ui: group.name).font(.subheadline.weight(.bold))
            }
            LeagueTable(doc: doc, rows: group.rows, highlight: highlight, season: season)
            let zones = LeagueDoc.zones(group.rows)
            if !zones.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(zones, id: \.note) { zone in
                        HStack(spacing: 6) {
                            RoundedRectangle(cornerRadius: 2).fill(Color(hex: zone.color) ?? .clear).frame(width: 10, height: 10)
                            Text(ui: zone.note)
                        }
                    }
                }
                .font(.caption2)
                .foregroundStyle(Theme.muted)
            }
        }
    }
}

/// İlk iki sütun yerində qalır, qalanı yana sürüşür.
struct LeagueTable: View {
    let doc: LeagueDoc
    let rows: [TeamRow]
    let highlight: String?
    let season: String?

    private let rowHeight: CGFloat = 34
    private func cell(_ value: Int?) -> String { value.map(String.init) ?? "–" }

    private var columns: [(title: LocalizedStringKey, width: CGFloat)] {
        if doc.isBasketball {
            return [("O", 28), ("Q", 28), ("M", 28), ("%", 42), ("Geridə", 52)]
        }
        var list: [(title: LocalizedStringKey, width: CGFloat)] = [("O", 26), ("Q", 26), ("H", 26), ("M", 26), ("Qol", 46), ("F", 34), ("Xal", 32)]
        if !doc.games.isEmpty { list.append(("Son 5", 116)) }
        return list
    }

    var body: some View {
        HStack(spacing: 0) {
            VStack(spacing: 0) {
                HStack(spacing: 4) {
                    Text("#").frame(width: 22, alignment: .leading)
                    Text("Komanda").frame(maxWidth: .infinity, alignment: .leading)
                }
                .font(.caption.weight(.semibold))
                .foregroundStyle(Theme.muted)
                .frame(height: rowHeight)
                ForEach(rows) { row in
                    NavigationLink(value: Route.team(league: doc.id, team: row.team, season: season)) {
                        HStack(spacing: 4) {
                            Text("\(row.pos)")
                                .font(.caption)
                                .monospacedDigit()
                                .foregroundStyle(Theme.muted)
                                .frame(width: 22, alignment: .leading)
                                .overlay(alignment: .leading) {
                                    if let zone = Color(hex: row.color) {
                                        zone.frame(width: 3).offset(x: -8)
                                    }
                                }
                            TeamLogo(url: doc.info(row.team)?.logo ?? "", size: 18, name: doc.info(row.team)?.shownName ?? "")
                            Text(doc.info(row.team)?.shownName ?? row.team)
                                .font(.caption.weight(row.team == highlight ? .bold : .semibold))
                                .lineLimit(1)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .frame(height: rowHeight)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("team-row")
                }
            }
            .frame(width: 164)
            ScrollView(.horizontal, showsIndicators: false) {
                VStack(spacing: 0) {
                    HStack(spacing: 2) {
                        ForEach(Array(columns.enumerated()), id: \.offset) { _, column in
                            Text(column.title).frame(width: column.width)
                        }
                    }
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Theme.muted)
                    .frame(height: rowHeight)
                    ForEach(rows) { row in
                        HStack(spacing: 2) { values(row) }
                            .font(.caption)
                            .monospacedDigit()
                            .frame(height: rowHeight)
                    }
                }
            }
        }
        .padding(.leading, 12)
        .padding(.trailing, 6)
        .padding(.bottom, 6)
        .cardStyle()
    }

    @ViewBuilder
    private func values(_ row: TeamRow) -> some View {
        let widths = columns.map(\.width)
        if doc.isBasketball {
            Text(cell(row.played)).frame(width: widths[0])
            Text(cell(row.won)).frame(width: widths[1])
            Text(cell(row.lost)).frame(width: widths[2])
            Text(row.pct.map { String(format: "%.1f", $0 * 100) } ?? "–").frame(width: widths[3])
            Text(row.gamesBehind ?? "-").frame(width: widths[4])
        } else {
            Text(cell(row.played)).frame(width: widths[0])
            Text(cell(row.won)).frame(width: widths[1])
            Text(cell(row.drawn)).frame(width: widths[2])
            Text(cell(row.lost)).frame(width: widths[3])
            Text("\(cell(row.goalsFor)):\(cell(row.goalsAgainst))").frame(width: widths[4])
            Text((row.goalDiff ?? 0) > 0 ? "+\(cell(row.goalDiff))" : cell(row.goalDiff)).frame(width: widths[5])
            Text(cell(row.points)).fontWeight(.bold).frame(width: widths[6])
            if widths.count > 7 {
                HStack(spacing: 2) {
                    ForEach(Array(doc.form(of: row.team).enumerated()), id: \.offset) { OutcomeBadge(outcome: $0.element) }
                }
                .frame(width: widths[7], alignment: .leading)
            }
        }
    }
}

private struct SquadBlock: View {
    @Environment(AppModel.self) private var model
    let leagueID: String
    let team: String
    let name: String

    var body: some View {
        let squad = model.teams.squads[leagueID]?.teams[team]
        if let squad, !squad.players.isEmpty {
            ForEach(SquadPlayer.positions, id: \.key) { position in
                let rows = squad.players.filter { $0.position == position.key }
                if !rows.isEmpty {
                    Text(ui: position.label).font(.subheadline.weight(.bold))
                    VStack(spacing: 0) {
                        ForEach(rows) { player in
                            HStack(spacing: 8) {
                                Text(player.number)
                                    .font(.caption.weight(.bold))
                                    .monospacedDigit()
                                    .foregroundStyle(Theme.muted)
                                    .frame(width: 24, alignment: .leading)
                                if let flag = TextTools.webURL(player.flag) {
                                    RemoteImage(urls: [flag], category: "idman", maxPixel: 40, contentMode: .fit).frame(width: 20, height: 14)
                                }
                                Text(player.name).font(.subheadline)
                                Spacer()
                                if !player.age.isEmpty { Text("\(player.age) yaş").font(.caption).foregroundStyle(Theme.muted) }
                            }
                            .padding(.vertical, 7)
                            .accessibilityElement(children: .combine)
                        }
                    }
                    .padding(.horizontal, 12)
                    .cardStyle()
                }
            }
            if !squad.wiki.isEmpty, let link = wikiURL(squad.wiki) {
                Text(attribution(link))
                    .font(.caption2)
                    .foregroundStyle(Theme.muted)
                    .environment(\.openURL, OpenURLAction { Browser.open($0); return .handled })
            }
        } else if model.teams.hasFailed("futbol/heyet-\(leagueID).json") {
            Text("Heyət yüklənmədi.").font(.footnote).foregroundStyle(Theme.muted)
        } else if model.teams.squads[leagueID] != nil {
            Text("\(name) üçün heyət məlumatı yoxdur.").font(.footnote).foregroundStyle(Theme.muted)
        } else {
            ProgressView().frame(maxWidth: .infinity)
        }
    }

    private func wikiURL(_ title: String) -> URL? {
        let page = title.replacingOccurrences(of: " ", with: "_").addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? ""
        return URL(string: "https://en.wikipedia.org/wiki/\(page)")
    }

    private func attribution(_ link: URL) -> AttributedString {
        var text = AttributedString("Heyət: ")
        var wiki = AttributedString("Vikipediya")
        wiki.link = link
        var license = AttributedString("CC BY-SA 4.0")
        license.link = URL(string: "https://creativecommons.org/licenses/by-sa/4.0/")
        text.append(wiki)
        text.append(AttributedString(", "))
        text.append(license)
        return text
    }
}

/// Səhifədə göstərilən bütün yarışların mənbəyi: lisenziya bunu tələb edir.
private struct SourceLine: View {
    let docs: [LeagueDoc]
    let checked: String?

    private var text: AttributedString {
        var out = AttributedString("Mənbə: ")
        var seen = Set<String>()
        var first = true
        func add(_ title: String, _ url: String) {
            if !first { out.append(AttributedString(", ")) }
            first = false
            var part = AttributedString(title)
            if let link = TextTools.webURL(url) { part.link = link }
            out.append(part)
        }
        for doc in docs where seen.insert(doc.source).inserted {
            add(doc.source, doc.sourceURL.isEmpty ? doc.url : doc.sourceURL)
        }
        if let wiki = docs.first(where: { !$0.sourceURL.isEmpty && !$0.url.isEmpty }) { add("Vikipediya", wiki.url) }
        if let until = docs.first?.asOfText, !until.isEmpty { out.append(AttributedString(" · \(until)")) }
        if let date = ISODate.parse(checked) { out.append(AttributedString(" · yoxlanıb \(Format.ago(date))")) }
        return out
    }

    var body: some View {
        Text(text)
            .font(.caption2)
            .foregroundStyle(Theme.muted)
            .environment(\.openURL, OpenURLAction { Browser.open($0); return .handled })
    }
}

private struct TeamLoading: View {
    let failed: Bool
    let noLeague: Bool

    var body: some View {
        if noLeague {
            EmptyStateView(symbol: "sportscourt", title: "Bu liqanın səhifəsi yoxdur", message: "Hazırda yalnız məlumatı alınan liqaların komanda səhifələri açılır.")
        } else if failed {
            EmptyStateView(symbol: "wifi.slash", title: "Komanda məlumatı açılmadı", message: "İnternet bağlantınızı yoxlayın. Səhifə özü yenidən cəhd edəcək.")
        } else {
            ProgressView().frame(maxWidth: .infinity).padding(.top, 40)
        }
    }
}

extension Color {
    /// Cədvəlin zona rəngi: `#BBF3BB`. Lent xarici mənbədir, başqa forma qəbul olunmur.
    init?(hex: String) {
        guard hex.hasPrefix("#") else { return nil }
        var digits = String(hex.dropFirst())
        if digits.count == 3 { digits = digits.map { "\($0)\($0)" }.joined() }
        guard digits.count >= 6, let value = UInt64(digits.prefix(6), radix: 16) else { return nil }
        self.init(red: Double((value >> 16) & 0xFF) / 255, green: Double((value >> 8) & 0xFF) / 255, blue: Double(value & 0xFF) / 255)
    }
}
