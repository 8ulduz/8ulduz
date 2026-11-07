import SwiftUI
import UIKit
import UlduzCore

enum AppLinks {
    static let privacy = URL(string: "https://8ulduz.az/mexfilik/")!
    static let site = URL(string: "https://8ulduz.az/")!
    static let issues = URL(string: "https://github.com/8ulduz/8ulduz/issues")!
    static let email = URL(string: "mailto:8ulduz.az@gmail.com")!
}

struct SettingsView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.openURL) private var openURL
    @State private var notificationDenied = false
    @State private var confirmClear = false

    private var version: String {
        let info = Bundle.main.infoDictionary
        let name = info?["CFBundleShortVersionString"] as? String ?? ""
        let build = info?["CFBundleVersion"] as? String ?? ""
        return "\(name) (\(build))"
    }

    var body: some View {
        @Bindable var model = model
        List {
            Section("Görünüş") {
                Picker("Tema", selection: $model.theme) {
                    ForEach(ThemeChoice.allCases) { Text(ui: $0.label).tag($0) }
                }
                .listRowBackground(Theme.card)
                NavigationLink("Bölmələri tənzimlə", value: Route.sectionEditor)
                    .listRowBackground(Theme.card)
            }
            Section {
                Picker("Xəbərlərin dili", selection: $model.language) {
                    Text("Bütün dillər").tag("")
                    ForEach(Catalog.languages) { Text($0.label).tag($0.code) }
                }
                .listRowBackground(Theme.card)
            } header: {
                Text("Lent")
            } footer: {
                Text("Şrift ölçüsü telefonun «Mətn ölçüsü» parametrinə uyğun dəyişir.")
            }
            Section {
                Toggle("Son dəqiqə bildirişləri", isOn: Binding(
                    get: { model.notificationsOn },
                    set: { value in
                        Task {
                            let ok = await model.setNotifications(value)
                            if !ok { notificationDenied = true }
                        }
                    }
                ))
                .listRowBackground(Theme.card)
            } header: {
                Text("Bildiriş")
            } footer: {
                Text("Bildiriş telefonun özündə yaranır, heç bir serverdə abunəlik saxlanmır. Yoxlamanın vaxtına iOS qərar verir, ona görə bildiriş gecikə bilər. Tətbiq açıq olanda lent hər dəqiqə yenilənir.")
            }
            Section("Mənbəni açmaq") {
                Toggle("Xəbəri birbaşa mənbədə aç", isOn: $model.opensSourceDirectly)
                    .listRowBackground(Theme.card)
                Toggle("Oxu rejimində aç", isOn: $model.opensInReaderMode)
                    .listRowBackground(Theme.card)
            }
            Section("Məlumat") {
                Button("Yaddaşı təmizlə", role: .destructive) { confirmClear = true }
                    .listRowBackground(Theme.card)
                Button("Məxfilik siyasəti") { Browser.open(AppLinks.privacy) }
                    .listRowBackground(Theme.card)
                Button("Bizə yazın") { openURL(AppLinks.email) }
                    .listRowBackground(Theme.card)
            }
            Section {
                LabeledContent("Versiya", value: version)
                    .listRowBackground(Theme.card)
            }
        }
        .screenBackground()
        .navigationTitle("Tənzimləmələr")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Bildirişə icazə yoxdur", isPresented: $notificationDenied) {
            Button("Parametrləri aç") {
                if let url = URL(string: UIApplication.openSettingsURLString) { openURL(url) }
            }
            Button("Bağla", role: .cancel) {}
        } message: {
            Text("Bildiriş almaq üçün telefonun parametrlərində 8ulduz-a icazə verin.")
        }
        .confirmationDialog("Seçilmişlər, axtarış tarixçəsi və bütün seçimlər silinsin?", isPresented: $confirmClear, titleVisibility: .visible) {
            Button("Sil", role: .destructive) { model.clearAllData() }
            Button("İmtina", role: .cancel) {}
        }
    }
}

struct AboutView: View {
    @Environment(AppModel.self) private var model

