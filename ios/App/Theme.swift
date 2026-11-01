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

    static let background = dynamic(dark: hsl(222, 0.47, 0.05), light: hsl(210, 0.40, 0.97))
    static let card = dynamic(dark: hsl(222, 0.40, 0.08), light: .white)
    static let card2 = dynamic(dark: hsl(222, 0.34, 0.11), light: hsl(210, 0.32, 0.93))
    static let gold = dynamic(dark: hsl(43, 0.96, 0.56), light: hsl(38, 0.88, 0.36))
    static let muted = dynamic(dark: hsl(215, 0.20, 0.62), light: hsl(215, 0.16, 0.32))
    static let border = dynamic(dark: hsl(222, 0.24, 0.16), light: hsl(214, 0.22, 0.82))
    static let red = Color(uiColor: hsl(0, 0.84, 0.60))
    static let green = Color(red: 0x10 / 255, green: 0xB9 / 255, blue: 0x81 / 255)

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

    func screenBackground() -> some View {
        self.scrollContentBackground(.hidden).background(Theme.background.ignoresSafeArea())
    }
}
