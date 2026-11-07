import Foundation

/// NSRegularExpression üçün qısa bükücü. Naxışlar kodda sabitdir, ona görə səhv naxış test zamanı üzə çıxır.
public final class Rx: @unchecked Sendable {
    private let re: NSRegularExpression?

    public init(_ pattern: String, caseInsensitive: Bool = false) {
        re = try? NSRegularExpression(pattern: pattern, options: caseInsensitive ? [.caseInsensitive] : [])
    }

    public var isValid: Bool { re != nil }

    public func test(_ text: String) -> Bool {
        guard let re else { return false }
        return re.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) != nil
    }

    public func replace(_ text: String, with template: String) -> String {
        guard let re else { return text }
        return re.stringByReplacingMatches(in: text, range: NSRange(text.startIndex..., in: text), withTemplate: template)
    }
}

/// assets/app.js-dəki mətn köməkçilərinin eyni qaydalı nüsxəsi.
public enum TextTools {
    private static let az = Locale(identifier: "az")
    private static let entity = try! NSRegularExpression(pattern: "&(#[0-9]+|#[xX][0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);")
    private static let named: [String: String] = [
        "amp": "&", "lt": "<", "gt": ">", "quot": "\"", "apos": "'", "nbsp": "\u{00A0}",
        "ndash": "–", "mdash": "—", "laquo": "«", "raquo": "»", "hellip": "…", "lsquo": "‘", "rsquo": "’",
        "ldquo": "“", "rdquo": "”", "bdquo": "„", "sbquo": "‚", "middot": "·", "bull": "•", "copy": "©",
        "reg": "®", "trade": "™", "euro": "€", "times": "×", "ouml": "ö", "Ouml": "Ö", "uuml": "ü", "Uuml": "Ü",
        "ccedil": "ç", "Ccedil": "Ç", "scedil": "ş", "Scedil": "Ş", "gbreve": "ğ", "Gbreve": "Ğ",
        "inodot": "ı", "Idot": "İ", "schwa": "ə", "SCHWA": "Ə",
    ]

    /// İç-içə kodlanmış HTML varlıqlarını açır (saytdakı kimi ən çox 3 dəfə).
    public static func decodeEntities(_ input: String) -> String {
        guard input.contains("&") else { return input }
        var current = input
        for _ in 0..<3 where current.contains("&") {
            let next = decodeOnce(current)
            if next == current { break }
            current = next
        }
        return current
    }

    private static func decodeOnce(_ s: String) -> String {
        let ns = s as NSString
        let matches = entity.matches(in: s, range: NSRange(location: 0, length: ns.length))
        guard !matches.isEmpty else { return s }
        var out = ""
        var cursor = 0
        for m in matches {
            out += ns.substring(with: NSRange(location: cursor, length: m.range.location - cursor))
            let body = ns.substring(with: m.range(at: 1))
            out += replacement(for: body) ?? ns.substring(with: m.range)
            cursor = m.range.location + m.range.length
        }
        out += ns.substring(from: cursor)
        return out
    }

    private static func replacement(for body: String) -> String? {
        if body.hasPrefix("#") {
            let digits = body.dropFirst()
            let code: UInt32?
            if digits.first == "x" || digits.first == "X" { code = UInt32(digits.dropFirst(), radix: 16) }
            else { code = UInt32(digits, radix: 10) }
            guard let code, let scalar = Unicode.Scalar(code) else { return nil }
            return String(Character(scalar))
        }
        return named[body]
    }

    private static let urlInText = Rx("\\s*https?://\\S+", caseInsensitive: true)
    private static let spaces = Rx("\\s+")
    private static let trailingSeparators = Rx("(?:\\s*[-–—|])+\\s*$")

    /// Başlıq və xülasə üçün təmizləmə (app.js `tidy`).
    public static func tidy(_ input: String?) -> String {
        guard let input, !input.isEmpty else { return "" }
        var s = decodeEntities(input)
        s = urlInText.replace(s, with: "")
        s = s.replacingOccurrences(of: "\u{00A0}", with: " ")
        s = spaces.replace(s, with: " ")
        s = trailingSeparators.replace(s, with: "")
        return s.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// `toLocaleLowerCase("az")`: İ → i, I → ı.
    public static func azLowercased(_ s: String) -> String { s.lowercased(with: az) }

    private static let nonWord = Rx("[^\\p{L}\\p{N}\\s]")

    /// Qruplaşdırma üçün başlıq forması (app.js `normTitle`).
    public static func normTitle(_ input: String?) -> String {
        guard var s = input?.lowercased(), !s.isEmpty else { return "" }
        s = s.replacingOccurrences(of: "i\u{0307}", with: "i")
        var mapped = String.UnicodeScalarView()
        for scalar in s.unicodeScalars {
            switch scalar {
            case "ə": mapped.append("e")
            case "â": mapped.append("a")
            case "ı", "î": mapped.append("i")
            case "ö": mapped.append("o")
            case "ü", "û": mapped.append("u")
            case "ş": mapped.append("s")
            case "ç": mapped.append("c")
            case "ğ": mapped.append("g")
            default: mapped.append(scalar)
            }
        }
        var out = nonWord.replace(String(mapped), with: " ")
        out = spaces.replace(out, with: " ")
        return out.trimmingCharacters(in: .whitespaces)
    }

    /// Axtarış üçün sadələşdirmə (app.js `fold`): «ilham eliyev», «qarabag», «AZERTAC» kimi yazılışlar da tapılır.
    public static func fold(_ input: String?) -> String {
        guard let input, !input.isEmpty else { return "" }
        let decomposed = input.lowercased().decomposedStringWithCanonicalMapping
        var out = String.UnicodeScalarView()
        for scalar in decomposed.unicodeScalars {
            if (0x0300...0x036F).contains(scalar.value) { continue }
            switch scalar {
            case "ə": out.append("e")
            case "ı": out.append("i")
            case "ö": out.append("o")
            case "ü": out.append("u")
            case "ğ": out.append("g")
            case "ş": out.append("s")
            case "ç": out.append("c")
            default: out.append(scalar)
            }
        }
        return String(out)
    }

    /// `new URL(url).hostname` (kiçik hərflə, `www.`-siz). Oxunmayan ünvan üçün boş sətir.
    public static func host(of urlString: String?) -> String {
        guard let urlString, !urlString.isEmpty else { return "" }
        var host = URL(string: urlString)?.host
        if host == nil || host?.isEmpty == true {
            guard let range = urlString.range(of: "://") else { return "" }
            var rest = String(urlString[range.upperBound...])
            if let cut = rest.firstIndex(where: { "/?#".contains($0) }) { rest = String(rest[..<cut]) }
            if let at = rest.lastIndex(of: "@") { rest = String(rest[rest.index(after: at)...]) }
            if let colon = rest.firstIndex(of: ":") { rest = String(rest[..<colon]) }
            host = rest
        }
        var h = (host ?? "").lowercased()
        if h.hasPrefix("www.") { h.removeFirst(4) }
        return h
    }

    /// Yalnız http(s) keçidlər açılır: lent etibarsız mənbədir (`javascript:` işləməsin).
    public static func webURL(_ s: String?) -> URL? {
        guard let s = s?.trimmingCharacters(in: .whitespacesAndNewlines) else { return nil }
        let lower = s.lowercased()
        guard lower.hasPrefix("http://") || lower.hasPrefix("https://") else { return nil }
        return URL(string: s)
    }
}
