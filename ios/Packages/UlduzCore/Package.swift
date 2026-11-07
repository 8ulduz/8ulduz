// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "UlduzCore",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "UlduzCore", targets: ["UlduzCore"]),
    ],
    targets: [
        .target(name: "UlduzCore"),
        .testTarget(name: "UlduzCoreTests", dependencies: ["UlduzCore"]),
    ]
)
