import XCTest
@testable import UlduzCore

/// Saytın mövzu qaydaları (assets/app.js `clubMatches`) və komanda məntiqi (assets/komanda.js).
final class TopicTests: XCTestCase {
    private func article(_ title: String, summary: String = "", source: String = "APA", category: String = "idman") -> Article {
        Article(id: title, title: title, summary: summary, category: category, source: source, sourceUrl: "https://apa.az/\(title.count)", publishedAt: "2026-11-01T10:00:00+00:00")
    }

    private func decode<T: Decodable>(_ json: String) throws -> T { try JSONDecoder().decode(T.self, from: Data(json.utf8)) }

    func testListsMatchTheSite() throws {
        let app = try String(contentsOf: RepoFiles.root.appendingPathComponent("assets/app.js"), encoding: .utf8)
        func check(_ topic: Topic) {
            XCTAssertTrue(app.contains("name: \"\(topic.name)\""), "\(topic.name) saytda yoxdur")
            topic.groups.flatMap(\.items).forEach(check)
        }
        XCTAssertFalse(Topics.sportTabs.isEmpty)
        XCTAssertFalse(Topics.regionTabs.isEmpty)
        (Topics.sportTabs + Topics.regionTabs).forEach(check)
        let tabs = app.components(separatedBy: "const REGION_TABS = [").last?.components(separatedBy: "];").first ?? ""
        XCTAssertEqual(tabs.components(separatedBy: "\n  { name: ").count - 1, Topics.regionTabs.count, "bölgə sayı saytla eyni deyil")
    }

    func testSabahIsAClubOnlyInQuotesOrWithFK() {
        XCTAssertFalse(Topics.matches(article("Sabah oyun keçiriləcək"), "Sabah"), "«sabah» sözü həm də tomorrow deməkdir")
        XCTAssertTrue(Topics.matches(article("«Sabah» qalib gəlib"), "Sabah"))
        XCTAssertTrue(Topics.matches(article("Sabah FK məşqçisi danışıb"), "Sabah"))
    }

    func testExclusionsAndSuffixes() {
        XCTAssertTrue(Topics.matches(article("Neftçinin qələbəsi"), "Neftçi") || Topics.matches(article("Neftçi qalib gəlib"), "Neftçi"))
        XCTAssertFalse(Topics.matches(article("Inter Miami qalib gəlib"), "İnter"))
        XCTAssertFalse(Topics.matches(article("Qarabağ universiteti açılıb"), "Qarabağ"))
    }

    func testFootballCoversItsTeamsAndSkipsBasket() {
        XCTAssertTrue(Topics.matches(article("Barcelona qalib gəlib"), "Futbol"), "alt bölmə düymələrinin xəbərlərini də əhatə edir")
        XCTAssertFalse(Topics.matches(article("Futbol və basketbol yarışı"), "Futbol"))
        XCTAssertTrue(Topics.matches(article("Yazı", source: "BBC Futbol"), "Futbol"), "mövzunun öz saytı")
    }

    func testTransferSplit() {
        let basket = article("LeBron transfer xəbəri, NBA")
        XCTAssertTrue(Topics.matches(basket, "Basketbol transferləri"))
        XCTAssertFalse(Topics.matches(basket, "Futbol transferləri"))
        XCTAssertFalse(Topics.matches(article("Pul transfer edilib"), "Transfer xəbərləri"))
    }

    func testRegionHasItsOwnQarabagh() {
        let city = article("Xankəndidə yeni bina açılıb", category: "gundem")
        XCTAssertTrue(Topics.matches(city, "Qarabağ", scope: .region), "bölgə düyməsi şəhərlərini əhatə edir")
        XCTAssertFalse(Topics.matches(city, "Qarabağ"), "komanda düyməsi yox")
        XCTAssertFalse(Topics.matches(article("Qazaxıstan prezidenti", category: "dunya"), "Qazax", scope: .region))
    }

    func testSearchFindsTeamInAnySpelling() {
        XCTAssertEqual(Topics.searchTopics("barselona"), ["Barcelona"])
        XCTAssertTrue(Topics.searchTopics("hava proqnozu").isEmpty)
        let ru = Article(id: "1", title: "Барселона выиграла", category: "idman", source: "Sport.ru", sourceUrl: "https://sport.ru/1", publishedAt: "2026-11-01T10:00:00+00:00", lang: "ru")
        XCTAssertEqual(Ranking.search("barselona", in: [ru], language: "az").map(\.id), ["1"], "komanda axtarışı bütün dillərdə")
    }

