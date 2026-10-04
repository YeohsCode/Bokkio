import Cocoa

final class Delegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 700, height: 500),
                          styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
        window.title = "Bokkio horizontal scroll"
        let scroll = NSScrollView(frame: window.contentView!.bounds)
        scroll.hasHorizontalScroller = true
        scroll.hasVerticalScroller = true
        scroll.scrollerStyle = .legacy
        scroll.autoresizingMask = [.width, .height]
        let document = NSView(frame: NSRect(x: 0, y: 0, width: 1800, height: 1200))
        for index in 0..<30 {
            let label = NSTextField(labelWithString: "Content \(index + 1)")
            label.frame = NSRect(x: (index % 5) * 350 + 20, y: (index / 5) * 180 + 20, width: 200, height: 30)
            document.addSubview(label)
        }
        scroll.documentView = document
        window.contentView = scroll
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}
let delegate = Delegate()
NSApplication.shared.delegate = delegate
NSApplication.shared.setActivationPolicy(.regular)
NSApplication.shared.run()
