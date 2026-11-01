import Foundation

public struct NewsCategory: Identifiable, Hashable, Sendable {
    public let slug: String
    public let label: String
    public let description: String
    public let symbol: String
    public var id: String { slug }
}

public struct NewsLanguage: Identifiable, Hashable, Sendable {
    public let code: String
    public let label: String
    public let badge: String
    public var id: String { code }
}

public struct City: Identifiable, Hashable, Sendable {
    public let name: String
    public let lat: Double
    public let lon: Double
    public var id: String { name }
}

public struct TrafficArea: Identifiable, Hashable, Sendable {
    public let id: String
    public let label: String
    public let lat: Double
    public let lon: Double
    public let zoom: Int
    public var embedURL: URL { URL(string: "https://embed.waze.com/iframe?zoom=\(zoom)&lat=\(lat)&lon=\(lon)")! }
    public var liveURL: URL { URL(string: "https://www.waze.com/live-map?ll=\(lat),\(lon)&zoom=\(zoom)")! }
}

public struct OfficialProfile: Identifiable, Hashable, Sendable {
    public let who: String
    public let links: [Link]
    public var id: String { who }
    public struct Link: Identifiable, Hashable, Sendable {
        public let name: String
        public let url: URL
        public var id: String { url.absoluteString }
    }
}

/// Saytın sabit siyahıları (assets/app.js-in başındakı CATS, LANGS, CITIES, TRAFFIC_AREAS, PROFILES).
public enum Catalog {
    public static let categories: [NewsCategory] = [
        NewsCategory(slug: "prezident", label: "Zuğulba Xronikası", description: "Prezident İlham Əliyev və Birinci xanım Mehriban Əliyevanın gündəliyi", symbol: "star.fill"),
        NewsCategory(slug: "sondeqiqe", label: "Son dəqiqə", description: "Son bir saatın xəbərləri", symbol: "bolt.fill"),
        NewsCategory(slug: "gundem", label: "Gündəm", description: "Günün əsas hadisələri", symbol: "newspaper.fill"),
        NewsCategory(slug: "siyaset", label: "Siyasət", description: "Daxili və xarici siyasət", symbol: "building.columns.fill"),
        NewsCategory(slug: "cemiyyet", label: "Cəmiyyət", description: "Sosial həyatdan xəbərlər", symbol: "person.3.fill"),
        NewsCategory(slug: "iqtisadiyyat", label: "İqtisadiyyat", description: "Bazar, maliyyə, enerji", symbol: "chart.line.uptrend.xyaxis"),
        NewsCategory(slug: "dunya", label: "Dünya", description: "Beynəlxalq mətbuat", symbol: "globe.europe.africa.fill"),
        NewsCategory(slug: "idman", label: "İdman", description: "İdman aləmindən xəbərlər və nəticələr", symbol: "sportscourt.fill"),
        NewsCategory(slug: "medeniyyet", label: "Mədəniyyət", description: "Kino, musiqi, sənət və mədəni həyat", symbol: "theatermasks.fill"),
        NewsCategory(slug: "heyat", label: "Sağlamlıq və həyat", description: "Tibb, sağlamlıq, qidalanma, psixologiya", symbol: "cross.case.fill"),
        NewsCategory(slug: "sosial", label: "Sosial müdafiə", description: "Pensiya, müavinət, sosial yardım, əlillik, məşğulluq", symbol: "person.2.fill"),
        NewsCategory(slug: "bolgeler", label: "Bölgələr", description: "Rayonlardan və şəhərlərdən xəbərlər", symbol: "map.fill"),
        NewsCategory(slug: "tehsil", label: "Təhsil və elm", description: "Məktəb, universitet, elm, texnologiya", symbol: "graduationcap.fill"),
        NewsCategory(slug: "video", label: "Video", description: "Saytlardakı video xəbərlərə keçidlər", symbol: "play.rectangle.fill"),
    ]

    /// Birləşmiş bölmələr: köhnə keçid, saxlanmış xəbər və köhnə keş də yeni bölməyə düşür (updater.py, SECTION_ALIASES).
    public static let sectionAlias = ["sehiyye": "heyat", "texnologiya": "tehsil"]
    public static func canonical(_ slug: String) -> String { sectionAlias[slug] ?? slug }

    public static func category(_ slug: String) -> NewsCategory? {
        let wanted = canonical(slug)
        return categories.first { $0.slug == wanted }
    }
    public static func label(_ slug: String) -> String { category(slug)?.label ?? slug }

    /// Ana səhifədə ayrıca bloku olan bölmələr; sıralanan siyahıya düşmür.
    public static let homeFixed: Set<String> = ["video", "prezident", "sondeqiqe"]
    public static var orderableSlugs: [String] { categories.map(\.slug).filter { !homeFixed.contains($0) } }

    public static let languages: [NewsLanguage] = [
        NewsLanguage(code: "az", label: "Azərbaycan dilində", badge: "AZ"),
        NewsLanguage(code: "tr", label: "Türkçe", badge: "TÜRK"),
        NewsLanguage(code: "ru", label: "на русском языке", badge: "RUS"),
        NewsLanguage(code: "en", label: "in English", badge: "ENG"),
    ]