    func testTeamSlugMatchesTheSite() {
        XCTAssertEqual(Topics.slug("Premyer Liqa"), "premyer-liqa")
        XCTAssertEqual(Topics.slug("Əvəzedicilər"), "evezediciler")
        XCTAssertEqual(Topics.slug("ÇL"), "cl")
        XCTAssertEqual(Topics.slug("Turan Tovuz"), "turan-tovuz")
    }

    func testTeamTopicAndName() {
        XCTAssertEqual(Topics.teamTopic("Internazionale"), "İnter")
        XCTAssertEqual(Topics.teamTopic("Real Madrid"), "Real Madrid")
        XCTAssertNil(Topics.teamTopic("Nice"))
        let rx = TeamNews.nameRx(["Nice"])
        XCTAssertEqual(rx?.test("Nice qalib gəlib"), true)
        XCTAssertEqual(rx?.test("a nice goal"), false, "böyük hərf saxlanır")
    }

    private let league = #"""
    {"id":"x","name":"Liqa","short":"X","source":"pfl.az","season":"2026-27","asof":"2026-10-31",
     "teams":{"a":{"name":"A klubu","logo":""},"b":{"name":"B klubu","logo":""}},
     "groups":[{"name":"","rows":[{"pos":1,"team":"a","p":2,"w":1,"d":1,"l":0,"gf":3,"ga":1,"gd":2,"pts":4,"color":"#BBF3BB","note":"Champions League"},{"pos":2,"team":"b","p":2,"w":0,"d":1,"l":1,"gf":1,"ga":3,"gd":-2,"pts":1}]}],
     "games":[{"home":"a","away":"b","hs":2,"as":0,"date":"2026-08-14T19:30+04:00","played":true,"round":"1"},
              {"home":"b","away":"a","hs":1,"as":1,"date":"2026-09-14T19:30+04:00","played":true,"round":"2"},
              {"home":"a","away":"b","date":"2099-01-01T19:30:00+00:00","played":false,"round":"3"},
              {"home":"b","away":"a","date":"2020-01-01T19:30:00+00:00","played":false,"round":"4","state":"off"},
              {"home":"b","away":"a","date":"2020-02-01T19:30:00+00:00","played":false,"round":"5"}]}
    """#

    func testLeagueLogic() throws {
        let doc: LeagueDoc = try decode(league)
        XCTAssertEqual(doc.form(of: "a"), [.win, .draw])
        XCTAssertEqual(doc.form(of: "b"), [.loss, .draw])
        XCTAssertEqual(doc.row(of: "b")?.row.pos, 2)
        XCTAssertEqual(doc.neighbours(of: "a").map(\.team), ["a", "b"])
        XCTAssertEqual(LeagueDoc.zones(doc.groups[0].rows).first?.note, "Çempionlar Liqası")
        let split = TeamGames.split(doc.games(of: "a"))
        XCTAssertEqual(split.played.count, 2)
        XCTAssertEqual(split.next.map(\.round), ["3"], "təxirə salınan və nəticəsi gəlməyən oyun qarşıdakı deyil")
        XCTAssertEqual(doc.games[3].stateText(), "Təxirə salınıb")
        XCTAssertEqual(doc.games[4].stateText(), "Nəticə gözlənilir")
        XCTAssertEqual(doc.games[0].roundText, "1-ci tur")
        XCTAssertEqual(TeamGames.byMonth(doc.games).last?.title, "Yanvar 2099")
        XCTAssertEqual(doc.asOfText, "31 oktyabr oyunlarına qədər")
    }

    func testLeagueFilePath() throws {
        let entry: TeamLeague = try decode(#"{"id":"x","ready":[{"key":"2026","label":"2026-27"},{"key":"2025","label":"2025-26"}],"teams":["a"]}"#)
        XCTAssertEqual(entry.path(), "futbol/x.json")
        XCTAssertEqual(entry.path(season: "2026"), "futbol/x.json")
        XCTAssertEqual(entry.path(season: "2025"), "futbol/x-2025.json")
    }

    func testReserveTeamsDoNotMix() throws {
        let index: TeamIndex = try decode(#"""
        {"leagues":[{"id":"l","ready":[{"key":"1"}],"teams":["a"]},{"id":"k","cup":true,"ready":[{"key":"1"}],"teams":["a"]},
        {"id":"r","reserve":true,"ready":[{"key":"1"}],"teams":["a"]},{"id":"bos","ready":[],"teams":["a"]}]}
        """#)
        XCTAssertNil(index.league("bos"), "hazır mövsümü olmayan liqa açılmır")
        XCTAssertEqual(index.otherLeagues(try XCTUnwrap(index.league("l")), team: "a").map(\.id), ["k"])
        XCTAssertTrue(index.otherLeagues(try XCTUnwrap(index.league("r")), team: "a").isEmpty)
    }
}
