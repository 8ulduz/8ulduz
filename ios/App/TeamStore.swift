import Foundation
import Observation
import UlduzCore

/// Komanda səhifələrinin faylları (data/futbol/): yalnız həmin ekran açılanda yüklənir, 10 dəqiqə yaddaşda qalır (assets/komanda.js).
@MainActor
@Observable
final class TeamStore {
    private static let keepFor: TimeInterval = 10 * 60
    private static let retryAfter: TimeInterval = 30

    private(set) var index: TeamIndex?
    private(set) var leagues: [String: LeagueDoc] = [:]
    private(set) var squads: [String: SquadDoc] = [:]
    private(set) var failed: Set<String> = []

    @ObservationIgnored private let client = FeedClient()
    @ObservationIgnored private var nextLoad: [String: Date] = [:]

    private func claim(_ path: String) -> Bool {
        if let at = nextLoad[path], Date() < at { return false }
        nextLoad[path] = Date().addingTimeInterval(Self.keepFor)
        return true
    }

    private func fetch<Value: Decodable & Sendable>(_ path: String, as type: Value.Type, show: (Value) -> Void) async {
        guard claim(path) else { return }
        if let cached: Value = await client.cached(path) { show(cached) }
        // Keş ekranı dəyişəndə baxış tapşırığı yenilənir: yüklənmə onunla birlikdə kəsilməsin.
        let feed = self.client
        let loaded = await Task { try? await feed.load(path, as: Value.self) }.value
        if let loaded {
            show(loaded.value)
            failed.remove(path)
        } else {
            failed.insert(path)
            nextLoad[path] = Date().addingTimeInterval(Self.retryAfter)
        }
    }

    func loadIndex() async {
        await fetch("futbol/index.json", as: TeamIndex.self) { index = $0 }
    }

    func loadLeague(_ path: String) async {
        await fetch(path, as: LeagueDoc.self) { leagues[path] = $0 }
    }

    func loadSquad(_ leagueID: String) async {
        await fetch("futbol/heyet-\(leagueID).json", as: SquadDoc.self) { squads[leagueID] = $0 }
    }

    func hasFailed(_ path: String) -> Bool { failed.contains(path) }
}