    private var sourceNames: String {
        model.sourceRows.map(\.name).sorted { $0.compare($1, locale: Locale(identifier: "az")) == .orderedAscending }.joined(separator: ", ")
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                block("Tətbiq nədir") {
                    Text("8ulduz Azərbaycan və dünya xəbərlərini bir yerə toplayan avtomatik xəbər lentidir. Heç bir xəbər burada yazılmır: başlıq, qısa xülasə və şəkil mənbənin açıq RSS lentindən və ya rəsmi səhifəsindən götürülür, tam mətn mənbənin öz saytında açılır. Lent hər dəqiqə yenilənir.")
                }
                block("Mənbələr") {
                    VStack(alignment: .leading, spacing: 8) {
                        if !model.sourceRows.isEmpty {
                            Text("Hazırda \(model.sourceRows.count) mənbə izlənilir: \(sourceNames).")
                        }
                        NavigationLink("Mənbə vəziyyətinə bax", value: Route.sources)
                            .foregroundStyle(Theme.gold)
                    }
                }
                block("Redaksiya prinsipləri") {
                    VStack(alignment: .leading, spacing: 8) {
                        bullet("Eyni hadisə haqqında yaxın başlıqlı xəbərlər bir kartda birləşir; «N mənbə» nişanı digər mənbələri göstərir.")
                        bullet("Baş səhifədəki böyük kart ən yeni xəbəri yox, son saatlarda ən çox mənbədə çıxan xəbərləri göstərir.")
                        bullet("Bölmələr başlıq və xülasədəki açar sözlərə görə avtomatik təyin olunur; səhv ola bilər.")
                        bullet("Dil süzgəci standart olaraq Azərbaycan dilindədir; rus, ingilis və türk dilində xəbərlər «Bütün dillər» və ya müvafiq dil seçiləndə görünür.")
                        bullet("Ölkə rəhbərliyi haqqında neqativ çağırışlı xəbərlər göstərilmir; bu, sayt sahibinin redaksiya qərarıdır.")
                        bullet("Azərbaycan dövləti və rəhbərliyi haqqında xəbərlər yalnız Azərbaycan mənbələrindən verilir; xarici mənbələrin bu mövzuda xəbərləri (idman istisna olmaqla) dərc edilmir.")
                        bullet("Müxalifət mənbələri lentə daxil edilmir; lentdə yalnız «Mənbələr» siyahısındakı saytlar görünür. Bu da sayt sahibinin redaksiya qərarıdır.")
                        bullet("Bazar məlumatı: valyuta AMB-nin rəsmi məzənnəsi (alınmayanda bazar məzənnəsi, nişanla), neft və bitcoin Yahoo Finance, qızıl və gümüş gold-api.com. Maliyyə məsləhəti deyil.")
                    }
                }
                block("Məxfilik") {
                    VStack(alignment: .leading, spacing: 8) {
                        bullet("Hesab yoxdur, tətbiq heç bir şəxsi məlumat və statistika toplamır.")
                        bullet("Seçilmişlər, bölmə sırası, dil, tema və şəhər seçimi yalnız telefonunuzda saxlanır.")
                        bullet("Hava (Open-Meteo), namaz vaxtı (aladhan.com), şəkillərin kiçildilməsi (wsrv.nl, yalnız şəklin ünvanı gedir), tıxac xəritəsi (Waze) və video (YouTube) telefonunuzdan birbaşa həmin xidmətlərə sorğu göndərir; onların öz məxfilik qaydaları tətbiq olunur. Xəritə və video yalnız düyməyə basanda yüklənir.")
                        Button("Məxfilik siyasəti") { Browser.open(AppLinks.privacy) }
                            .foregroundStyle(Theme.gold)
                    }
                }
                block("Əlaqə") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Səhv, təklif və mənbə əlavəsi üçün yazın. Xəbər mətnlərinin hüququ müvafiq mənbələrə aiddir; mənbə öz xəbərinin göstərilməsini istəmirsə, bildirin, lent siyahıdan çıxarılar.")
                        Link("8ulduz.az@gmail.com", destination: AppLinks.email)
                            .foregroundStyle(Theme.gold)
                        Button("GitHub-da müraciət") { Browser.open(AppLinks.issues) }
                            .foregroundStyle(Theme.gold)
                        Button("8ulduz.az") { Browser.open(AppLinks.site) }
                            .foregroundStyle(Theme.gold)
                    }
                }
            }
            .font(.subheadline)
            .padding(16)
        }
        .screenBackground()
        .navigationTitle("Haqqımızda")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func block<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(ui: title)
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func bullet(_ text: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text(verbatim: "•").foregroundStyle(Theme.gold)
            Text(ui: text)
        }
    }
}
