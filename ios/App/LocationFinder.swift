import CoreLocation
import SwiftUI
import UlduzCore

/// «Konumum»: konum yalnız düyməyə basanda soruşulur, cihazda qalır, heç yerə göndərilmir.
/// Ondan yalnız ən yaxın şəhər seçilir; hava və namaz həmin şəhərin koordinatı ilə istənir (app.js `locate`, `nearestCity`).
@MainActor
final class LocationFinder: NSObject, CLLocationManagerDelegate {
    enum Failure: Error { case denied, notFound }

    private let manager = CLLocationManager()
    private var waiting: CheckedContinuation<CLLocation, Error>?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
    }

    func locate() async throws -> CLLocation {
        if let recent = manager.location, recent.timestamp.timeIntervalSinceNow > -600 { return recent }
        switch manager.authorizationStatus {
        case .denied, .restricted: throw Failure.denied
        default: break
        }
        return try await withCheckedThrowingContinuation { continuation in
            waiting?.resume(throwing: Failure.notFound)
            waiting = continuation
            if manager.authorizationStatus == .notDetermined {
                manager.requestWhenInUseAuthorization()
            } else {
                manager.requestLocation()
            }
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            guard self.waiting != nil else { return }
            switch status {
            case .authorizedWhenInUse, .authorizedAlways: self.manager.requestLocation()
            case .denied, .restricted: self.finish(.failure(Failure.denied))
            default: break
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        Task { @MainActor in self.finish(.success(location)) }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        let denied = (error as? CLError)?.code == .denied
        Task { @MainActor in self.finish(.failure(denied ? Failure.denied : Failure.notFound)) }
    }

    private func finish(_ result: Result<CLLocation, Error>) {
        guard let waiting else { return }
        self.waiting = nil
        waiting.resume(with: result)
    }
}

/// Hava və namaz ekranlarındakı düymə: ən yaxın şəhəri seçir.
struct LocateButton: View {
    @Environment(AppModel.self) private var model
    @State private var finder: LocationFinder?
    @State private var busy = false
    @State private var message: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Button {
                Task { await find() }
            } label: {
                Label {
                    Text(LocalizedStringKey(busy ? "Axtarılır…" : "Konumum"))
                } icon: {
                    Image(systemName: "location.fill").foregroundStyle(Theme.gold)
                }
            }
            .disabled(busy)
            if let message {
                Text(ui: message).font(.caption).foregroundStyle(Theme.muted)
            }
        }
        .accessibilityHint(Text("Konumunuza ən yaxın şəhər"))
    }

    private func find() async {
        busy = true
        message = nil
        defer { busy = false }
        let finder = self.finder ?? LocationFinder()
        self.finder = finder
        do {
            let here = try await finder.locate()
            if let city = Catalog.nearestCity(lat: here.coordinate.latitude, lon: here.coordinate.longitude) {
                model.cityName = city.name
            } else {
                message = "Yaxında şəhər tapılmadı"
            }
        } catch LocationFinder.Failure.denied {
            message = "Konuma icazə verilmədi"
        } catch {
            message = "Konum tapılmadı"
        }
    }
}
