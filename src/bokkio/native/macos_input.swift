import Cocoa
import ApplicationServices
func result(_ body:[String:Any]) {if let d=try? JSONSerialization.data(withJSONObject:body){FileHandle.standardOutput.write(d)}}
let eventTag:Int64 = 0x424B494F
var request:[String:Any] = [:]
func controlState()->[String:Any]? {
    guard let path=request["control_file"] as? String,let data=FileManager.default.contents(atPath:path) else{return nil}
    return (try? JSONSerialization.jsonObject(with:data)) as? [String:Any]
}
func allowed()->Bool {
    guard request["control_file"] != nil else{return true}
    guard let state=controlState(),state["allowed"] as? Bool == true,
          state["generation"] as? Int == request["control_generation"] as? Int,
          let expires=state["expires"] as? Double,expires>Date().timeIntervalSince1970 else{return false}
    return true
}
func held(_ name:String)->Bool {
    if request["control_file"] == nil{return false}
    guard let state=controlState(),let expires=state["expires"] as? Double,expires>Date().timeIntervalSince1970 else{return true}
    return (state["physical_held"] as? [String] ?? []).contains(name)
}
func cleanupPost(_ event:CGEvent?) {event?.setIntegerValueField(.eventSourceUserData,value:eventTag);event?.post(tap:.cghidEventTap)}
var dispatched=false
var mouseHeld:CGMouseButton?
var keyHeld:CGKeyCode?
func fail(_ message:String)->Never {
    if let button=mouseHeld,!held(button == .right ? "mouse:2":"mouse:1") {let point=CGEvent(source:nil)?.location ?? .zero;cleanupPost(CGEvent(mouseEventSource:nil,mouseType:button == .right ? .rightMouseUp:.leftMouseUp,mouseCursorPosition:point,mouseButton:button))}
    if let key=keyHeld,!held("key:"+String(key)) {let up=CGEvent(keyboardEventSource:nil,virtualKey:key,keyDown:false);up?.flags=[];cleanupPost(up)}
    result(["error":message,"dispatched":dispatched]);exit(1)}
