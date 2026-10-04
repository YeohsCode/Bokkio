import Cocoa

final class Delegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    let search = NSTextField()
    let result = NSTextField(labelWithString: "Ready")
    func applicationDidFinishLaunching(_ notification: Notification) {
        let name = Bundle.main.object(forInfoDictionaryKey: "CFBundleName") as? String ?? "BokkioWorkflow"
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 520, height: 160),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = name
        search.frame = NSRect(x: 20, y: 100, width: 320, height: 28)
        search.setAccessibilityLabel("Search")
        result.frame = NSRect(x: 20, y: 45, width: 470, height: 28)
        result.setAccessibilityLabel("Ready")
        let submit = NSButton(title: "Submit", target: self, action: #selector(submitValue))
        submit.frame = NSRect(x: 360, y: 98, width: 130, height: 32)
        submit.setAccessibilityLabel("Submit")
        window.contentView!.addSubview(search)
        window.contentView!.addSubview(submit)
        window.contentView!.addSubview(result)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    @objc func submitValue(_ sender: Any?) {
        let text = "Submitted: " + search.stringValue
        result.stringValue = text
        result.setAccessibilityLabel(text)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
let delegate = Delegate()
NSApplication.shared.delegate = delegate
NSApplication.shared.setActivationPolicy(.regular)
NSApplication.shared.run()
