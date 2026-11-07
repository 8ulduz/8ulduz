import Foundation

public enum ISODate {
    private static let plain: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()
    private static let fractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
    private static let dateOnly: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withFullDate]
        return f
    }()
    private static let noSeconds = try! NSRegularExpression(pattern: "^(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2})([+-]\\d{2}:\\d{2}|Z)$")

    /// Lentdə üç forma görünür: saniyəli, kəsrli və saniyəsiz (`2026-10-31T17:30+04:00`).
    public static func parse(_ s: String?) -> Date? {
        guard let s, !s.isEmpty else { return nil }
        if let d = plain.date(from: s) { return d }
        if let d = fractional.date(from: s) { return d }
        let range = NSRange(s.startIndex..., in: s)
        if noSeconds.firstMatch(in: s, range: range) != nil {
            let fixed = noSeconds.stringByReplacingMatches(in: s, range: range, withTemplate: "$1:00$2")
            if let d = plain.date(from: fixed) { return d }
        }
        return dateOnly.date(from: s)
    }
}

public enum Format {
    public static let months = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
    public static let days = ["bazar", "bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə"]

    /// İnterfeys dili: «az» və ya saytın lüğəti olan dil. Tətbiq dil seçiləndə təyin edir.
    public static var language = "az"

    private struct Words: Decodable {
        let min, hour, day, round, place, until, now: String
        let mon, monN, mon3, days: [String]
    }

    private static let table: [String: Words] = (try? JSONDecoder().decode([String: Words].self, from: Data(UiDatesData.json.utf8))) ?? [:]
    private static var words: Words? { language == "az" ? nil : table[language] }
    private static func fill(_ template: String, _ value: String) -> String { template.replacingOccurrences(of: "$1", with: value) }

    private static var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = .current
        return c
    }

    /// «5 dəqiqə əvvəl» (app.js `ago`).
    public static func ago(_ date: Date?, now: Date = Date()) -> String {
        guard let date else { return "" }
        let minutes = Int(max(0, now.timeIntervalSince(date)) / 60)
        if minutes < 1 { return words?.now ?? "indicə" }
        if minutes < 60 { return words.map { fill($0.min, String(minutes)) } ?? "\(minutes) dəqiqə əvvəl" }
        let hours = minutes / 60
        if hours < 24 { return words.map { fill($0.hour, String(hours)) } ?? "\(hours) saat əvvəl" }
        let days = hours / 24
        if days >= 30 { return fullDate(date) }
        return words.map { fill($0.day, String(days)) } ?? "\(days) gün əvvəl"
    }

    public static func fullDate(_ date: Date) -> String {
        let p = calendar.dateComponents([.day, .month, .year], from: date)
        return "\(p.day ?? 1) \((words?.mon ?? months)[(p.month ?? 1) - 1]) \(p.year ?? 2026)"
    }

    /// «Şənbə, 31 oktyabr 2026».
    public static func today(_ date: Date = Date()) -> String {
        let weekday = calendar.component(.weekday, from: date) - 1
        // Lüğətdə həftə bazar ertəsindən başlayır.
        let name = words.map { $0.days[(weekday + 6) % 7] } ?? days[weekday]
        let s = "\(name), \(fullDate(date))"
        return s.prefix(1).uppercased(with: Locale(identifier: "az")) + s.dropFirst()
    }

    /// «31 okt, 17:30» (app.js `shortDT`). Saatı olmayan oyunda yalnız tarix.
    public static func shortDateTime(_ iso: String?) -> String {
        guard let iso, let date = ISODate.parse(iso) else { return "" }
        let p = calendar.dateComponents([.day, .month, .hour, .minute], from: date)
        let month = words?.mon3[(p.month ?? 1) - 1] ?? String(months[(p.month ?? 1) - 1].prefix(3))
        let hasTime = iso.range(of: "T\\d\\d:\\d\\d", options: .regularExpression) != nil && !iso.contains("T00:00")
        let time = hasTime ? String(format: ", %02d:%02d", p.hour ?? 0, p.minute ?? 0) : ""
        return "\(p.day ?? 1) \(month)\(time)"
    }

    /// «Oktyabr 2026»: oyun siyahısının ay başlığı.
    public static func monthTitle(_ iso: String?) -> String {
        guard let date = ISODate.parse(iso) else { return "Vaxtı elan olunmayıb" }
        let p = calendar.dateComponents([.month, .year], from: date)
        let month = (words?.monN ?? months)[(p.month ?? 1) - 1]
        return month.prefix(1).uppercased(with: Locale(identifier: "az")) + month.dropFirst() + " \(p.year ?? 2026)"
    }

    /// «31 oktyabr oyunlarına qədər» (app.js `asofLabel`).
    public static func gamesUntil(_ day: String) -> String {
        let parts = day.split(separator: "-").compactMap { Int($0) }
        guard parts.count >= 3, (1...12).contains(parts[1]) else { return "" }
        if let words { return fill(words.until, "\(parts[2]) \(words.mon[parts[1] - 1])") }
        return "\(parts[2]) \(months[parts[1] - 1]) oyunlarına qədər"
    }

    /// «9-cu tur».
    public static func round(_ value: String) -> String {
        words.map { fill($0.round, value) } ?? "\(ordinal(value)) tur"
    }

    /// «3-cü yer».
    public static func place(_ value: Int) -> String {
        words.map { fill($0.place, String(value)) } ?? "\(ordinal(String(value))) yer"
    }

    /// Sıra sayı şəkilçisi: 9-cu, 10-cu, 1-ci, 3-cü, 6-cı (app.js `ordTur`).
    public static func ordinal(_ value: String?) -> String {
        guard let value, let n = Int(value) else { return value ?? "" }
        let tens = [10: "cu", 20: "ci", 30: "cu", 40: "cı", 50: "ci", 60: "cı", 70: "ci", 80: "ci", 90: "cı"]
        let ones = [1: "ci", 2: "ci", 3: "cü", 4: "cü", 5: "ci", 6: "cı", 7: "ci", 8: "ci", 9: "cu"]
        let suffix = n % 10 == 0 ? (tens[n % 100] ?? "cu") : (ones[n % 10] ?? "")
        return "\(n)-\(suffix)"
    }

    /// Bazar rəqəmi: ən azı `min(dec, 2)`, ən çoxu `dec` onluq (app.js `fmt`).
    public static func number(_ value: Double, decimals: Int) -> String {
        let f = NumberFormatter()
        f.locale = Locale(identifier: "en_US")
        f.numberStyle = .decimal
        f.roundingMode = .halfUp // toLocaleString kimi: NumberFormatter-in standartı .halfEven-dir
        f.minimumFractionDigits = min(decimals, 2)
        f.maximumFractionDigits = decimals
        return f.string(from: NSNumber(value: value)) ?? String(value)
    }
}
