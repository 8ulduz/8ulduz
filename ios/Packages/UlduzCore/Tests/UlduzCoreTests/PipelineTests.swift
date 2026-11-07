import XCTest
@testable import UlduzCore

final class PipelineTests: XCTestCase {
    private let now = ISODate.parse("2026-10-31T12:00:00+00:00")!

    private func iso(minutesAgo m: Double) -> String {
        let f = ISO8601DateFormatter()
        return f.string(from: now.addingTimeInterval(-m * 60))
    }

    private func item(_ id: String, _ title: String, source: String = "APA", url: String? = nil, minutesAgo: Double = 10, category: String = "gundem", image: String = "", summary: String = "", lang: String = "az") -> Article {
        Article(id: id, title: title, summary: summary, category: category, source: source, sourceUrl: url ?? "https://apa.az/\(id)", publishedAt: iso(minutesAgo: minutesAgo), imageUrl: image, lang: lang)
    }

    // MARK: - Real lent

    func testEveryDataFileDecodes() throws {
        let data = RepoFiles.root.appendingPathComponent("data")
        func read(_ name: String) throws -> Data { try Data(contentsOf: data.appendingPathComponent(name)) }
        let decoder = JSONDecoder()
        let news = try decoder.decode(NewsFeed.self, from: read("news.json"))
        XCTAssertGreaterThan(news.articles.count, 100)
        XCTAssertGreaterThan(news.articles.filter { $0.date != nil }.count, news.articles.count * 9 / 10, "tarix formatı oxunmur")
        XCTAssertFalse(try decoder.decode(NewsFeed.self, from: read("latest.json")).articles.isEmpty)
        XCTAssertFalse(try decoder.decode(MarketsFeed.self, from: read("markets.json")).items.isEmpty)
        XCTAssertNotNil(try decoder.decode(FeedStatus.self, from: read("status.json")).checkedAt)
        XCTAssertFalse(try decoder.decode(SourcesFeed.self, from: read("sources.json")).sources.isEmpty)
        XCTAssertFalse(try decoder.decode(FootballFeed.self, from: read("football.json")).leagues.isEmpty)
        XCTAssertFalse(try decoder.decode(SportsFeed.self, from: read("sports.json")).leagues.isEmpty)
        _ = try decoder.decode(VideoFeed.self, from: read("video.json"))
        _ = try decoder.decode(SocialFeed.self, from: read("social.json"))
        XCTAssertFalse(try decoder.decode(OgImages.self, from: read("og.json")).images.isEmpty)
        XCTAssertFalse(try decoder.decode(NewsFeed.self, from: read("first.json")).articles.isEmpty)
        XCTAssertFalse(try decoder.decode(NewsFeed.self, from: read("arxiv/idman.json")).articles.isEmpty)
    }

    func testTeamFilesDecode() throws {
        let dir = RepoFiles.root.appendingPathComponent("data/futbol")
        let decoder = JSONDecoder()
        let index = try decoder.decode(TeamIndex.self, from: Data(contentsOf: dir.appendingPathComponent("index.json")))
        XCTAssertGreaterThan(index.leagues.count, 10)
        for league in index.leagues {
            for season in league.ready {
                let file = league.path(season: season.key).replacingOccurrences(of: "futbol/", with: "")
                let doc = try decoder.decode(LeagueDoc.self, from: Data(contentsOf: dir.appendingPathComponent(file)))
                XCTAssertEqual(doc.id, league.id)
                XCTAssertFalse(doc.teams.isEmpty, file)
            }
            for team in league.squads.prefix(1) {
                let squad = try decoder.decode(SquadDoc.self, from: Data(contentsOf: dir.appendingPathComponent("heyet-\(league.id).json")))
                XCTAssertFalse(squad.teams[team]?.players.isEmpty ?? true, team)
            }
        }
    }

    func testRealFeedThroughThePipelineIsFastAndSorted() throws {
        let root = RepoFiles.root
        let news = try JSONDecoder().decode(NewsFeed.self, from: Data(contentsOf: root.appendingPathComponent("data/news.json")))
        let og = try JSONDecoder().decode(OgImages.self, from: Data(contentsOf: root.appendingPathComponent("data/og.json"))).images
        let policy = try ContentPolicy(javascript: String(contentsOf: root.appendingPathComponent("assets/content-policy.js"), encoding: .utf8))
        let started = Date()
        let out = NewsPipeline.publish(raw: news.articles, og: og, policy: policy)
        XCTAssertLessThan(Date().timeIntervalSince(started), 5)
        XCTAssertFalse(out.isEmpty)
        let dates = out.compactMap(\.date)
        XCTAssertEqual(dates, dates.sorted(by: >))
        XCTAssertEqual(Set(out.map(\.sourceUrl)).count, out.count)
    }

