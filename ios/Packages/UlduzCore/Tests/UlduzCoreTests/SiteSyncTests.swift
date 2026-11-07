import XCTest
@testable import UlduzCore

/// Saytın 2026-11 dəyişiklikləri: dil faylları, silinmiş xəbərlər, paylaşma səhifəsi, reklam, «Konumum», Zuğulba.
final class SiteSyncTests: XCTestCase {
    private func decode<T: Decodable>(_ type: T.Type, _ json: String) throws -> T {
        try JSONDecoder().decode(T.self, from: Data(json.utf8))
    }

    private func policy() throws -> ContentPolicy {
        let text = try String(contentsOf: RepoFiles.root.appendingPathComponent("assets/content-policy.js"), encoding: .utf8)
        return try ContentPolicy(javascript: text)
    }

    // MARK: - Silinmiş xəbərlər

    /// Sahibin sildirdiyi xəbər qayda faylındadır: id, keçid və eyni nömrəli başqa keçid də düşür.
    func testRemovedArticlesFromThePolicyFile() throws {
        let p = try policy()
        XCTAssertTrue(p.isRemoved(id: "5e6cc2e84ced07dd", url: "https://example.com/x"))
        XCTAssertTrue(p.isRemoved(id: nil, url: "https://nocomment.az/cemiyyet/nazirlik-bu-sexleri-hedefe-goturdu-900-1000-civarinda-pensiya-alanlar-sok-iddia-555222"))
        XCTAssertTrue(p.isRemoved(id: nil, url: "https://www.nocomment.az/cemiyyet/basqa-basliq-555222"))
        XCTAssertFalse(p.isRemoved(id: nil, url: "https://nocomment.az/cemiyyet/basqa-xeber-555223"))
        let row = Article(id: "5e6cc2e84ced07dd", title: "Başlıq", source: "Nocomment.az", sourceUrl: "https://nocomment.az/cemiyyet/yeni-555999")
        XCTAssertTrue(p.violation(row))
        XCTAssertTrue(p.clean([row]).isEmpty)
    }

