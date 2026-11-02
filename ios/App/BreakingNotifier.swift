import BackgroundTasks
import Foundation
import UlduzCore
import UserNotifications
import WidgetKit

/// «Son dəqiqə» bildirişləri. Saytdakı kimi serversizdir: abunəlik və cihaz identifikatoru yoxdur, bildiriş cihazın özündə yaranır.
/// Arxa planda nə vaxt işləyəcəyinə iOS qərar verir, ona görə bildiriş gecikə bilər.
enum BreakingNotifier {
    static let taskID = "az.ulduz8.app.refresh"
    private static let seenKey = "8ulduz-seen"
    private static let notifyKey = "8ulduz-notify"
    private static let languageKey = "8ulduz-lang"
    private static let refreshAfter: TimeInterval = 15 * 60
    private static let maxPerRun = 2

    static func requestPermission() async -> Bool {
        (try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])) ?? false
    }

    static func schedule() {
        let request = BGAppRefreshTaskRequest(identifier: taskID)
        request.earliestBeginDate = Date(timeIntervalSinceNow: refreshAfter)
        try? BGTaskScheduler.shared.submit(request)
    }

    /// Ön planda görülən xəbər üçün sonradan bildiriş gəlməsin.
    static func markSeen(_ articles: [Article]) {
        let ids = articles.filter { $0.isWithinHour() }.map(\.id)
        UserDefaults.standard.set(ids, forKey: seenKey)
    }

    private static func title(language: String) -> String {
        guard let path = Bundle.main.path(forResource: language.isEmpty ? "az" : language, ofType: "lproj"), let bundle = Bundle(path: path) else { return "Son dəqiqə" }
        return bundle.localizedString(forKey: "Son dəqiqə", value: "Son dəqiqə", table: nil)
    }

    static func runInBackground() async {
        schedule()
        WidgetCenter.shared.reloadAllTimelines()
        let defaults = UserDefaults.standard
        guard defaults.bool(forKey: notifyKey) else { return }

        let client = FeedClient()
        var policy = ContentPolicy.bundled()
        if let cached = await client.cachedPolicy() { policy = cached }
        guard let loaded = try? await client.load("latest.json", as: NewsFeed.self), loaded.origin != .cache else { return }

        let language = defaults.object(forKey: languageKey) == nil ? "az" : (defaults.string(forKey: languageKey) ?? "az")
        let dead = Set(loaded.value.dead)
        let recent = policy.clean(loaded.value.articles).filter { $0.isWithinHour() && !dead.contains($0.sourceUrl) }
        let fresh = Ranking.filtered(recent, language: language.isEmpty ? nil : language)
        // «Görülmüş» siyahı bütün dillərdir: dil dəyişəndə köhnə xəbər təzə kimi gəlmir.
        let ids = recent.map(\.id)
        guard let seen = defaults.stringArray(forKey: seenKey) else {
            defaults.set(ids, forKey: seenKey)
            return
        }
        let known = Set(seen)
        let center = UNUserNotificationCenter.current()
        for article in fresh.filter({ !known.contains($0.id) }).prefix(maxPerRun) {
            let content = UNMutableNotificationContent()
            content.title = title(language: language)
            content.body = article.cleanTitle
            content.sound = .default
            content.threadIdentifier = "son-deqiqe"
            content.userInfo = ["id": article.id, "url": article.sourceUrl]
            try? await center.add(UNNotificationRequest(identifier: "break-\(article.id)", content: content, trigger: nil))
        }
        defaults.set(ids, forKey: seenKey)
    }
}