    // MARK: - Birləşdirmə

    func testSimilarTitlesFromDifferentSourcesMerge() {
        let list = [
            item("1", "Əli Əsədov və İrakli Kobaxidze Tbilisidə görüşüb müzakirə aparıblar", source: "APA", minutesAgo: 5),
            item("2", "Əli Əsədov və İrakli Kobaxidze Tbilisidə görüşüb", source: "Oxu.az", url: "https://oxu.az/2", minutesAgo: 8, image: "https://oxu.az/2.jpg"),
            item("3", "Tamamilə başqa hadisə barədə xəbər verilir bu gün", source: "Lent.az", url: "https://lent.az/3", minutesAgo: 9),
        ]
        let out = NewsPipeline.cluster(list)
        XCTAssertEqual(out.count, 2)
        let merged = out.first { $0.sourceCount == 2 }
        XCTAssertEqual(merged?.source, "Oxu.az", "şəkli olan kart əsas olur")
        XCTAssertEqual(merged?.alts.map(\.source), ["APA"])
    }

    func testServerGroupingIsTrusted() {
        var a = item("1", "Bir başlıq burada yazılıb artıq", source: "APA")
        a.alts = [AltSource(source: "Oxu.az", sourceUrl: "https://oxu.az/1")]
        let b = item("2", "Bir başlıq burada yazılıb artıq deyə", source: "Lent.az", url: "https://lent.az/2")
        XCTAssertEqual(NewsPipeline.cluster([a, b]).count, 2)
    }

    func testOfficialSourceStaysPrimary() {
        let official = item("1", "Prezident İlham Əliyev qəbul edib nazirlər kabineti üzvlərini", source: "Prezident.az", url: "https://president.az/1")
        var rich = item("2", "Prezident İlham Əliyev qəbul edib nazirlər kabineti üzvlərini", source: "APA", image: "https://apa.az/x.jpg", summary: "Uzun xülasə")
        rich.lang = "az"
        let out = NewsPipeline.collapseExact([rich, official])
        XCTAssertEqual(out.count, 1)
        XCTAssertEqual(out[0].source, "Prezident.az")
        XCTAssertEqual(out[0].alts.map(\.source), ["APA"])
    }

    func testExactTitlesCollapseButNotAcrossDays() {
        let a = item("1", "Eyni başlıq iki dəfə gəlib burada", source: "APA", minutesAgo: 10)
        let b = item("2", "Eyni başlıq iki dəfə gəlib burada", source: "Oxu.az", url: "https://oxu.az/2", minutesAgo: 20)
        let old = item("3", "Eyni başlıq iki dəfə gəlib burada", source: "Lent.az", url: "https://lent.az/3", minutesAgo: 60 * 40)
        XCTAssertEqual(NewsPipeline.collapseExact([a, b, old]).count, 2)
    }

    func testNovelSkipsKnownLinksAndAlternatives() {
        var known = item("1", "Birinci")
        known.alts = [AltSource(source: "Oxu.az", sourceUrl: "https://oxu.az/alt")]
        let dup = item("2", "Təkrar", url: known.sourceUrl)
        let altDup = item("3", "Alternativ", url: "https://oxu.az/alt")
        let fresh = item("4", "Yeni")
        XCTAssertEqual(NewsPipeline.novel([dup, altDup, fresh], against: [known]).map(\.id), ["4"])
    }

    // MARK: - Şəkillər

    func testImageCandidatesSkipBrokenAndUpgradeHTTP() {
        var a = item("1", "Başlıq", image: "https://apa.az/storage/news/resize/")
        a.alts = [
            AltSource(source: "Oxu.az", sourceUrl: "https://oxu.az/1", imageUrl: "http://oxu.az/1.jpg"),
            AltSource(source: "Lent.az", sourceUrl: "https://lent.az/1", imageUrl: "data:image/png;base64,xx"),
        ]
        XCTAssertEqual(a.imageCandidates(og: ["https://lent.az/1": "https://lent.az/og.jpg"]).map(\.absoluteString),
                       ["https://oxu.az/1.jpg", "https://lent.az/og.jpg"])
    }