    private static func city(_ name: String, _ lat: Double, _ lon: Double) -> City { City(name: name, lat: lat, lon: lon) }

    public static let cities: [City] = [
        city("Bakı", 40.4093, 49.8671), city("Sumqayıt", 40.5897, 49.6686), city("Gəncə", 40.6828, 46.3606), city("Mingəçevir", 40.77, 47.0286),
        city("Şirvan", 39.937, 48.929), city("Naxçıvan", 39.2089, 45.4122), city("Lənkəran", 38.7529, 48.85), city("Şəki", 41.1919, 47.1706),
        city("Quba", 41.3611, 48.5133), city("Xaçmaz", 41.459, 48.802), city("Şamaxı", 40.631, 48.641), city("İsmayıllı", 40.785, 48.15),
        city("Qəbələ", 40.98, 47.86), city("Oğuz", 41.071, 47.465), city("Zaqatala", 41.63, 46.64), city("Balakən", 41.726, 46.404),
        city("Qax", 41.418, 46.92), city("Şuşa", 39.758, 46.75), city("Ağdam", 39.993, 46.93), city("Füzuli", 39.604, 47.15),
        city("Cəbrayıl", 39.399, 47.03), city("Kəlbəcər", 40.106, 46.045), city("Laçın", 39.638, 46.546), city("Zəngilan", 39.088, 46.65),
        city("Qubadlı", 39.344, 46.58), city("Tovuz", 40.992, 45.628), city("Göygöl", 40.585, 46.306), city("Yevlax", 40.617, 47.15),
        city("Bərdə", 40.375, 47.126), city("Ağsu", 40.57, 48.4), city("Kürdəmir", 40.335, 48.16), city("Ucar", 40.52, 47.65),
        city("Göyçay", 40.65, 47.74), city("Ağdaş", 40.65, 47.48), city("Zərdab", 40.22, 47.71), city("İmişli", 39.87, 48.06),
        city("Saatlı", 39.93, 48.37), city("Sabirabad", 40.01, 48.48), city("Salyan", 39.596, 49.0), city("Neftçala", 39.376, 49.247),
        city("Hacıqabul", 40.04, 48.94), city("Biləsuvar", 39.46, 48.55), city("Masallı", 39.034, 48.665), city("Astara", 38.501, 48.875),
        city("Lerik", 38.775, 48.415), city("Yardımlı", 38.908, 48.24),
    ]

    public static let trafficAreas: [TrafficArea] = [
        TrafficArea(id: "merkez", label: "Bakı mərkəz", lat: 40.4093, lon: 49.8671, zoom: 12),
        TrafficArea(id: "sumqayit", label: "Sumqayıt yolu", lat: 40.482, lon: 49.835, zoom: 13),
        TrafficArea(id: "hava", label: "Hava limanı yolu", lat: 40.45, lon: 50.0, zoom: 13),
        TrafficArea(id: "abseron", label: "Abşeron", lat: 40.45, lon: 49.95, zoom: 11),
    ]

    public static let profiles: [OfficialProfile] = [
        OfficialProfile(who: "İlham Əliyev", links: [
            link("X", "https://x.com/presidentaz"), link("X (AZ)", "https://x.com/azpresident"),
            link("Instagram", "https://www.instagram.com/presidentaz/"),
            link("Facebook", "https://www.facebook.com/PresidentIlhamAliyev"),
            link("YouTube", "https://www.youtube.com/@presidentaz"),
        ]),
        OfficialProfile(who: "Mehriban Əliyeva", links: [
            link("X", "https://x.com/1VicePresident"),
            link("Instagram", "https://www.instagram.com/firstvicepresidentazerbaijan/"),
            link("Facebook", "https://www.facebook.com/FirstvicepresidentofAzerbaijanOfficial"),
            link("YouTube", "https://www.youtube.com/@FirstvicepresidentofAzerbaijan"),
        ]),
    ]

    private static func link(_ name: String, _ url: String) -> OfficialProfile.Link {
        OfficialProfile.Link(name: name, url: URL(string: url)!)
    }

    /// TheSportsDB ingilis adlarını azərbaycanca yazır (app.js `CLUB_AZ`).
    public static func clubAz(_ name: String) -> String {
        clubNames[name.trimmingCharacters(in: .whitespaces)] ?? name
    }
    private static let clubNames: [String: String] = [
        "Sabah Baku": "Sabah", "Sabah FK": "Sabah", "Qarabag": "Qarabağ", "Qarabag FK": "Qarabağ", "Neftci Baku": "Neftçi",
        "Neftchi Baku": "Neftçi", "Neftchi": "Neftçi", "Zira": "Zirə", "Zira FK": "Zirə", "Sumqayit": "Sumqayıt", "Sumgayit": "Sumqayıt",
        "Kapaz": "Kəpəz", "Shamakhi": "Şamaxı", "Araz-Naxcivan": "Araz-Naxçıvan", "Araz Nakhchivan": "Araz-Naxçıvan", "Imisli": "İmişli",
        "Gabala": "Qəbələ", "Sabail": "Səbail", "Karvan": "Karvan-Yevlax", "Turan Tovuz": "Turan Tovuz", "Sheki": "Şəki", "Mingachevir": "Mingəçevir",
    ]
}
