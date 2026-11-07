import Foundation

public struct WeatherNow: Identifiable, Hashable, Sendable {
    public let city: String
    public let temp: Int
    public let feels: Int
    public let humidity: Int
    public let wind: Int
    public let pressure: Int
    public let precipitation: Double
    public let label: String
    public let symbol: String
    public var id: String { city }

    /// app.js `wxCode`.
    public static func describe(code c: Int) -> (label: String, symbol: String) {
        switch c {
        case 0: return ("Açıq", "sun.max.fill")
        case 1: return ("Əsasən açıq", "sun.min.fill")
        case 2: return ("Qismən buludlu", "cloud.sun.fill")
        case 3: return ("Buludlu", "cloud.fill")
        case 45, 48: return ("Duman", "cloud.fog.fill")
        case 51...57: return ("Çiskin", "cloud.drizzle.fill")
        case 61...67, 80...82: return ("Yağışlı", "cloud.rain.fill")
        case 71...77, 85, 86: return ("Qarlı", "cloud.snow.fill")
        case 95...: return ("İldırımlı", "cloud.bolt.rain.fill")
        default: return ("Dəyişkən", "thermometer.medium")
        }
    }
}

public struct PrayerTime: Identifiable, Hashable, Sendable {
    public let key: String
    public let label: String
    public let time: String
    public let symbol: String
    public var id: String { key }
}

public struct PrayerDay: Sendable, Hashable {
    public let city: String
    public let times: [PrayerTime]
    public let hijri: String

    /// Bakı vaxtı ilə növbəti namaz (Günəş daxil, saytdakı kimi).
    public func next(after date: Date = Date()) -> PrayerTime? {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Baku") ?? .current
        let p = cal.dateComponents([.hour, .minute], from: date)
        let current = (p.hour ?? 0) * 60 + (p.minute ?? 0)
        return times.first { t in
            let parts = t.time.split(separator: ":").compactMap { Int($0) }
            return parts.count == 2 && parts[0] * 60 + parts[1] > current
        }
    }
}

/// Hava və namaz vaxtları: saytdakı kimi birbaşa cihazdan həmin xidmətlərə gedir. Yalnız şəhərin koordinatları göndərilir.
public enum Services {
    private struct OpenMeteo: Decodable {
        struct Current: Decodable {
            let temperature_2m: Double
            let apparent_temperature: Double
            let relative_humidity_2m: Double
            let precipitation: Double?
            let weathercode: Int
            let surface_pressure: Double
            let wind_speed_10m: Double
        }
        let current: Current
    }

    private static let session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.httpCookieStorage = nil
        config.httpShouldSetCookies = false
        config.timeoutIntervalForRequest = 15
        return URLSession(configuration: config)
    }()

    public static func weather(cities: [City]) async throws -> [WeatherNow] {
        guard !cities.isEmpty else { return [] }
        let lat = cities.map { String($0.lat) }.joined(separator: ",")
        let lon = cities.map { String($0.lon) }.joined(separator: ",")
        let url = URL(string: "https://api.open-meteo.com/v1/forecast?latitude=\(lat)&longitude=\(lon)&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weathercode,surface_pressure,wind_speed_10m&timezone=Asia%2FBaku")!
        let (data, _) = try await session.data(from: url)
        let list: [OpenMeteo]
        if let many = try? JSONDecoder().decode([OpenMeteo].self, from: data) { list = many }
        else { list = [try JSONDecoder().decode(OpenMeteo.self, from: data)] }
        return zip(cities, list).map { city, item in
            let c = item.current
            let d = WeatherNow.describe(code: c.weathercode)
            return WeatherNow(city: city.name, temp: Int(c.temperature_2m.rounded()), feels: Int(c.apparent_temperature.rounded()),
                              humidity: Int(c.relative_humidity_2m.rounded()), wind: Int(c.wind_speed_10m.rounded()),
                              pressure: Int(c.surface_pressure.rounded()), precipitation: ((c.precipitation ?? 0) * 10).rounded() / 10,
                              label: d.label, symbol: d.symbol)
        }
    }

    private struct Aladhan: Decodable {
        struct Payload: Decodable {
            struct DateInfo: Decodable {
                struct Hijri: Decodable {
                    struct Month: Decodable { let number: Int }
                    let day: String
                    let year: String
                    let month: Month
                }
                let hijri: Hijri?
            }
            let timings: [String: String]
            let date: DateInfo?
        }
        let data: Payload
    }

    private static let prayerOrder: [(key: String, label: String, symbol: String)] = [
        ("Fajr", "Sübh", "sunrise"), ("Sunrise", "Günəş", "sun.horizon"), ("Dhuhr", "Zöhr", "sun.max"),
        ("Asr", "Əsr", "sun.min"), ("Maghrib", "Məğrib", "sunset"), ("Isha", "İşa", "moon.stars"),
    ]
    private static let hijriMonths = ["", "Məhərrəm", "Səfər", "Rəbiüləvvəl", "Rəbiülaxır", "Cümadəl-ula", "Cümadəl-axır", "Rəcəb", "Şaban", "Ramazan", "Şəvval", "Zilqədə", "Zilhiccə"]

    public static func prayer(city: City) async throws -> PrayerDay {
        let url = URL(string: "https://api.aladhan.com/v1/timings?latitude=\(city.lat)&longitude=\(city.lon)&method=13")!
        let (data, _) = try await session.data(from: url)
        let payload = try JSONDecoder().decode(Aladhan.self, from: data).data
        let times = prayerOrder.compactMap { item -> PrayerTime? in
            guard let raw = payload.timings[item.key] else { return nil }
            return PrayerTime(key: item.key, label: item.label, time: String(raw.prefix(5)), symbol: item.symbol)
        }
        var hijri = ""
        if let h = payload.date?.hijri, hijriMonths.indices.contains(h.month.number) {
            hijri = "\(h.day) \(hijriMonths[h.month.number]) \(h.year)"
        }
        return PrayerDay(city: city.name, times: times, hijri: hijri)
    }
}
