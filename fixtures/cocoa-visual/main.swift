import Cocoa

// The app paints the business UI. No NSButton/NSTextField child controls or
// accessibility business labels are exposed; OCR must read the actual pixels.
final class Canvas: NSView {
    let duplicate = ProcessInfo.processInfo.environment["BOKKIO_VISUAL_DUPLICATE"] == "1"
    let iconOnly = ProcessInfo.processInfo.environment["BOKKIO_VISUAL_ICON"] == "1"
    var input=""
    var clicks=0
    var focused=false
    var changed:(()->Void)?
    override var acceptsFirstResponder:Bool { true }
    override var isFlipped: Bool { true }
    override func isAccessibilityElement() -> Bool { false }
    override func accessibilityChildren() -> [Any]? { [] }
    override func mouseDown(with event:NSEvent) {
        let point=convert(event.locationInWindow,from:nil)
        focused=NSRect(x:60,y:100,width:340,height:48).contains(point)
        if NSRect(x:60,y:175,width:210,height:52).contains(point) { clicks+=1 }
        window?.makeFirstResponder(self); needsDisplay=true; changed?()
    }
    override func keyDown(with event:NSEvent) {
        if focused, let value=event.characters { input+=value; needsDisplay=true; changed?() }
    }
    override func draw(_ dirtyRect: NSRect) {
        NSColor.white.setFill(); bounds.fill()
        func text(_ value: String, _ x: CGFloat, _ y: CGFloat, color: NSColor = .black) {
            value.draw(at: NSPoint(x:x,y:y),withAttributes:[.font:NSFont.systemFont(ofSize:20),.foregroundColor:color])
        }
        text("Bokkio visual task",60,35)
        NSColor(calibratedRed:0.94,green:0.97,blue:1,alpha:1).setFill()
        NSRect(x:60,y:100,width:340,height:48).fill()
        text(input.isEmpty ? "Enter code" : input,70,110)
        NSColor(calibratedRed:0.15,green:0.3,blue:0.85,alpha:1).setFill()
        NSRect(x:60,y:175,width:210,height:52).fill()
        if iconOnly {
            NSColor.white.setFill()
            let icon=NSBezierPath()
            icon.move(to:NSPoint(x:150,y:185));icon.line(to:NSPoint(x:150,y:216))
            icon.line(to:NSPoint(x:178,y:200));icon.close();icon.fill()
        } else { text("Run check",75,188,color:.white) }
        text(clicks == 0 ? "Ready" : "Checked",60,265)
        text("Clicks: \(clicks)",60,305)
        if duplicate {
            NSColor(calibratedRed:0.15,green:0.3,blue:0.85,alpha:1).setFill()
            NSRect(x:330,y:245,width:210,height:52).fill()
            text("Run check",345,258,color:.white)
        }
        let marks: [(NSColor,NSRect)] = [
            (NSColor(calibratedRed:161/255,green:11/255,blue:206/255,alpha:1),NSRect(x:8,y:8,width:16,height:16)),
            (NSColor(calibratedRed:19/255,green:203/255,blue:101/255,alpha:1),NSRect(x:bounds.width-24,y:8,width:16,height:16)),
            (NSColor(calibratedRed:211/255,green:50/255,blue:33/255,alpha:1),NSRect(x:8,y:bounds.height-24,width:16,height:16)),
            (NSColor(calibratedRed:36/255,green:104/255,blue:172/255,alpha:1),NSRect(x:bounds.width-24,y:bounds.height-24,width:16,height:16))]
        for (color,area) in marks { color.setFill(); area.fill() }
    }
}

