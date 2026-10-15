import Cocoa
import ApplicationServices
import Darwin

// Passive only: no events are swallowed, replaced or posted by the recorder.
func emit(_ input:[String:Any]) {
    var body=input;body["timestamp"]=Date().timeIntervalSince1970
    if let data=try? JSONSerialization.data(withJSONObject:body,options:[.sortedKeys]) {
        FileHandle.standardOutput.write(data);FileHandle.standardOutput.write(Data([10]))
    }
}
func apps()->[[String:Any]] {
    NSWorkspace.shared.runningApplications.filter{$0.activationPolicy == .regular}.compactMap { a in
        guard let path=a.bundleURL?.path, let name=a.localizedName else{return nil}
        return ["pid":Int(a.processIdentifier),"name":name,"path":path,"bundle_id":a.bundleIdentifier ?? ""]
    }
}
if CommandLine.arguments.contains("--apps") {emit(["apps":apps()]);exit(0)}
if CommandLine.arguments.contains("--environment") {
    let point=CGEvent(source:nil)?.location ?? CGPoint.zero
    emit(["foreground_pid":Int(NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0),"pointer":["x":point.x,"y":point.y]])
    exit(0)
}
let permitted=Set(CommandLine.arguments.dropFirst().compactMap{Int32($0)})
let recordingParent=getppid()
if permitted.isEmpty {emit(["error":"Select applications before recording"]);exit(1)}
if !AXIsProcessTrusted() {emit(["error":"Accessibility permission is required; no permission prompt was requested"]);exit(1)}
let system=AXUIElementCreateSystemWide()
AXUIElementSetMessagingTimeout(system,0.15)
func attr(_ e:AXUIElement,_ name:String)->CFTypeRef? {
    var v:CFTypeRef?;return AXUIElementCopyAttributeValue(e,name as CFString,&v) == .success ? v:nil
}
func text(_ e:AXUIElement,_ name:String)->String {return attr(e,name) as? String ?? ""}
func describe(_ e:AXUIElement)->[String:Any]? {
    var pid:pid_t=0;guard AXUIElementGetPid(e,&pid) == .success,permitted.contains(pid) else{return nil}
    AXUIElementSetMessagingTimeout(e,0.15)
    let role=text(e,"AXRole"),sub=text(e,"AXSubrole")
    if sub == "AXSecureTextField" {return ["pid":Int(pid),"kind":"unsupported","reason":"Secure input is excluded"]}
    var ancestors:[[String:String]]=[];var current=e
    for _ in 0..<32 {
        guard let p=attr(current,"AXParent"),CFGetTypeID(p) == AXUIElementGetTypeID() else{break}
        current=unsafeBitCast(p,to:AXUIElement.self)
        let r=text(current,"AXRole")
        if r == "AXApplication" {break}
        ancestors.append(["role":r,"name":text(current,"AXTitle").isEmpty ? text(current,"AXDescription"):text(current,"AXTitle")])
    }
    let name=text(e,"AXTitle").isEmpty ? text(e,"AXDescription"):text(e,"AXTitle")
    var window="";var windowIdentity=""
    if let w=attr(e,"AXWindow"),CFGetTypeID(w) == AXUIElementGetTypeID() {window=text(unsafeBitCast(w,to:AXUIElement.self),"AXTitle");windowIdentity="ax:"+String(CFHash(w))}
    if window.isEmpty {
        let app=AXUIElementCreateApplication(pid)
        if let w=attr(app,"AXFocusedWindow"),CFGetTypeID(w) == AXUIElementGetTypeID() {window=text(unsafeBitCast(w,to:AXUIElement.self),"AXTitle");windowIdentity="ax:"+String(CFHash(w))}
    }
    var bounds:[String:Double]=[:]
    if let p=attr(e,"AXPosition"),let z=attr(e,"AXSize"),CFGetTypeID(p)==AXValueGetTypeID(),CFGetTypeID(z)==AXValueGetTypeID(){
        var point=CGPoint.zero;var size=CGSize.zero
        if AXValueGetValue(unsafeBitCast(p,to:AXValue.self),.cgPoint,&point),AXValueGetValue(unsafeBitCast(z,to:AXValue.self),.cgSize,&size){bounds=["x":point.x,"y":point.y,"width":size.width,"height":size.height]}
    }
    return ["window_identity":windowIdentity,"bounds":bounds,"pid":Int(pid),"role":role,"name":name,"identifier":text(e,"AXIdentifier"),"ancestors":ancestors,"window":window]
}
var editWork:DispatchWorkItem?
var editTarget:AXUIElement?
var clickTarget:AXUIElement?
var clickBody:[String:Any]?
var clickOrigin=CGPoint.zero
var clickMoved=false
var scrolling:DispatchWorkItem?
func focused()->AXUIElement? {
    guard let pid=NSWorkspace.shared.frontmostApplication?.processIdentifier,permitted.contains(pid) else{return nil}
    let app=AXUIElementCreateApplication(pid)
    guard let p=attr(app,"AXFocusedUIElement"),CFGetTypeID(p) == AXUIElementGetTypeID() else{return nil}
    return unsafeBitCast(p,to:AXUIElement.self)
}
func emitEdit(_ element:AXUIElement) {
    guard var body=describe(element) else{return}
    if body["kind"] as? String == "unsupported" {emit(body);return}
    let role=text(element,"AXRole")
    guard ["AXTextField","AXTextArea","AXComboBox"].contains(role) else {
        body["kind"]="unsupported";body["reason"]="Keyboard interaction has no editable accessibility target";emit(body);return
    }
    guard let value=attr(element,"AXValue") as? String,value.count<=32000 else {
        body["kind"]="unsupported";body["reason"]="Editable value is unavailable or too large";emit(body);return
    }
    body["kind"]="edit";body["value"]=value;emit(body)
}
let observationQueue=DispatchQueue(label:"bokkio.record-observations",qos:.userInitiated)
var dragReported=false
func allowed(_ e:AXUIElement)->Bool {var pid:pid_t=0;return AXUIElementGetPid(e,&pid) == .success && permitted.contains(pid)}
let callback:CGEventTapCallBack={ _,type,event,_ in
    if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
        emit(["error":"Recording event tap stopped; recording is incomplete"]);CFRunLoopStop(CFRunLoopGetMain());return Unmanaged.passUnretained(event)
    }
    if type == .leftMouseDown || type == .rightMouseDown {
        clickMoved=false;clickOrigin=event.location;clickBody=nil
        if let target=editTarget {editWork?.cancel();emitEdit(target);editTarget=nil;editWork=nil}
        var target:AXUIElement?
        if AXUIElementCopyElementAtPosition(system,Float(event.location.x),Float(event.location.y),&target) == .success,let e=target {clickTarget=e;clickBody=describe(e)}
    } else if type == .leftMouseDragged {clickMoved=true
    } else if type == .leftMouseUp || type == .rightMouseUp {
        if var body=clickBody,body["kind"] == nil {
            body["kind"]=clickMoved ? "drag":type == .rightMouseUp ? "right_click":"click"
            body["double_click"]=event.getIntegerValueField(.mouseEventClickState)>1
            body["x"]=clickOrigin.x;body["y"]=clickOrigin.y
            body["end_x"]=event.location.x;body["end_y"]=event.location.y
            emit(body)
        };clickTarget=nil;clickBody=nil
    } else if type == .keyDown {
        guard let target=focused(),allowed(target) else{return Unmanaged.passUnretained(event)}
        let command=event.flags.contains(.maskCommand) || event.flags.contains(.maskControl)
        let code=event.getIntegerValueField(.keyboardEventKeycode)
        if command && event.flags.contains(.maskShift) && [15,35,111].contains(code){return Unmanaged.passUnretained(event)}
        let named:[Int64:String]=[36:"Enter",48:"Tab",53:"Escape",123:"Left",124:"Right",125:"Down",126:"Up",51:"Backspace",117:"Delete",115:"Home",119:"End",116:"PageUp",121:"PageDown"]
        let letters:[Int64:String]=[0:"A",1:"S",2:"D",3:"F",4:"H",5:"G",6:"Z",7:"X",8:"C",9:"V",11:"B",12:"Q",13:"W",14:"E",15:"R",16:"Y",17:"T",31:"O",32:"U",34:"I",35:"P",37:"L",38:"J",40:"K",45:"N",46:"M"]
        if command && code != 9 || named[code] != nil && ![51,117].contains(code) {
            if let edit=editTarget {editWork?.cancel();emitEdit(edit);editTarget=nil}
            if var body=describe(target),body["kind"] == nil,let base=named[code] ?? letters[code] {
                var keys:[String]=[]
                if event.flags.contains(.maskCommand){keys.append("Command")}
                if event.flags.contains(.maskControl){keys.append("Ctrl")}
                if event.flags.contains(.maskAlternate){keys.append("Alt")}
                if event.flags.contains(.maskShift){keys.append("Shift")}
                keys.append(base);body["kind"]="key";body["key"]=keys.joined(separator:"+");emit(body)
            }
        } else {
            editWork?.cancel();editTarget=target;let work=DispatchWorkItem{emitEdit(target)};editWork=work
            observationQueue.asyncAfter(deadline:.now()+0.35,execute:work)
        }
    } else if type == .scrollWheel {
        var target:AXUIElement?
        if AXUIElementCopyElementAtPosition(system,Float(event.location.x),Float(event.location.y),&target) == .success,let e=target,allowed(e),var body=describe(e),body["kind"] == nil {
            let dy=event.getIntegerValueField(.scrollWheelEventDeltaAxis1),dx=event.getIntegerValueField(.scrollWheelEventDeltaAxis2)
            let delta=abs(dy)>abs(dx) ? dy:dx
            if delta != 0 {body["kind"]="scroll";body["direction"]=abs(dy)>abs(dx) ? (dy>0 ? "up":"down"):(dx>0 ? "left":"right");body["amount"]=min(100,abs(delta));body["x"]=event.location.x;body["y"]=event.location.y;emit(body)}
        }
    }
    return Unmanaged.passUnretained(event)
}
let types:[CGEventType]=[.leftMouseDown,.leftMouseUp,.keyDown,.scrollWheel,.rightMouseDown,.rightMouseUp,.leftMouseDragged]
let mask=types.reduce(CGEventMask(0)){$0 | (CGEventMask(1)<<$1.rawValue)}
guard let tap=CGEvent.tapCreate(tap:.cgSessionEventTap,place:.headInsertEventTap,options:.listenOnly,eventsOfInterest:mask,callback:callback,userInfo:nil) else {
    emit(["error":"Input Monitoring permission is required or the session is unavailable; no permission prompt was requested"]);exit(1)
}
let source=CFMachPortCreateRunLoopSource(kCFAllocatorDefault,tap,0)
CFRunLoopAddSource(CFRunLoopGetMain(),source,.commonModes);CGEvent.tapEnable(tap:tap,enable:true)
// Readback also covers IME commits/accessibility editors that update values
// without ordinary keyDown events. Baselines are never emitted as input.
var values:[String:String]=[:]
let pollGate=DispatchSemaphore(value:1)
let poll=Timer(timeInterval:0.2,repeats:true){_ in
    if getppid() != recordingParent {CFRunLoopStop(CFRunLoopGetMain());return}
    guard pollGate.wait(timeout:.now()) == .success else{return}
    observationQueue.async{
    defer{pollGate.signal()}
    for pid in permitted {
    let app=AXUIElementCreateApplication(pid);AXUIElementSetMessagingTimeout(app,0.15)
    guard let p=attr(app,"AXFocusedUIElement"),CFGetTypeID(p) == AXUIElementGetTypeID() else{continue}
    let e=unsafeBitCast(p,to:AXUIElement.self)
    guard let body=describe(e),body["kind"] == nil,
          ["AXTextField","AXTextArea","AXComboBox"].contains(text(e,"AXRole")),
          let value=attr(e,"AXValue") as? String,value.count<=32000 else{continue}
    let identity:[String:Any]=["pid":body["pid"] ?? 0,"role":body["role"] ?? "","name":body["name"] ?? "","identifier":body["identifier"] ?? "","ancestors":body["ancestors"] ?? []]
    guard let bytes=try? JSONSerialization.data(withJSONObject:identity,options:[.sortedKeys]),let key=String(data:bytes,encoding:.utf8) else{continue}
    if let old=values[key],old != value {emitEdit(e)}
    values[key]=value
    }
    }
}
RunLoop.main.add(poll,forMode:.common)
emit(["status":"recording","pids":permitted.sorted()])
signal(SIGTERM,SIG_IGN)
let stopSignal=DispatchSource.makeSignalSource(signal:SIGTERM,queue:.main)
stopSignal.setEventHandler {
    editWork?.cancel()
    if let target=editTarget {emitEdit(target)}
    CFRunLoopStop(CFRunLoopGetMain())
}
stopSignal.resume()
CFRunLoopRun()