guard let r=(try? JSONSerialization.jsonObject(with:FileHandle.standardInput.readDataToEndOfFile())) as? [String:Any],let pid=r["pid"] as? Int,let action=r["action"] as? String else{fail("Invalid input request")}
request=r
if !allowed(){fail("User takeover: desktop input paused")}
if !AXIsProcessTrusted(){fail("Accessibility authorization is required")}
guard let app=NSRunningApplication(processIdentifier:pid_t(pid)) else{fail("Target application exited")}
if !allowed(){fail("User takeover: desktop input paused")}
dispatched=true
app.activate(options:[.activateIgnoringOtherApps])
for _ in 0..<80 {if NSWorkspace.shared.frontmostApplication?.processIdentifier==pid_t(pid){break};RunLoop.current.run(until:Date(timeIntervalSinceNow:0.025))}
let ax=AXUIElementCreateApplication(pid_t(pid));var value:CFTypeRef?
if !allowed(){fail("User takeover: desktop input paused")}
_=AXUIElementSetAttributeValue(ax,kAXFrontmostAttribute as CFString,kCFBooleanTrue)
if let title=r["window"] as? String,!title.isEmpty {
    var available:CFTypeRef?
    guard AXUIElementCopyAttributeValue(ax,kAXWindowsAttribute as CFString,&available) == .success,
          let windows=available as? [AXUIElement] else{fail("Target windows are unavailable")}
    let matches=windows.filter{ w in
        var name:CFTypeRef?
        return AXUIElementCopyAttributeValue(w,kAXTitleAttribute as CFString,&name) == .success && name as? String == title
    }
    guard matches.count == 1 else{fail("Target window is absent or ambiguous")}
    let win=matches[0]
    if !allowed(){fail("User takeover: desktop input paused")}
    _=AXUIElementPerformAction(win,kAXRaiseAction as CFString)
    _=AXUIElementSetAttributeValue(ax,kAXFocusedWindowAttribute as CFString,win)
    RunLoop.current.run(until:Date(timeIntervalSinceNow:0.15))
    guard AXUIElementCopyAttributeValue(ax,kAXFocusedWindowAttribute as CFString,&value) == .success,
          let focused=value,CFEqual(focused,win) else{fail("Target window did not receive focus")}

}
for _ in 0..<80 {if NSWorkspace.shared.frontmostApplication?.processIdentifier==pid_t(pid){break};RunLoop.current.run(until:Date(timeIntervalSinceNow:0.025))}
if NSWorkspace.shared.frontmostApplication?.processIdentifier != pid_t(pid){fail("Target window did not become foreground")}
if ["key","type","replace_text"].contains(action),let target=r["target"] as? [String:Any],!["window","application"].contains(target["role"] as? String ?? "") {
    var focused:CFTypeRef?
    if AXUIElementCopyAttributeValue(ax,kAXFocusedUIElementAttribute as CFString,&focused) != .success {fail("No focused keyboard target")}
    let element=unsafeBitCast(focused!,to:AXUIElement.self);var identifier:CFTypeRef?
    if let wanted=target["identifier"] as? String,!wanted.isEmpty {
        if AXUIElementCopyAttributeValue(element,"AXIdentifier" as CFString,&identifier) != .success || identifier as? String != wanted {fail("Keyboard focus differs from target")}
    }
    if let b=target["bounds"] as? [String:Double] {
        var p:CFTypeRef?,z:CFTypeRef?;var point=CGPoint.zero;var size=CGSize.zero
        guard AXUIElementCopyAttributeValue(element,kAXPositionAttribute as CFString,&p) == .success,AXUIElementCopyAttributeValue(element,kAXSizeAttribute as CFString,&z) == .success,AXValueGetValue(unsafeBitCast(p!,to:AXValue.self),.cgPoint,&point),AXValueGetValue(unsafeBitCast(z!,to:AXValue.self),.cgSize,&size),abs(point.x-(b["x"] ?? 0))<1,abs(point.y-(b["y"] ?? 0))<1,abs(size.width-(b["width"] ?? 0))<1,abs(size.height-(b["height"] ?? 0))<1 else {fail("Keyboard focus geometry differs from target")}
    }
}
let source=CGEventSource(stateID:.privateState)
let point=CGPoint(x:r["x"] as? Double ?? 0,y:r["y"] as? Double ?? 0)
if ["click","double_click","right_click","scroll","drag"].contains(action) {
    let system=AXUIElementCreateSystemWide();var hit:AXUIElement?
    if AXUIElementCopyElementAtPosition(system,Float(point.x),Float(point.y),&hit) != .success{fail("Cannot hit-test input point")}
    var owner:pid_t=0;if AXUIElementGetPid(hit!,&owner) != .success || owner != pid_t(pid){fail("Input point is occluded")}
}
func post(_ event:CGEvent?,release:Bool=false){if !release && !allowed(){fail("User takeover: desktop input paused")};if !release,let file=r["cancel_file"] as? String,FileManager.default.fileExists(atPath:file){fail("Input cancelled")};guard let e=event else{fail("Event creation failed")};if release {let name=e.type == .keyUp ? "key:"+String(e.getIntegerValueField(.keyboardEventKeycode)):(e.type == .rightMouseUp ? "mouse:2":"mouse:1");if held(name){return}};dispatched=true;e.setIntegerValueField(.eventSourceUserData,value:eventTag);e.post(tap:.cghidEventTap)}
func mouse(_ type:CGEventType,_ p:CGPoint,_ button:CGMouseButton = .left,_ count:Int64=1){let e=CGEvent(mouseEventSource:source,mouseType:type,mouseCursorPosition:p,mouseButton:button);e?.setIntegerValueField(.mouseEventClickState,value:count);let release=type == .leftMouseUp || type == .rightMouseUp;post(e,release:release);if type == .leftMouseDown || type == .rightMouseDown {mouseHeld=button}else if release{mouseHeld=nil}}
let keycodes:[String:CGKeyCode]=["a":0,"s":1,"d":2,"f":3,"h":4,"g":5,"z":6,"x":7,"c":8,"v":9,"b":11,"q":12,"w":13,"e":14,"r":15,"y":16,"t":17,"1":18,"2":19,"3":20,"4":21,"6":22,"5":23,"9":25,"7":26,"8":28,"0":29,"o":31,"u":32,"i":34,"p":35,"enter":36,"return":36,"l":37,"j":38,"k":40,"n":45,"m":46,"tab":48,"space":49,"backspace":51,"escape":53,"esc":53,"delete":117,"left":123,"right":124,"down":125,"up":126,"home":115,"end":119,"pageup":116,"pagedown":121,"f1":122,"f2":120,"f3":99,"f4":118,"f5":96,"f6":97,"f7":98,"f8":100,"f9":101,"f10":109,"f11":103,"f12":111]
switch action {
case "click","double_click","right_click":
    let right=action=="right_click"
    mouse(.mouseMoved,point)
    for n in 1...(action=="double_click" ? 2:1){mouse(right ? .rightMouseDown:.leftMouseDown,point,right ? .right:.left,Int64(n));mouse(right ? .rightMouseUp:.leftMouseUp,point,right ? .right:.left,Int64(n));Thread.sleep(forTimeInterval:0.06)}
case "key":
    let parts=(r["key"] as? String ?? "").lowercased().split(separator:"+").map{String($0).trimmingCharacters(in:.whitespaces)}
    var flags=CGEventFlags();var code:CGKeyCode?
    for p in parts {switch p {case "command","cmd","meta":flags.insert(.maskCommand);case "ctrl","control":flags.insert(.maskControl);case "shift":flags.insert(.maskShift);case "alt","option":flags.insert(.maskAlternate);default:guard let k=keycodes[p],code==nil else{fail("Unknown or multiple non-modifier keys")};code=k}}
    guard let k=code else{fail("Key combination lacks a key")}
    let down=CGEvent(keyboardEventSource:source,virtualKey:k,keyDown:true);down?.flags=flags;post(down);keyHeld=k
    let up=CGEvent(keyboardEventSource:source,virtualKey:k,keyDown:false);up?.flags=[];post(up,release:true);keyHeld=nil
case "type","replace_text":
    if action == "replace_text" {let down=CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:true);down?.flags=[.maskCommand];post(down);keyHeld=0;let up=CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:false);up?.flags=[];post(up,release:true);keyHeld=nil;RunLoop.current.run(until:Date(timeIntervalSinceNow:0.05))}
    let units=Array((r["text"] as? String ?? "").utf16)
    for i in stride(from:0,to:units.count,by:128){var chunk=Array(units[i..<min(i+128,units.count)]);let down=CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:true);down?.flags=[];down?.keyboardSetUnicodeString(stringLength:chunk.count,unicodeString:&chunk);post(down);let up=CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:false);up?.flags=[];up?.keyboardSetUnicodeString(stringLength:chunk.count,unicodeString:&chunk);post(up,release:true);Thread.sleep(forTimeInterval:0.03)}
