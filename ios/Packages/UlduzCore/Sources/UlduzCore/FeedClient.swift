import Foundation

/// Paylaşılan yaddaş: tətbiq və vidcet eyni keşi görür. App Group yoxdursa (imzasız simulyator) tətbiqin öz keşi işlənir.
public struct DiskStore: Sendable {
    public static let appGroup = "group.az.ulduz8.app"
    public let directory: URL

    public init(directory: URL) {
        self.directory = directory
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        var dir = directory
        try? dir.setResourceValues(values)
    }

    public static let shared: DiskStore = {
        let fm = FileManager.default
        let base = fm.containerURL(forSecurityApplicationGroupIdentifier: appGroup)
            ?? fm.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return DiskStore(directory: base.appendingPathComponent("8ulduz", isDirectory: true))
    }()

    public func read(_ name: String) -> Data? { try? Data(contentsOf: directory.appendingPathComponent(name)) }
    public func write(_ data: Data, to name: String) { try? data.write(to: directory.appendingPathComponent(name), options: .atomic) }
    public func remove(_ name: String) { try? FileManager.default.removeItem(at: directory.appendingPathComponent(name)) }
}

/// sw.js-in məlumat zənciri (docs/qirmizi-xetler.md): canlı kanal, sayt, ehtiyat kanal, keş.
/// Vaxt rəqəmləri sw.js ilə eynidir, səbəbləri orada yazılıb. Onları ayrıca dəyişməyin.
public actor FeedClient {
    public enum Origin: String, Sendable { case live, site, mirror, cache }

    public struct Loaded<Value: Sendable>: Sendable {
        public let value: Value
        public let origin: Origin
    }

    public struct Failure: Error, Sendable {}
    struct HTTPStatus: Error { let code: Int }

    public typealias Transport = @Sendable (URLRequest) async throws -> (Data, URLResponse)

    public static let siteRoot = "https://8ulduz.az/"
    static let liveRoot = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/"
    static let mirrorRoot = "https://raw.githubusercontent.com/8ulduz/8ulduz/main/"
    static let liveFiles: Set<String> = ["status.json", "latest.json", "markets.json"]
    static let staleCheckedFiles: Set<String> = ["status.json", "latest.json", "news.json"]
    static let liveWait: TimeInterval = 2.5
    static let liveGrace: TimeInterval = 45
    static let livePause: TimeInterval = 5 * 60
    static let siteWait: TimeInterval = 4
    static let mirrorWait: TimeInterval = 6
    static let staleAfter: TimeInterval = 15 * 60

    private let transport: Transport
    private let store: DiskStore
    private let now: @Sendable () -> Date
    private var liveSkipUntil = Date.distantPast

    public static func defaultTransport() -> Transport {
        let config = URLSessionConfiguration.ephemeral
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        config.urlCache = nil
        config.httpCookieStorage = nil
        config.httpShouldSetCookies = false
        config.timeoutIntervalForResource = 45
        config.waitsForConnectivity = false
        let session = URLSession(configuration: config)
        return { try await session.data(for: $0) }
    }

    public init(store: DiskStore = .shared, transport: Transport? = nil, now: @escaping @Sendable () -> Date = { Date() }) {
        self.store = store
        self.transport = transport ?? FeedClient.defaultTransport()
        self.now = now
    }

    private func attempt(_ urlString: String, wait: TimeInterval) async throws -> (Data, HTTPURLResponse) {
        guard let url = URL(string: urlString) else { throw Failure() }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: wait)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let (data, response) = try await transport(request)
        guard let http = response as? HTTPURLResponse else { throw Failure() }
        guard (200...299).contains(http.statusCode) else { throw HTTPStatus(code: http.statusCode) }
        return (data, http)
    }

    /// Dəqiqənin faylı yalnız yazılandan sonra istənir: yaranmamış yola sorğu 404-ü 55 saniyə keşə salır.
    func liveMinutes() -> [Int] {
        let slot = Int(floor((now().timeIntervalSince1970 - Self.liveGrace) / 60))
        return [slot, slot - 1, slot - 2]
    }

    private func live(_ file: String) async -> Data? {
        guard Self.liveFiles.contains(file), now() >= liveSkipUntil else { return nil }
        for minute in liveMinutes() {
            do {
                return try await attempt("\(Self.liveRoot)\(minute)/\(file)", wait: Self.liveWait).0
            } catch let error as HTTPStatus where error.code == 404 {
                continue
            } catch let error as HTTPStatus where error.code == 403 || error.code == 429 {
                liveSkipUntil = now().addingTimeInterval(Self.livePause)
                return nil
            } catch {
                return nil // şəbəkə xətası: digər dəqiqələri gözləmədən sayta keç
            }
        }
        liveSkipUntil = now().addingTimeInterval(60) // axın yazmır: dəqiqəlik bir daha yoxla, indi sayt kanalı
        return nil
    }

    private func query(force: Bool) -> String {
        let minute = Int(now().timeIntervalSince1970 / 60)
        return force ? "?t=\(minute)&r=\(UUID().uuidString.prefix(8))" : "?t=\(minute)"
    }

    private func siteIsStuck(_ response: HTTPURLResponse, file: String) -> Bool {
        guard Self.staleCheckedFiles.contains(file),
              let header = response.value(forHTTPHeaderField: "Last-Modified"),
              let modified = Self.httpDate.date(from: header) else { return false }
        return now().timeIntervalSince(modified) > Self.staleAfter
    }

    private static let httpDate: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "GMT")
        f.dateFormat = "EEE, dd MMM yyyy HH:mm:ss zzz"
        return f
    }()

    /// Faylı zəncirlə gətirir. Oxunmayan cavab növbəti kanala keçir, uğurlu cavab keşə yazılır.
    public func load<Value: Decodable & Sendable>(_ file: String, as type: Value.Type = Value.self, force: Bool = false) async throws -> Loaded<Value> {
        func parsed(_ data: Data?) -> Value? {
            guard let data else { return nil }
            return try? JSONDecoder().decode(Value.self, from: data)
        }
        let cacheName = "data-\(file)"

        if let data = await live(file), let value = parsed(data) {
            store.write(data, to: cacheName)
            return Loaded(value: value, origin: .live)
        }
        let suffix = query(force: force)
        var stuckData: Data?
        var stuckValue: Value?
        if let answer = try? await attempt("\(Self.siteRoot)data/\(file)\(suffix)", wait: Self.siteWait), let value = parsed(answer.0) {
            if !siteIsStuck(answer.1, file: file) {
                store.write(answer.0, to: cacheName)
                return Loaded(value: value, origin: .site)
            }
            stuckData = answer.0
            stuckValue = value
        }
        if let answer = try? await attempt("\(Self.mirrorRoot)data/\(file)\(suffix)", wait: Self.mirrorWait), let value = parsed(answer.0) {
            store.write(answer.0, to: cacheName)
            return Loaded(value: value, origin: .mirror)
        }
        if let stuckData, let stuckValue {
            store.write(stuckData, to: cacheName)
            return Loaded(value: stuckValue, origin: .site)
        }
        if let value = parsed(store.read(cacheName)) {
            return Loaded(value: value, origin: .cache)
        }
        throw Failure()
    }

    /// Şəbəkəyə çıxmadan keşdən (açılışda ekran dərhal dolsun).
    public func cached<Value: Decodable & Sendable>(_ file: String, as type: Value.Type = Value.self) -> Value? {
        guard let data = store.read("data-\(file)") else { return nil }
        return try? JSONDecoder().decode(Value.self, from: data)
    }

    // MARK: - Qayda faylı

    private static let policyFile = "content-policy.js"

    public func cachedPolicy() -> ContentPolicy? {
        guard let data = store.read(Self.policyFile), let text = String(data: data, encoding: .utf8) else { return nil }
        return try? ContentPolicy(javascript: text)
    }

    /// assets/content-policy.js saytdan oxunur: qayda dəyişəndə tətbiq yenilənmədən qüvvəyə minir.
    /// Bu fayl yalnız məlumatdır, kod kimi işlədilmir.
    public func refreshPolicy() async -> ContentPolicy? {
        let hour = Int(now().timeIntervalSince1970 / 3600)
        for root in [Self.siteRoot, Self.mirrorRoot] {
            guard let answer = try? await attempt("\(root)assets/\(Self.policyFile)?t=\(hour)", wait: Self.mirrorWait + 4),
                  let text = String(data: answer.0, encoding: .utf8),
                  let policy = try? ContentPolicy(javascript: text) else { continue }
            store.write(answer.0, to: Self.policyFile)
            return policy
        }
        return nil
    }
}