    /// Dəqiqəlik lentin `removed` sahəsi: tətbiq yenilənmədən xəbər dərhal düşür, alt mənbə də.
    func testLiveRemovals() throws {
        var p = try policy()
        let feed = try decode(NewsFeed.self, #"{"articles":[],"removed":{"oxu.az#123456":{"id":"abc","urls":["https://apa.az/1"],"key":"oxu.az#123456"},"pis":5}}"#)
        XCTAssertEqual(feed.removed.count, 1)
        XCTAssertTrue(p.addRemovals(feed.removed))
        XCTAssertFalse(p.addRemovals(feed.removed), "eyni siyahı ikinci dəfə dəyişiklik sayılmır")
        XCTAssertTrue(p.isRemoved(id: "abc", url: ""))
        XCTAssertTrue(p.isRemoved(id: nil, url: "https://apa.az/1"))
        XCTAssertTrue(p.isRemoved(id: nil, url: "https://oxu.az/xeber/bir-sey-123456"))
        XCTAssertTrue(p.isRemoved(id: nil, url: "https://oxu.az/xeber/bir-sey-123456.html"))
        XCTAssertFalse(p.isRemoved(id: nil, url: "https://oxu.az/xeber/20261106/basqa-777777"), "tarix nömrə sayılmır, son nömrə fərqlidir")
        let alt = AltSource(source: "Oxu.az", sourceUrl: "https://oxu.az/a-123456")
        let main = Article(id: "z", title: "Başlıq", source: "APA", sourceUrl: "https://apa.az/xeber/2", alts: [alt])
        XCTAssertTrue(p.clean([main]).first?.alts.isEmpty ?? false, "silinmiş alt mənbə kartdan çıxır")
    }

    // MARK: - Dil faylları

    func testNewsFilesPerLanguage() throws {
        let status = try decode(FeedStatus.self, #"{"checkedAt":"2026-11-06T17:17:24+00:00","ok":true,"langs":["az","en"],"newsLangs":["en","ru"]}"#)
        XCTAssertEqual(status.newsFiles(language: "az"), ["news.json"])
        XCTAssertEqual(status.newsFiles(language: "en"), ["news.en.json"])
        XCTAssertEqual(status.newsFiles(language: "tr"), ["news.json"], "faylı olmayan dil ümumi fayldan")
        XCTAssertEqual(status.newsFiles(language: ""), ["news.json", "news.en.json", "news.ru.json"])
        XCTAssertEqual(status.latestFile(language: "az"), "latest.az.json")
        XCTAssertNil(status.latestFile(language: "ru"))
        XCTAssertNil(status.latestFile(language: ""))
    }

    /// Real fayllar: status-da adı çəkilən hər dil faylı oxunur və yalnız həmin dildədir.
    func testRealLanguageFiles() throws {
        let data = RepoFiles.root.appendingPathComponent("data")
        let status = try JSONDecoder().decode(FeedStatus.self, from: Data(contentsOf: data.appendingPathComponent("status.json")))
        XCTAssertFalse(status.newsLangs.isEmpty)
        for code in status.newsLangs {
            let feed = try JSONDecoder().decode(NewsFeed.self, from: Data(contentsOf: data.appendingPathComponent("news.\(code).json")))
            XCTAssertFalse(feed.articles.isEmpty, code)
            XCTAssertTrue(feed.articles.allSatisfy { $0.language == code }, code)
        }
    }

    func testLiveChannelFiles() {
        XCTAssertTrue(FeedClient.isLiveFile("latest.json"))
        XCTAssertTrue(FeedClient.isLiveFile("latest.en.json"))
        XCTAssertTrue(FeedClient.isLiveFile("status.json"))
        XCTAssertFalse(FeedClient.isLiveFile("news.en.json"), "news.<dil>.json main-dədir")
        XCTAssertFalse(FeedClient.isLiveFile("latest.json/../x"))
        XCTAssertTrue(FeedClient.isStaleChecked("news.ru.json"))
        XCTAssertFalse(FeedClient.isStaleChecked("markets.json"))
    }

    // MARK: - Paylaşma

    func testSharePageLink() throws {
        let feed = try decode(NewsFeed.self, #"{"sharePages":true,"articles":[{"id":"0123456789abcdef","title":"t","category":"gundem","sourceUrl":"https://a.az/1"},{"id":"nohex","title":"t","category":"gundem","sourceUrl":"https://a.az/2"}]}"#)
        XCTAssertEqual(feed.articles[0].shareURL?.absoluteString, "https://8ulduz.az/x/0123456789abcdef")
        XCTAssertEqual(feed.articles[1].shareURL?.absoluteString, "https://8ulduz.az/#/xeber/nohex?b=gundem")
        let live = try decode(NewsFeed.self, #"{"articles":[{"id":"0123456789abcdef","title":"t","category":"gundem","sourceUrl":"https://a.az/1"}]}"#)
        XCTAssertEqual(live.articles[0].shareURL?.absoluteString, "https://8ulduz.az/#/xeber/0123456789abcdef?b=gundem", "dəqiqəlik xəbərin hələ səhifəsi yoxdur")
    }

    // MARK: - Reklam

    func testAdSlotsNeedImageAndLink() throws {
        let feed = try decode(AdsFeed.self, #"{"slots":[{"image":"https://a.az/b.png","link":"https://a.az","alt":"A"},{"image":"https://a.az/c.png"},{"image":"javascript:x","link":"https://a.az"}]}"#)
        XCTAssertEqual(feed.slots.map(\.alt), ["A"])
        XCTAssertTrue(try decode(AdsFeed.self, #"{"slots":[]}"#).slots.isEmpty)
    }

    // MARK: - Konumum

    func testNearestCity() {
        XCTAssertEqual(Catalog.nearestCity(lat: 40.41, lon: 49.87)?.name, "Bakı")
        XCTAssertEqual(Catalog.nearestCity(lat: 40.68, lon: 46.36)?.name, "Gəncə")
        XCTAssertNil(Catalog.nearestCity(lat: 41.01, lon: 28.97), "xaricdə şəhər seçilmir")
    }

    func testFollowLinksAreOfficialHttps() {
        XCTAssertFalse(Catalog.followLinks.isEmpty)
        for item in Catalog.followLinks {
            XCTAssertEqual(item.link?.scheme, "https", item.label)
        }
    }

    // MARK: - Zuğulba

    /// 44 öz dilindən dolmayanda başqa dilin xəbəri sona qoyulur, daha yeni olsa da önə keçmir.
    func testPrezFillsOtherLanguagesLast() {
        let now = Date()
        func stamp(_ minutesAgo: Double) -> String { ISO8601DateFormatter().string(from: now.addingTimeInterval(-minutesAgo * 60)) }
        let az = Article(id: "az1", title: "Prezident İlham Əliyev qəbul etdi", category: "prezident", source: "Prezident.az",
                         sourceUrl: "https://president.az/1", publishedAt: stamp(60), lang: "az")
        let ru = Article(id: "ru1", title: "Ильхам Алиев принял делегацию", category: "prezident", source: "Report",
                         sourceUrl: "https://report.az/ru/1", publishedAt: stamp(5), lang: "ru")
        let picked = Ranking.prezHome([az], all: [az, ru], now: now)
        XCTAssertEqual(picked.map(\.id), ["az1", "ru1"])
        XCTAssertEqual(Ranking.prezHome([az], now: now).map(\.id), ["az1"])
    }
}