case "scroll":
    mouse(.mouseMoved,point)
    let direction=r["direction"] as? String ?? "down",amount=Int32(r["amount"] as? Double ?? 3)*(direction=="down" || direction=="left" ? -1:1)
    post(CGEvent(scrollWheelEvent2Source:source,units:.line,wheelCount:2,wheel1:direction=="up" || direction=="down" ? amount:0,wheel2:direction=="left" || direction=="right" ? amount:0,wheel3:0))
case "drag":
    let end=CGPoint(x:r["end_x"] as? Double ?? point.x,y:r["end_y"] as? Double ?? point.y),duration=r["duration"] as? Double ?? 0.4
    mouse(.mouseMoved,point);mouse(.leftMouseDown,point)
    for i in 1...20 {if NSWorkspace.shared.frontmostApplication?.processIdentifier != pid_t(pid){mouse(.leftMouseUp,point);fail("Foreground changed during drag")};let f=Double(i)/20;mouse(.leftMouseDragged,CGPoint(x:point.x+(end.x-point.x)*f,y:point.y+(end.y-point.y)*f));Thread.sleep(forTimeInterval:duration/20)}
    mouse(.leftMouseUp,end)
default:fail("Unsupported input action")
}
RunLoop.current.run(until:Date(timeIntervalSinceNow:0.15))
result(["status":"posted_unverified","dispatched":dispatched,"pid":pid,"transport":"macOS.CGEvent"])
