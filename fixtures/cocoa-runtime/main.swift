import Cocoa
_ = NSApplication.shared

// A self-contained native contract fixture, independent of vendored sources.
final class Delegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    let field=NSTextField(string: "")
    let status=NSTextField(labelWithString: "Ready")
    var clicks=0
    var timer:Timer?
    func writeState() {
        guard let path=ProcessInfo.processInfo.environment["BOKKIO_NATIVE_RESULT"] else {return}
        let state:[String:Any]=["pid":ProcessInfo.processInfo.processIdentifier,"window_id":window.windowNumber,
                                "input":field.stringValue,"clicks":clicks]
        if let data=try? JSONSerialization.data(withJSONObject:state,options:[.sortedKeys]) {
            try? data.write(to:URL(fileURLWithPath:path),options:.atomic)
        }
    }
    @objc func confirm(_ sender:NSButton) {
        clicks+=1;status.stringValue="Confirmed \(clicks)";writeState()
    }
    func applicationDidFinishLaunching(_ note:Notification) {
        window=NSWindow(contentRect:NSRect(x:80,y:300,width:480,height:220),styleMask:[.titled,.closable,.miniaturizable],backing:.buffered,defer:false)
        window.title="Bokkio Runtime Contract"
        let view=NSView(frame:NSRect(x:0,y:0,width:480,height:220))
        field.frame=NSRect(x:40,y:140,width:360,height:28)
        field.setAccessibilityLabel("Search");field.setAccessibilityIdentifier("runtime-input")
        view.addSubview(field)
        let button=NSButton(title:"Confirm",target:self,action:#selector(confirm(_:)))
        button.frame=NSRect(x:40,y:90,width:140,height:32);view.addSubview(button)
        status.frame=NSRect(x:40,y:45,width:340,height:25);view.addSubview(status)
        window.contentView=view;window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
        writeState();timer=Timer.scheduledTimer(withTimeInterval:0.05,repeats:true){[weak self] _ in self?.writeState()}
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ app:NSApplication)->Bool {true}
}
let delegate=Delegate()
NSApplication.shared.delegate=delegate
NSApplication.shared.setActivationPolicy(.regular)
NSApplication.shared.run()
