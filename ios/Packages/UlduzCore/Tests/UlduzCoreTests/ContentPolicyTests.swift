import XCTest
@testable import UlduzCore

/// QIRMIZI XƏTT 2: tests/test_red_lines.py və tests/browser-logic.test.cjs-dəki hallar burada da eyni nəticə verməlidir.
final class ContentPolicyTests: XCTestCase {
    private func policy() throws -> ContentPolicy {
        let text = try String(contentsOf: RepoFiles.root.appendingPathComponent("assets/content-policy.js"), encoding: .utf8)
        return try ContentPolicy(javascript: text)
    }

    private func row(_ source: String, _ url: String, _ title: String, _ category: String = "dunya", summary: String = "") -> Article {
        Article(id: UUID().uuidString, title: title, summary: summary, category: category, source: source, sourceUrl: url)
    }

    func testSameCasesAsTheBrowser() throws {
        let p = try policy()
        XCTAssertTrue(p.violation(row("BBC News", "https://bbc.co.uk/1", "Azerbaijan to transfer detainees", "idman")))
        XCTAssertFalse(p.violation(row("Match TV", "https://matchtv.ru/1", "Карабах вышел в плей-офф", "idman")))
        XCTAssertTrue(p.violation(row("Match TV", "https://matchtv.ru/1", "Алиев поздравил футболистов", "idman")))
        XCTAssertTrue(p.violation(row("Hürriyet", "https://hurriyet.com.tr/1", "ALİYEV açıklama yaptı")))
        XCTAssertFalse(p.violation(row("Hürriyet", "https://hurriyet.com.tr/1", "Bakırköy'de kaza")))
        XCTAssertTrue(p.violation(row("AZƏRTAC", "javascript://azertag.az/%0aalert(1)", "Başlıq")))
    }

    func testForeignSourcesDoNotReportOnAzerbaijan() throws {
        let p = try policy()
        XCTAssertTrue(p.violation(row("TASS", "https://tass.ru/1", "Переговоры", summary: "Встреча прошла в Баку")))
        XCTAssertTrue(p.violation(row("BBC News", "https://bbc.com/1", "Talks held in Baku")))
        XCTAssertTrue(p.violation(row("Euronews", "https://euronews.com/1", "BAKI görüşü")))
        XCTAssertFalse(p.violation(row("BBC News", "https://bbc.com/2", "Elections in France")))
    }

    func testSportExceptionBelongsToSportSitesOnly() throws {
        let p = try policy()
        XCTAssertTrue(p.violation(row("BBC News", "https://bbc.com/3", "Qarabağ wins in Europe", "idman")))
        XCTAssertFalse(p.violation(row("NTV Spor", "https://ntvspor.net/3", "Karabağ kazandı", "idman")))
    }

    func testAllowlistAndLinks() throws {
        let p = try policy()
        XCTAssertFalse(p.violation(row("APA", "https://apa.az/1", "Azərbaycan Prezidenti qəbul edib", "siyaset")))
        XCTAssertFalse(p.violation(row("APA", "https://www.apa.az/1", "Başlıq", "siyaset")))
        XCTAssertTrue(p.violation(row("Naməlum", "https://example.com/1", "Başlıq")), "siyahıda olmayan mənbə düşür")
        XCTAssertTrue(p.violation(row("APA", "https://example.com/1", "Başlıq")), "keçid mənbənin öz saytına aparmalıdır")
        XCTAssertTrue(p.violation(row("APA", "https://apa.az.example.com/1", "Başlıq")))
        XCTAssertTrue(p.violation(row("APA", "https://meydan.tv/1", "Başlıq")), "qadağan sayt")
        XCTAssertTrue(p.violation(row("Azadlıq", "https://azadliq.org/1", "Başlıq")))
        XCTAssertFalse(p.allowsExternalLink("https://meydan.tv/x"))
        XCTAssertFalse(p.allowsExternalLink("https://example.com/x"))
        XCTAssertTrue(p.allowsExternalLink("https://oxu.az/x"))
    }

    func testAlternativesAreCheckedToo() throws {
        let p = try policy()
        var a = row("BBC News", "https://bbc.com/9", "Talks in Paris")
        a.alts = [
            AltSource(source: "TASS", sourceUrl: "https://tass.ru/9", title: "Переговоры с Азербайджаном"),
            AltSource(source: "Al Jazeera", sourceUrl: "https://aljazeera.com/9", title: "Talks in Paris"),
            AltSource(source: "Oxu.az", sourceUrl: "https://oxu.az/9", title: "Parisdə danışıqlar"),
            AltSource(source: "Xəyali", sourceUrl: "https://meydan.tv/9", title: "Talks"),
        ]
        let cleaned = p.clean([a])
        XCTAssertEqual(cleaned.first?.alts.map(\.source), ["Al Jazeera", "Oxu.az"])
    }

    func testBrokenRuleFileLetsNothingThrough() {
        XCTAssertThrowsError(try ContentPolicy(javascript: "window.CONTENT_POLICY = {"))
        let p = ContentPolicy.failClosed
        XCTAssertTrue(p.violation(row("APA", "https://apa.az/1", "Başlıq", "siyaset")))
    }

    func testEveryPublishedArticlePasses() throws {
        // Server qapısından keçmiş real lent tətbiqin qapısında da boşalmamalıdır.
        let feed = try JSONDecoder().decode(NewsFeed.self, from: Data(contentsOf: RepoFiles.root.appendingPathComponent("data/news.json")))
        let p = try policy()
        let kept = p.clean(feed.articles)
        XCTAssertGreaterThan(feed.articles.count, 100)
        XCTAssertGreaterThan(Double(kept.count) / Double(feed.articles.count), 0.9, "regex mühərriki saytdan fərqli işləyir")
    }
}

enum RepoFiles {
    /// ios/Packages/UlduzCore/Tests/UlduzCoreTests/<fayl> → repo kökü.
    static var root: URL {
        var url = URL(fileURLWithPath: #filePath)
        for _ in 0..<6 { url.deleteLastPathComponent() }
        return url
    }
}