final class Delegate: NSObject, NSApplicationDelegate {
    var windows: [NSWindow] = []
    var lastCommand = ""
    var timer: Timer?
    func writeState(command: String? = nil) {
        guard let path=ProcessInfo.processInfo.environment["BOKKIO_VISUAL_STATE"],let window=windows.first else {return}
        let displays=NSScreen.screens.enumerated().map { index,screen -> [String:Any] in
            ["index":index,"frame":["x":screen.frame.minX,"y":screen.frame.minY,
             "width":screen.frame.width,"height":screen.frame.height],"scale":screen.backingScaleFactor]
        }
        var state:[String:Any] = ["pid":ProcessInfo.processInfo.processIdentifier,
            "window_id":window.windowNumber,"window_count":windows.count,
            "window_ids":windows.map{$0.windowNumber},"subviews":window.contentView!.subviews.count,
            "client_width":window.contentView!.bounds.width,"client_height":window.contentView!.bounds.height,
            "frame":["x":window.frame.minX,"y":window.frame.minY,"width":window.frame.width,"height":window.frame.height],
            "expected_content_rect":["x":window.frame.minX,"y":NSScreen.screens[0].frame.maxY-window.frame.maxY,
                                     "width":window.frame.width,"height":window.frame.height],
            "scale":window.backingScaleFactor,"displays":displays,
            "minimized":window.isMiniaturized,
            "on_screen":(CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]])?.contains(where:{$0[kCGWindowNumber as String] as? Int == window.windowNumber}) == true,
            "duplicate":ProcessInfo.processInfo.environment["BOKKIO_VISUAL_DUPLICATE"] == "1"]
        if let command=command {state["command_id"]=command}
        if let data=try? JSONSerialization.data(withJSONObject:state,options:[.sortedKeys]) {
            try? data.write(to:URL(fileURLWithPath:path),options:.atomic)
        }
    }
    func pollControl() {
        // Disposable-fixture control only. It never executes code or touches other apps.
        guard let path=ProcessInfo.processInfo.environment["BOKKIO_VISUAL_CONTROL"],
              let data=try? Data(contentsOf:URL(fileURLWithPath:path)),
              let args=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
              let id=args["id"] as? String,
              let action=args["action"] as? String,let window=windows.first else {return}
        if id == lastCommand {writeState(command:id);return}
        lastCommand=id
        switch action {
        case "front": window.deminiaturize(nil);window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
        case "move":
            if let x=args["x"] as? Double,let y=args["y"] as? Double {window.setFrameOrigin(NSPoint(x:x,y:y))}
        case "resize":
            if let width=args["width"] as? Double,let height=args["height"] as? Double {
                window.setContentSize(NSSize(width:width,height:height))
            }
        case "display":
            if let index=args["index"] as? Int,NSScreen.screens.indices.contains(index) {
                let frame=NSScreen.screens[index].visibleFrame
                window.setFrameOrigin(NSPoint(x:frame.minX+40,y:frame.minY+40))
            }
        case "minimize": window.miniaturize(nil)
        case "repaint":
            if let canvas=window.contentView as? Canvas {canvas.input="CHANGED";canvas.needsDisplay=true;canvas.changed?()}
        case "rebuild":
            let replacement=NSWindow(contentRect:NSRect(x:180,y:180,width:640,height:360),
                                     styleMask:[.titled,.closable,.miniaturizable],backing:.buffered,defer:false)
            replacement.title="BokkioVisual";replacement.contentView=window.contentView
            window.contentView=nil;window.isReleasedWhenClosed=false;windows[0]=replacement
            replacement.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
            window.close()
        default: break
        }
        window.contentView?.displayIfNeeded()
        writeState(command:id)
    }
    func applicationDidFinishLaunching(_ note: Notification) {
        let count = ProcessInfo.processInfo.environment["BOKKIO_VISUAL_WINDOWS"] == "2" ? 2 : 1
        for index in 0..<count {
            let window = NSWindow(contentRect:NSRect(x:180+index*650,y:180,width:640,height:360),
                                  styleMask:[.titled,.closable,.miniaturizable],backing:.buffered,defer:false)
            window.title = "BokkioVisual"
            let canvas=Canvas(frame:NSRect(x:0,y:0,width:640,height:360))
            window.contentView=canvas; window.makeKeyAndOrderFront(nil); windows.append(window)
            if let path=ProcessInfo.processInfo.environment["BOKKIO_VISUAL_RESULT"] {
                canvas.changed = {
                    let result:[String:Any] = ["pid":ProcessInfo.processInfo.processIdentifier,"input":canvas.input,"clicks":canvas.clicks]
                    if let data=try? JSONSerialization.data(withJSONObject:result) { try? data.write(to:URL(fileURLWithPath:path)) }
                }
                canvas.changed?()
            }
        }
        NSApp.activate(ignoringOtherApps:true)
        let environment=ProcessInfo.processInfo.environment
        if let path=environment["BOKKIO_VISUAL_STATE"] {
            let window=windows[0]
            let screen=NSScreen.screens[0]
            let state:[String:Any] = ["pid":ProcessInfo.processInfo.processIdentifier,
                "window_id":window.windowNumber,"subviews":window.contentView!.subviews.count,
                "window_count":windows.count,"duplicate":environment["BOKKIO_VISUAL_DUPLICATE"] == "1",
                "expected_content_rect":["x":window.frame.minX,"y":screen.frame.maxY-window.frame.maxY,
                                         "width":window.frame.width,"height":window.frame.height],
                "client_width":window.contentView!.bounds.width,"client_height":window.contentView!.bounds.height]
            if let data=try? JSONSerialization.data(withJSONObject:state,options:[.sortedKeys]) {
                try? data.write(to:URL(fileURLWithPath:path))
            }
        }
        if environment["BOKKIO_VISUAL_MINIMIZE"] == "1" { windows[0].miniaturize(nil) }
        writeState()
        if environment["BOKKIO_VISUAL_CONTROL"] != nil {
            timer=Timer.scheduledTimer(withTimeInterval:0.03,repeats:true){[weak self] _ in self?.pollControl()}
        }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ app:NSApplication)->Bool { true }
}
let delegate=Delegate()
NSApplication.shared.delegate=delegate
NSApplication.shared.setActivationPolicy(.regular)
NSApplication.shared.run()