    func testGluedImageAddressIsRepaired() {
        let a = item("1", "Başlıq", image: "https://azpolitika.infohttps://cdn.az/1.jpg")
        XCTAssertEqual(a.imageCandidates().map(\.absoluteString), ["https://cdn.az/1.jpg"])
    }

    func testImageProxy() {
        let url = URL(string: "https://apa.az/şəkil 1.jpg?x=1".addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed)!)!
        XCTAssertTrue(ImageProxy.sized(url, width: 420)?.absoluteString.hasPrefix("https://wsrv.nl/?url=https%3A%2F%2Fapa.az%2F") ?? false)
        XCTAssertTrue(ImageProxy.sized(url, width: 420)?.absoluteString.hasSuffix("&w=420&we&output=webp&q=70") ?? false)
        XCTAssertNil(ImageProxy.sized(URL(string: "https://x.az/a.svg")!, width: 420))
    }

    // MARK: - Mətn

    func testTidy() {
        XCTAssertEqual(TextTools.tidy("Başlıq &amp;amp; digər&nbsp;mətn https://x.az/1 — "), "Başlıq & digər mətn")
        XCTAssertEqual(TextTools.tidy("&#1040;&#x411; test"), "АБ test")
        XCTAssertEqual(TextTools.tidy(nil), "")
    }

    func testFoldAndSearch() {
        XCTAssertEqual(TextTools.fold("Əliyev Şuşa ÇÖĞÜ"), "eliyev susa cogu")
        let list = [
            item("1", "İlham Əliyev Şuşada", minutesAgo: 30),
            item("2", "Şuşa haqqında", minutesAgo: 10),
            item("3", "Dollar bahalaşdı", minutesAgo: 5, summary: "Şuşa bazarı"),
        ]
        XCTAssertEqual(Ranking.search("ilham eliyev", in: list).first?.id, "1")
        XCTAssertEqual(Ranking.search("susa", in: list).map(\.id), ["2", "1", "3"])
        XCTAssertTrue(Ranking.search("x", in: list).isEmpty, "bir hərf axtarılmır")
    }

    func testClubMatching() {
        let a = item("1", "Qarabağın qələbəsi", category: "idman")
        let b = item("2", "International tournament", category: "idman")
        let c = item("3", "«Карабаха» победа", category: "idman", lang: "ru")
        XCTAssertTrue(Topics.matches(a, "Qarabağ"))
        XCTAssertFalse(Topics.matches(b, "İnter"))
        XCTAssertFalse(Topics.matches(c, "Neftçi"))
        XCTAssertTrue(Topics.matches(c, "Qarabağ"))
    }

    // MARK: - Sıralama

    func testHeroPrefersMostSourcesAndStaysDiverse() {
        var big = item("1", "Prezidentin səfəri barədə geniş məlumat yayılıb", minutesAgo: 120)
        big.alts = (0..<5).map { AltSource(source: "S\($0)", sourceUrl: "https://s\($0).az") }
        var twin = item("2", "Prezidentin səfəri barədə başqa məlumat", minutesAgo: 110)
        twin.alts = (0..<4).map { AltSource(source: "T\($0)", sourceUrl: "https://t\($0).az") }
        let others = (3..<9).map { item("\($0)", "Fərqli hadisə nömrə\($0)xxxx haqqında", minutesAgo: Double($0)) }
        let hero = Ranking.heroPick([twin, big] + others, need: 3, now: now)
        XCTAssertEqual(hero.first?.id, "1")
        XCTAssertFalse(hero.prefix(2).contains { $0.id == "2" }, "eyni hadisə təkrarlanmır")
    }

    func testPrezHomeKeepsBothGroupsAndCapsSources() {
        var list = (0..<6).map { item("p\($0)", "Prezident görüşdü \($0)", source: "Report", url: "https://report.az/\($0)", minutesAgo: Double($0 * 10), category: "prezident") }
        list.append(item("l1", "Mehriban Əliyeva tədbirdə", source: "Mehriban Əliyeva", url: "https://mehriban-aliyeva.az/1", minutesAgo: 600, category: "prezident"))
        list.append(item("o1", "Prezident kənar saytda", source: "Lent.az", url: "https://lent.az/1", category: "prezident"))
        let out = Ranking.prezHome(list, now: now)
        XCTAssertTrue(out.contains { $0.id == "l1" }, "Birinci xanım qrupu görünür")
        XCTAssertFalse(out.contains { $0.id == "o1" }, "adı keçməyən yad xəbər blokda yoxdur")
        XCTAssertEqual(out.first?.source, "Report")
    }

    func testPrezHomeFillsTo44WithOurLeadersOnly() {
        var list = (0..<60).map { item("o\($0)", "İlham Əliyev görüşdü \($0)", source: "Lent.az", url: "https://lent.az/\($0)", minutesAgo: Double($0), category: "prezident") }
        list.append(item("y1", "Prezident Tramp bəyanat verib", source: "Lent.az", url: "https://lent.az/y1", category: "prezident"))
        let out = Ranking.prezHome(list, now: now)
        XCTAssertEqual(out.count, 44)
        XCTAssertFalse(out.contains { $0.id == "y1" })
    }

    // MARK: - Bölmələr və ölü linklər

    func testMergedSectionsMoveToTheNewOne() {
        XCTAssertEqual(item("1", "Başlıq", category: "sehiyye").category, "heyat")
        XCTAssertEqual(item("2", "Başlıq", category: "texnologiya").category, "tehsil")
        XCTAssertEqual(Catalog.category("sehiyye")?.slug, "heyat")
        XCTAssertNotNil(Catalog.category("sosial"))
    }

    func testDeadLinkMovesToNextSourceOrDisappears() {
        var a = item("1", "Birinci", url: "https://a.az/1")
        a.alts = [AltSource(source: "Oxu.az", sourceUrl: "https://oxu.az/1", title: "Oxu başlığı")]
        let b = item("2", "İkinci", url: "https://a.az/2")
        let c = item("3", "Üçüncü", url: "https://a.az/3")
        let out = NewsPipeline.dropDead([a, b, c], dead: ["https://a.az/1", "https://a.az/2"])
        XCTAssertEqual(out.map(\.id), ["1", "3"])
        XCTAssertEqual(out[0].source, "Oxu.az")
        XCTAssertEqual(out[0].cleanTitle, "Oxu başlığı")
        XCTAssertTrue(out[0].alts.isEmpty)
    }

    func testLatestFillsMissingImage() {
        var raw = [item("1", "Birinci", url: "https://a.az/1")]
        let latest = [item("1", "Birinci", url: "https://a.az/1", image: "https://a.az/1.jpg")]
        XCTAssertTrue(NewsPipeline.fillImages(from: latest, into: &raw))
        XCTAssertEqual(raw[0].imageUrl, "https://a.az/1.jpg")
        XCTAssertFalse(NewsPipeline.fillImages(from: latest, into: &raw))
    }

    func testArchiveAddsOnlyUnknownLinks() {
        let list = [item("1", "Birinci", url: "https://a.az/1")]
        let rows = [item("1", "Birinci", url: "https://a.az/1"), item("2", "İkinci", url: "https://a.az/2")]
        XCTAssertEqual(NewsPipeline.withArchive(list, rows: rows).map(\.id), ["1", "2"])
    }

    func testRegionSearchesEveryArchiveButSkipsSport() {
        let local = item("1", "Şəkidə yeni məktəb açılıb", category: "tehsil")
        let sport = item("2", "Şəki komandası qalib gəlib", category: "idman")
        let out = Ranking.section("bolgeler", club: "Şəki", articles: [sport], archives: ["tehsil": [local]], language: "az", now: now)
        XCTAssertEqual(out.map(\.id), ["1"])
    }

    func testShareLinkLeadsToTheSite() {
        XCTAssertEqual(item("abc", "Başlıq", category: "idman").shareURL?.absoluteString, "https://8ulduz.az/#/xeber/abc?b=idman")
    }

    func testRoadItems() {
        let list = [
            item("1", "Bakıda yol qəzası baş verib", minutesAgo: 30),
            item("2", "Gəncədə yol qəzası baş verib", minutesAgo: 30),
            item("3", "Bakıda qəza oldu", minutesAgo: 60 * 5),
            item("4", "Bakıda dəmir yolu qəzası", minutesAgo: 30),
        ]
        XCTAssertEqual(Ranking.localRoadItems(list, now: now).map(\.article.id), ["1"])
    }

    func testRushHourUsesBakuTime() {
        XCTAssertTrue(Ranking.bakuRushHour(ISODate.parse("2026-10-30T05:00:00+00:00")!), "cümə 09:00 Bakı")
        XCTAssertFalse(Ranking.bakuRushHour(ISODate.parse("2026-10-31T05:00:00+00:00")!), "şənbə")
        XCTAssertFalse(Ranking.bakuRushHour(ISODate.parse("2026-10-30T09:00:00+00:00")!), "cümə 13:00 Bakı")
    }

    // MARK: - Bazar və format

    func testConverter() {
        let items = [
            MarketItem(id: "USD", label: "Dollar", unit: "AZN", value: 1.7),
            MarketItem(id: "RUB100", label: "100 Rubl", unit: "AZN", value: 2.0),
            MarketItem(id: "XAU", label: "Qızıl", unit: "USD", value: 2000),
        ]
        XCTAssertEqual(Converter.convert(100, from: "USD", to: "AZN", items: items), 170)
        XCTAssertEqual(Converter.convert(100, from: "RUB100", to: "AZN", items: items), 2)
        XCTAssertEqual(Converter.convert(1, from: "XAU", to: "USD", items: items), 2000)
        XCTAssertNil(Converter.convert(1, from: "YOX", to: "AZN", items: items))
    }

    func testUnofficialRateHasNoChange() {
        let official = MarketItem(id: "USD", label: "Dollar", unit: "AZN", value: 1.7, change: 0, changePct: 0, src: "AMB")
        let market = MarketItem(id: "USD", label: "Dollar", unit: "AZN", value: 1.7, change: 0, changePct: 0, src: "ExchangeRate-API")
        XCTAssertTrue(official.hasChange)
        XCTAssertFalse(market.hasChange)
        XCTAssertTrue(market.isUnofficial)
    }

    func testFormatting() {
        XCTAssertEqual(Format.ago(now.addingTimeInterval(-20), now: now), "indicə")
        XCTAssertEqual(Format.ago(now.addingTimeInterval(-300), now: now), "5 dəqiqə əvvəl")
        XCTAssertEqual(Format.ago(now.addingTimeInterval(-7200), now: now), "2 saat əvvəl")
        XCTAssertEqual(Format.ago(now.addingTimeInterval(-86400 * 3), now: now), "3 gün əvvəl")
        XCTAssertEqual(Format.ordinal("9"), "9-cu")
        XCTAssertEqual(Format.ordinal("10"), "10-cu")
        XCTAssertEqual(Format.ordinal("3"), "3-cü")
        XCTAssertEqual(Format.ordinal("6"), "6-cı")
        XCTAssertEqual(Format.number(1.7, decimals: 4), "1.70")
        XCTAssertEqual(Format.number(1.9019, decimals: 4), "1.9019")
        XCTAssertEqual(Format.number(75432.5, decimals: 0), "75,433")
    }

    func testDates() {
        XCTAssertNotNil(ISODate.parse("2026-10-31T02:40:26.950704+00:00"))
        XCTAssertNotNil(ISODate.parse("2026-10-31T02:39:13+00:00"))
        XCTAssertEqual(ISODate.parse("2026-10-31T17:30+04:00"), ISODate.parse("2026-10-31T13:30:00Z"))
        XCTAssertNil(ISODate.parse("sabah"))
    }

    func testInterfaceLanguageChangesDates() {
        Format.language = "en"
        defer { Format.language = "az" }
        XCTAssertEqual(Format.ago(now.addingTimeInterval(-300), now: now), "5 min ago")
        XCTAssertEqual(Format.round("9"), "Round 9")
        XCTAssertTrue(Format.monthTitle("2026-10-31T12:00:00+00:00").hasPrefix("October"))
    }

    func testBadRowDoesNotBreakTheFeed() throws {
        let json = #"{"articles":[{"title":"id yoxdur"},{"id":"1","title":"Yaxşı","imageUrl":null,"video":false},42]}"#
        let feed = try JSONDecoder().decode(NewsFeed.self, from: Data(json.utf8))
        XCTAssertEqual(feed.articles.map(\.id), ["1"])
        XCTAssertThrowsError(try JSONDecoder().decode(NewsFeed.self, from: Data(#"{"offline":true}"#.utf8)))
    }
}
