import Cocoa
_ = NSApplication.shared
let root=URL(fileURLWithPath:"/tmp/bokkio-workflow-fixture")
try? FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
final class Delegate:NSObject,NSApplicationDelegate {
    var window:NSWindow!;let field=NSTextField(string:"");let status=NSTextField(labelWithString:"Ready")
    var clicks=0;var timer:Timer?;var commandVersion="";var duplicate:NSTextField?
    func writeState(){
        let data:[String:Any]=["pid":Int(ProcessInfo.processInfo.processIdentifier),"window_id":window.windowNumber,"input":field.stringValue,"clicks":clicks,"x":window.frame.minX,"y":window.frame.minY]
        if let d=try? JSONSerialization.data(withJSONObject:data,options:[.sortedKeys]) {try? d.write(to:root.appendingPathComponent("state.json"),options:.atomic)}
    }
    @objc func confirm(_ sender:NSButton){clicks+=1;status.stringValue="Confirmed \(clicks)";writeState()}
    func applicationDidFinishLaunching(_ note:Notification){
        window=NSWindow(contentRect:NSRect(x:120,y:300,width:500,height:240),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false);window.title="Bokkio Workflow Lab"
        let view=NSView(frame:NSRect(x:0,y:0,width:500,height:240))
        field.frame=NSRect(x:40,y:150,width:400,height:28);field.setAccessibilityLabel("Workflow Input");field.setAccessibilityIdentifier("workflow-input");view.addSubview(field)
        let b=NSButton(title:"Confirm",target:self,action:#selector(confirm(_:)));b.frame=NSRect(x:40,y:95,width:140,height:32);b.setAccessibilityIdentifier("workflow-confirm");view.addSubview(b)
        status.frame=NSRect(x:40,y:55,width:330,height:25);status.setAccessibilityIdentifier("workflow-status");view.addSubview(status)
        window.contentView=view;window.makeKeyAndOrderFront(nil)
        timer=Timer.scheduledTimer(withTimeInterval:0.05,repeats:true){[weak self]_ in
            guard let self=self else{return}
            if let data=try? Data(contentsOf:root.appendingPathComponent("command.json")),let c=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let id=c["id"] as? String,id != self.commandVersion {
                self.commandVersion=id
                switch c["action"] as? String {
                case "reset":self.field.stringValue="";self.clicks=0;self.status.stringValue="Ready"
                case "move":self.window.setFrameOrigin(NSPoint(x:c["x"] as? Double ?? 400,y:c["y"] as? Double ?? 180))
                case "duplicate":let f=NSTextField(string:"");f.frame=NSRect(x:210,y:95,width:230,height:28);f.setAccessibilityLabel("Workflow Input");f.setAccessibilityIdentifier("workflow-input");self.window.contentView?.addSubview(f);self.duplicate=f
                case "clear-duplicate":self.duplicate?.removeFromSuperview();self.duplicate=nil
                case "front":self.window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
                case "blur":self.window.makeFirstResponder(nil)
                default:break
                }
            };self.writeState()
        };writeState()
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ app:NSApplication)->Bool{true}
}
let delegate=Delegate();NSApplication.shared.delegate=delegate;NSApplication.shared.setActivationPolicy(.regular);NSApplication.shared.run()
