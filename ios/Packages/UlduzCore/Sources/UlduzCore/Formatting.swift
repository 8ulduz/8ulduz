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

    private static var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = .current
        return c
    }

    /// «5 dəqiqə əvvəl» (app.js `ago`).
    public static func ago(_ date: Date?, now: Date = Date()) -> String {
        guard let date else { return "" }
        let minutes = Int(max(0, now.timeIntervalSince(date)) / 60)
        if minutes < 1 { return "indicə" }
        if minutes < 60 { return "\(minutes) dəqiqə əvvəl" }
        let hours = minutes / 60
        if hours < 24 { return "\(hours) saat əvvəl" }
        let days = hours / 24
        return days < 30 ? "\(days) gün əvvəl" : fullDate(date)
    }

    public static func fullDate(_ date: Date) -> String {
        let p = calendar.dateComponents([.day, .month, .year], from: date)
        return "\(p.day ?? 1) \(months[(p.month ?? 1) - 1]) \(p.year ?? 2026)"
    }

    /// «Şənbə, 31 oktyabr 2026».
    public static func today(_ date: Date = Date()) -> String {
        let weekday = calendar.component(.weekday, from: date) - 1
        let s = "\(days[weekday]), \(fullDate(date))"
        return s.prefix(1).uppercased(with: Locale(identifier: "az")) + s.dropFirst()
    }

    /// «31 okt, 17:30» (app.js `shortDT`). Saatı olmayan oyunda yalnız tarix.
    public static func shortDateTime(_ iso: String?) -> String {
        guard let iso, let date = ISODate.parse(iso) else { return "" }
        let p = calendar.dateComponents([.day, .month, .hour, .minute], from: date)
        let month = months[(p.month ?? 1) - 1].prefix(3)
        let hasTime = iso.range(of: "T\\d\\d:\\d\\d", options: .regularExpression) != nil && !iso.contains("T00:00")
        let time = hasTime ? String(format: ", %02d:%02d", p.hour ?? 0, p.minute ?? 0) : ""
        return "\(p.day ?? 1) \(month)\(time)"
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
