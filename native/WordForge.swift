// WordForge — native macOS front end (glass / vibrancy), talking to the local
// Python API at http://127.0.0.1:8764. No HTML: real NSVisualEffectView window
// blur + SwiftUI material panels. First proof: Stats + Expression ladder.
//
// Build: native/build.command  (swiftc, Command Line Tools — no Xcode needed)

import AppKit
import SwiftUI

let API = "http://127.0.0.1:8764"

// MARK: - cold palette
extension Color {
    static let ice = Color(red: 0.56, green: 0.75, blue: 0.94)      // #8FC0F0 active
    static let sapphire = Color(red: 0.36, green: 0.56, blue: 0.84) // #5B8FD6 accent
    static let frost = Color(red: 0.91, green: 0.93, blue: 0.96)    // text
    static let coldGray = Color(red: 0.54, green: 0.58, blue: 0.65) // muted
}

// MARK: - API models
struct StatsData: Decodable {
    let total_words: Int; let due_now: Int; let reviewed_today: Int
    let reviews_total: Int; let avg_production_score: Double
}
struct StatsResponse: Decodable { let stats: StatsData }
struct Rung: Decodable, Identifiable {
    var id = UUID()
    let kind: String; let rendering: String; let image: String
    let connotation: String; let register: String
    enum CodingKeys: String, CodingKey { case kind, rendering, image, connotation, register }
}
struct Ladder: Decodable { let feeling_question: String; let note: String; let rungs: [Rung] }

@MainActor
final class Model: ObservableObject {
    @Published var stats: StatsData?
    @Published var ladder: Ladder?
    @Published var status = ""
    @Published var busy = false

    func get<T: Decodable>(_ path: String, as: T.Type) async throws -> T {
        let (data, _) = try await URLSession.shared.data(from: URL(string: API + path)!)
        return try JSONDecoder().decode(T.self, from: data)
    }
    func post<T: Decodable>(_ path: String, body: [String: Any], as: T.Type) async throws -> T {
        var req = URLRequest(url: URL(string: API + path)!)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode(T.self, from: data)
    }
    func loadStats() async {
        do { stats = try await get("/api/stats", as: StatsResponse.self).stats }
        catch { status = "Backend not reachable — is the studio server running?" }
    }
    func makeLadder(_ thought: String) async {
        guard !thought.isEmpty else { return }
        busy = true; status = "Thinking…"; ladder = nil
        do { ladder = try await post("/api/expression/ladder", body: ["thought": thought], as: Ladder.self); status = "" }
        catch { status = "Error: \(error.localizedDescription)" }
        busy = false
    }
}

// MARK: - reusable glass card
struct Glass<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content.padding(16)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.07), lineWidth: 1))
    }
}

// MARK: - views
struct Sidebar: View {
    @Binding var tab: String
    let items = [("vocab", "Vocab"), ("express", "Expression"), ("reader", "Reader"),
                 ("writing", "Writing"), ("stats", "Stats")]
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("WordForge").font(.system(size: 18, weight: .medium))
                .foregroundColor(.frost).padding(.horizontal, 10).padding(.vertical, 16)
            ForEach(items, id: \.0) { id, label in
                Button { tab = id } label: {
                    Text(label).frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 8).padding(.horizontal, 10)
                        .foregroundColor(tab == id ? .frost : .coldGray)
                        .background(tab == id ? Color.sapphire.opacity(0.22) : .clear,
                                    in: RoundedRectangle(cornerRadius: 8))
                }.buttonStyle(.plain)
            }
            Spacer()
        }.padding(10).frame(width: 190)
    }
}

struct Metric: View {
    let value: String; let label: String
    var body: some View {
        Glass { VStack(alignment: .leading, spacing: 2) {
            Text(value).font(.system(size: 22, weight: .medium)).foregroundColor(.frost)
            Text(label).font(.system(size: 11)).foregroundColor(.coldGray)
        }.frame(maxWidth: .infinity, alignment: .leading) }
    }
}

struct StatsView: View {
    @ObservedObject var model: Model
    var body: some View {
        let s = model.stats
        HStack(spacing: 10) {
            Metric(value: "\(s?.total_words ?? 0)", label: "words")
            Metric(value: "\(s?.due_now ?? 0)", label: "due now")
            Metric(value: "\(s?.reviewed_today ?? 0)", label: "reviewed today")
            Metric(value: String(format: "%.2f", s?.avg_production_score ?? 0), label: "avg production")
        }
    }
}

struct ExpressionView: View {
    @ObservedObject var model: Model
    @State private var thought = "his eyes are blue and striking"
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Glass { VStack(alignment: .leading, spacing: 10) {
                TextField("a plain thought…", text: $thought, axis: .vertical)
                    .textFieldStyle(.plain).foregroundColor(.frost).lineLimit(1...3)
                HStack {
                    Button("Show ladder") { Task { await model.makeLadder(thought) } }
                        .disabled(model.busy)
                    Text(model.status).font(.system(size: 12)).foregroundColor(.coldGray)
                }
            }}
            if let l = model.ladder {
                Text(l.feeling_question).font(.system(size: 14)).foregroundColor(.ice)
                ForEach(l.rungs) { r in
                    Glass { VStack(alignment: .leading, spacing: 6) {
                        Text(r.kind.uppercased() + " · " + r.register)
                            .font(.system(size: 11)).foregroundColor(.coldGray)
                        Text(r.rendering).font(.custom("Georgia", size: 19)).foregroundColor(.frost)
                        Text("image — \(r.image)  ·  feeling — \(r.connotation)")
                            .font(.system(size: 13)).foregroundColor(.coldGray)
                    }.frame(maxWidth: .infinity, alignment: .leading) }
                }
                Text(l.note).font(.system(size: 13)).italic().foregroundColor(.coldGray)
            }
        }
    }
}

struct Placeholder: View {
    let name: String
    var body: some View {
        Glass { Text("\(name) is in the browser studio (localhost:8764) — native version coming next.")
            .foregroundColor(.coldGray).frame(maxWidth: .infinity, alignment: .leading) }
    }
}

struct RootView: View {
    @StateObject var model = Model()
    @State var tab = "express"
    var body: some View {
        HStack(spacing: 0) {
            Sidebar(tab: $tab)
            Divider().overlay(Color.white.opacity(0.06))
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    switch tab {
                    case "vocab": StatsView(model: model); Placeholder(name: "Vocab drills")
                    case "express": ExpressionView(model: model)
                    case "stats": StatsView(model: model)
                    default: Placeholder(name: tab.capitalized)
                    }
                }.padding(22).frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .frame(minWidth: 820, minHeight: 560)
        .task { await model.loadStats() }
    }
}

// MARK: - AppKit window with vibrancy (the native glass)
class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    func applicationDidFinishLaunching(_ n: Notification) {
        let vfx = NSVisualEffectView()
        vfx.material = .underWindowBackground
        vfx.state = .active
        vfx.blendingMode = .behindWindow
        let host = NSHostingView(rootView: RootView())
        host.frame = vfx.bounds
        host.autoresizingMask = [.width, .height]
        vfx.addSubview(host)

        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 900, height: 620),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isMovableByWindowBackground = true
        window.contentView = vfx
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
