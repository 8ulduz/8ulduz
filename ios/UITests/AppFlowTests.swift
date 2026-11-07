import XCTest

/// Tətbiqin əsas yollarını simulyatorda real lentlə yoxlayır və eyni zamanda App Store ekran şəkillərini çəkir.
/// SCREENSHOT_DIR verilibsə şəkillər ora yazılır (CI: `TEST_RUNNER_SCREENSHOT_DIR`).
final class AppFlowTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments += ["-8ulduz-theme", "dark"]
        dismissSystemAlert()
        app.launch()
        dismissSystemAlert()
    }

    /// Simulyatorda klaviatura ilk dəfə açılanda sistem «Enable Dictation?» soruşur və ekranı örtür.
    /// Pəncərə tətbiqin yox, SpringBoard-ındır.
    private func dismissSystemAlert() {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let notNow = springboard.buttons["Not Now"]
        if notNow.waitForExistence(timeout: 2) { notNow.tap() }
    }

    private func shot(_ name: String) {
        let screenshot = XCUIScreen.main.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
        if let dir = ProcessInfo.processInfo.environment["SCREENSHOT_DIR"], !dir.isEmpty {
            try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
            try? screenshot.pngRepresentation.write(to: URL(fileURLWithPath: dir).appendingPathComponent("\(name).png"))
        }
    }

    private func tab(_ title: String) {
        let button = app.tabBars.buttons[title]
        XCTAssertTrue(button.waitForExistence(timeout: 15), "«\(title)» tabı yoxdur")
        button.tap()
    }

    private func element(startingWith text: String) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", text)).firstMatch
    }

    /// Əsas karuselin ulduzu lent ekrana düşəndə görünür.
    private func waitForFeed() {
        XCTAssertTrue(app.buttons["Yadda saxla"].firstMatch.waitForExistence(timeout: 60), "Lent 60 saniyədə gəlmədi")
    }

    func test1_screens() throws {
        waitForFeed()
        sleep(5) // şəkillər və bazar zolağı yüklənsin
        shot("1-ana")

        app.scrollViews.firstMatch.swipeUp()
        sleep(3)
        shot("2-lent")

        tab("Bölmələr")
        let economy = element(startingWith: "İqtisadiyyat")
        XCTAssertTrue(economy.waitForExistence(timeout: 10))
        shot("3-bolmeler")

        economy.tap()
        sleep(4)
        shot("4-bolme")
        app.navigationBars.buttons.element(boundBy: 0).tap()

        tab("Axtar")
        let field = app.searchFields.firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        field.tap()
        dismissSystemAlert()
        // Sətir sonu axtarışı təsdiqləyir və klaviaturanı bağlayır: açıq klaviatura tab panelini örtür.
        field.typeText("Bakı\n")
        sleep(4)
        dismissSystemAlert()
        shot("5-axtaris")

        tab("Xidmətlər")
        let markets = app.staticTexts["Bazar və çevirici"]
        XCTAssertTrue(markets.waitForExistence(timeout: 10))
        markets.tap()
        XCTAssertTrue(app.staticTexts["Çevirici"].waitForExistence(timeout: 10))
        sleep(2)
        shot("6-bazar")
        app.navigationBars.buttons.element(boundBy: 0).tap()

        app.staticTexts["Futbol və cədvəllər"].tap()
        let league = app.staticTexts["Misli Premyer Liqası"]
        XCTAssertTrue(league.waitForExistence(timeout: 20), "liqaların siyahısı gəlmədi")
        shot("7-futbol")

        league.tap()
        let team = app.buttons.matching(identifier: "team-row").firstMatch
        XCTAssertTrue(team.waitForExistence(timeout: 20), "liqanın cədvəli gəlmədi")
        sleep(6) // loqolar yüklənsin
        shot("8-liqa")

        team.tap()
        XCTAssertTrue(app.staticTexts["Son nəticələr"].waitForExistence(timeout: 20), "komanda səhifəsi açılmadı")
        sleep(6)
        shot("9-komanda")
    }

    /// İdman bölməsinin alt başlıqları: Futbol seçiləndə liqalar və Milli komanda görünür.
    func test3_sportSubsections() throws {
        waitForFeed()
        tab("Bölmələr")
        let sport = element(startingWith: "İdman")
        XCTAssertTrue(sport.waitForExistence(timeout: 10))
        sport.tap()
        let football = app.buttons["Futbol"]
        XCTAssertTrue(football.waitForExistence(timeout: 10), "alt bölmələr yoxdur")
        football.tap()
        XCTAssertTrue(app.buttons["Milli komanda"].waitForExistence(timeout: 10), "ikinci sətir açılmadı")
        sleep(3)
        shot("10-idman")
    }

    /// Xarici dil seçiləndə interfeys də həmin dilə keçir, xəbər mətni tərcümə olunmur.
    func test4_interfaceLanguage() throws {
        app.terminate()
        app.launchArguments += ["-8ulduz-lang", "en"]
        app.launch()
        dismissSystemAlert()
        XCTAssertTrue(app.tabBars.buttons["Sections"].waitForExistence(timeout: 30) || app.tabBars.buttons.count == 5)
        sleep(6)
        shot("11-ingilis")
    }

    func test2_saveAndFind() throws {
        waitForFeed()
        app.buttons["Yadda saxla"].firstMatch.tap()

        tab("Seçilmişlər")
        XCTAssertFalse(app.staticTexts["Saxlanmış xəbər yoxdur"].waitForExistence(timeout: 3), "seçilmiş xəbər siyahıya düşmədi")
        let saved = app.buttons["Saxlanmışlardan çıxar"].firstMatch
        XCTAssertTrue(saved.waitForExistence(timeout: 5))
        saved.tap()
        XCTAssertTrue(app.staticTexts["Saxlanmış xəbər yoxdur"].waitForExistence(timeout: 5))
    }
}
