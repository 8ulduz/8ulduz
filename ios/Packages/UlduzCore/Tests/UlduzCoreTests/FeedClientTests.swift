import XCTest
@testable import UlduzCore

/// QIRMIZI XƏTT 1: tətbiq saytla eyni zənciri işlədir (sw.js): canlı kanal, sayt, ehtiyat kanal, keş.
final class FeedClientTests: XCTestCase {
    private let status = #"{"checkedAt":"2026-10-31T10:00:00+00:00","ok":true,"degraded":false}"#
    private let fixedNow = Date(timeIntervalSince1970: 1_800_000_000)

    private final class Log: @unchecked Sendable {
        private let lock = NSLock()
        private var items: [String] = []
        func add(_ s: String) { lock.lock(); items.append(s); lock.unlock() }
        var all: [String] { lock.lock(); defer { lock.unlock() }; return items }
    }

    private func store() -> DiskStore {
        DiskStore(directory: FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString))
    }

    private func response(_ request: URLRequest, _ code: Int, headers: [String: String] = [:]) -> HTTPURLResponse {
        HTTPURLResponse(url: request.url!, statusCode: code, httpVersion: nil, headerFields: headers)!
    }

    private func client(store: DiskStore, log: Log, answer: @escaping @Sendable (String) -> (Int, String?, [String: String])) -> FeedClient {
        let now = fixedNow
        return FeedClient(store: store, transport: { request in
            let url = request.url!.absoluteString
            log.add(url)
            let (code, body, headers) = answer(url)
            guard let body else { throw URLError(.notConnectedToInternet) }
            return (Data(body.utf8), HTTPURLResponse(url: request.url!, statusCode: code, httpVersion: nil, headerFields: headers)!)
        }, now: { now })
    }

    private var slot: Int { Int(floor((fixedNow.timeIntervalSince1970 - 45) / 60)) }

    func testLiveChannelComesFirstAndUsesTheMinutePath() async throws {
        let log = Log(), body = status
        let c = client(store: store(), log: log) { _ in (200, body, [:]) }
        let loaded = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(loaded.origin, .live)
        XCTAssertEqual(log.all, ["https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/\(slot)/status.json"])
    }

    func testFullFeedSkipsTheLiveChannel() async throws {
        let log = Log()
        let c = client(store: store(), log: log) { _ in (200, #"{"articles":[]}"#, [:]) }
        let loaded = try await c.load("news.json", as: NewsFeed.self)
        XCTAssertEqual(loaded.origin, .site)
        XCTAssertEqual(log.all.count, 1)
        XCTAssertTrue(log.all[0].hasPrefix("https://8ulduz.az/data/news.json?t="))
    }

    func testMissingMinuteFallsBackToOlderMinuteThenSite() async throws {
        let log = Log(), body = status, older = slot - 1
        let c = client(store: store(), log: log) { url in
            url.contains("/m/\(older)/") ? (200, body, [:]) : (404, "", [:])
        }
        let loaded = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(loaded.origin, .live)
        XCTAssertEqual(log.all.count, 2)
    }

    func testRateLimitPausesTheLiveChannel() async throws {
        let log = Log(), body = status
        let c = client(store: store(), log: log) { url in
            url.contains("/live/m/") ? (429, "", [:]) : (200, body, [:])
        }
        let first = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(first.origin, .site)
        let second = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(second.origin, .site)
        XCTAssertEqual(log.all.filter { $0.contains("/live/m/") }.count, 1, "429-dan sonra canlı kanal 5 dəqiqə sınanmır")
    }

    func testSiteDownUsesMirror() async throws {
        let log = Log(), body = status
        let c = client(store: store(), log: log) { url in
            url.contains("raw.githubusercontent.com/8ulduz/8ulduz/main/") ? (200, body, [:]) : (0, nil, [:])
        }
        let loaded = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(loaded.origin, .mirror)
    }

    func testStuckPagesPrefersMirror() async throws {
        let log = Log(), body = status
        let c = client(store: store(), log: log) { url in
            if url.contains("/live/m/") { return (404, "", [:]) }
            return (200, body, ["Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"])
        }
        let loaded = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(loaded.origin, .mirror)
    }

    func testBrokenBodyMovesToNextChannel() async throws {
        let log = Log(), body = status
        let c = client(store: store(), log: log) { url in
            url.contains("8ulduz.az/data/") ? (200, body, [:]) : (200, "<html>rate limited</html>", [:])
        }
        let loaded = try await c.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(loaded.origin, .site)
    }

    func testEverythingDownServesTheCache() async throws {
        let disk = store(), body = status
        let online = client(store: disk, log: Log()) { _ in (200, body, [:]) }
        _ = try await online.load("status.json", as: FeedStatus.self)
        let offline = client(store: disk, log: Log()) { _ in (0, nil, [:]) }
        let loaded = try await offline.load("status.json", as: FeedStatus.self)
        XCTAssertEqual(loaded.origin, .cache)
    }

    func testNothingAtAllThrows() async {
        let c = client(store: store(), log: Log()) { _ in (0, nil, [:]) }
        do {
            _ = try await c.load("status.json", as: FeedStatus.self)
            XCTFail("keş boş olanda xəta gözlənilir")
        } catch {}
    }

    func testPolicyRefreshKeepsLastGoodRules() async throws {
        let disk = store()
        let good = #"window.CONTENT_POLICY = {"azSources":{"APA":["apa.az"]},"worldSources":{},"blockedHosts":[],"azTerms":"x","leaderTerms":"y"};"#
        let online = client(store: disk, log: Log()) { _ in (200, good, [:]) }
        let fresh = await online.refreshPolicy()
        XCTAssertNotNil(fresh)
        let broken = client(store: disk, log: Log()) { _ in (200, "<html></html>", [:]) }
        let none = await broken.refreshPolicy()
        XCTAssertNil(none)
        let cached = await broken.cachedPolicy()
        XCTAssertNotNil(cached)
    }
}
