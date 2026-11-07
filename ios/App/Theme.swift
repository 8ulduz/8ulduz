import SwiftUI
import UIKit
import UlduzCore

/// Saytın rəngləri (assets/app.css :root).
enum Theme {
    static func hsl(_ h: Double, _ s: Double, _ l: Double) -> UIColor {
        let c = (1 - abs(2 * l - 1)) * s
        let hp = h / 60
        let x = c * (1 - abs(hp.truncatingRemainder(dividingBy: 2) - 1))
        let m = l - c / 2
        let rgb: (Double, Double, Double)
        switch hp {
        case 0..<1: rgb = (c, x, 0)
        case 1..<2: rgb = (x, c, 0)
        case 2..<3: rgb = (0, c, x)
        case 3..<4: rgb = (0, x, c)
        case 4..<5: rgb = (x, 0, c)
        default: rgb = (c, 0, x)
        }
        return UIColor(red: rgb.0 + m, green: rgb.1 + m, blue: rgb.2 + m, alpha: 1)
    }

    private static func dynamic(dark: UIColor, light: UIColor) -> Color {
        Color(uiColor: UIColor { $0.userInterfaceStyle == .dark ? dark : light })
    }

    static func hex(_ value: UInt32) -> UIColor {
        UIColor(red: CGFloat((value >> 16) & 0xFF) / 255, green: CGFloat((value >> 8) & 0xFF) / 255, blue: CGFloat(value & 0xFF) / 255, alpha: 1)
    }

    // Üç rəng: əsas göy, vurğu qızılı, təcili qırmızı. Tünddə vurğu qızılı, açıqda lacivərd (app.css `--primary`).
    static let background = dynamic(dark: hex(0x15233B), light: hex(0xF6F4EE))
    static let card = dynamic(dark: hex(0x1C2C46), light: .white)
    static let card2 = dynamic(dark: hex(0x263952), light: hex(0xE6EBF2))
    static let text = dynamic(dark: hex(0xD5DEEB), light: hex(0x172B4D))
    static let gold = dynamic(dark: hex(0xD6BD80), light: hex(0x19385F))
    static let muted = dynamic(dark: hex(0xAABBD2), light: hex(0x465773))
    static let border = dynamic(dark: hex(0x3E5370), light: hex(0xE2DDD0))
    static let red = Color(uiColor: hsl(0, 0.84, 0.60))
    static let green = Color(red: 0x10 / 255, green: 0xB9 / 255, blue: 0x81 / 255)
    static let up = dynamic(dark: hex(0x34D399), light: hex(0x047857))
    static let down = dynamic(dark: hex(0xF87171), light: hex(0xB91C1C))

    private static let categoryColors: [String: UIColor] = [
        "gundem": hsl(210, 0.70, 0.62), "siyaset": hsl(262, 0.48, 0.68), "cemiyyet": hsl(168, 0.42, 0.52),
        "iqtisadiyyat": hsl(43, 0.78, 0.56), "dunya": hsl(199, 0.62, 0.58), "idman": hsl(142, 0.46, 0.48),
        "medeniyyet": hsl(328, 0.46, 0.64), "heyat": hsl(16, 0.72, 0.60), "sosial": hsl(186, 0.50, 0.52), "video": hsl(0, 0.72, 0.62),
        "prezident": hsl(43, 0.96, 0.56), "sondeqiqe": hsl(0, 0.84, 0.60),
    ]

    static func color(forCategory slug: String) -> Color {
        Color(uiColor: categoryColors[slug] ?? hsl(215, 0.20, 0.62))
    }
}

extension View {
    /// Kart: saytın `.card` görünüşü.
    func cardStyle(padding: CGFloat = 0) -> some View {
        self.padding(padding)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Theme.border, lineWidth: 1))
    }

    /// Mətn rəngi yalnız ekranın məzmununa verilir, sistem axtarış sətrinə keçmir. Rəng tətbiqin kökündə olanda
    /// «Axtar» tabı açılarkən tətbiq donmuşdu (2026-11-07 UI testi); səbəb ehtimal ki `searchable` idi.
    func screenBackground() -> some View {
        self.foregroundStyle(Theme.text)
            .scrollContentBackground(.hidden)
            .background(Theme.background.ignoresSafeArea())
    }
}
