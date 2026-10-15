// Independent UX actor. AX only reads targets; mutations use global mouse/key events.
import Cocoa
import ApplicationServices
let input=(try! JSONSerialization.jsonObject(with:Data(CommandLine.arguments[1].utf8))) as! [String:String]
let command=input["command"]!,title=input["window"] ?? "Bokkio UX.txt"
func fail(_ message:String)->Never {FileHandle.standardError.write(Data(message.utf8));exit(1)}
func attr(_ e:AXUIElement,_ key:String)->CFTypeRef? {var v:CFTypeRef?;return AXUIElementCopyAttributeValue(e,key as CFString,&v) == .success ? v:nil}
func str(_ e:AXUIElement,_ key:String)->String {attr(e,key) as? String ?? ""}
func application(_ bundle:String)->NSRunningApplication {
 guard let a=NSRunningApplication.runningApplications(withBundleIdentifier:bundle).first else{fail("Expected running application: "+bundle)};return a
}
func window(_ app:NSRunningApplication,_ name:String)->AXUIElement {
 let root=AXUIElementCreateApplication(app.processIdentifier)
 let rows=(attr(root,"AXWindows") as? [AXUIElement] ?? []).filter{str($0,"AXTitle")==name}
 if rows.count != 1 {fail("Expected one test window: "+name)};return rows[0]
}
func descendants(_ e:AXUIElement)->[AXUIElement] {
 var result:[AXUIElement]=[],pending=[e]
 while !pending.isEmpty && result.count<4000 {let n=pending.removeLast();result.append(n);pending.append(contentsOf:attr(n,"AXChildren") as? [AXUIElement] ?? [])};return result
}
func bounds(_ e:AXUIElement)->CGRect {
 guard let p=attr(e,"AXPosition"),let z=attr(e,"AXSize"),CFGetTypeID(p)==AXValueGetTypeID(),CFGetTypeID(z)==AXValueGetTypeID() else{fail("Visible target bounds unavailable")}
 var point=CGPoint.zero,size=CGSize.zero
 AXValueGetValue(unsafeBitCast(p,to:AXValue.self),.cgPoint,&point);AXValueGetValue(unsafeBitCast(z,to:AXValue.self),.cgSize,&size)
 return CGRect(origin:point,size:size)
}
func front(_ app:NSRunningApplication,_ win:AXUIElement) {
 app.activate(options:[])
 for _ in 0..<100 {if NSWorkspace.shared.frontmostApplication?.processIdentifier==app.processIdentifier{break};RunLoop.current.run(until:Date(timeIntervalSinceNow:0.02))}
 guard NSWorkspace.shared.frontmostApplication?.processIdentifier==app.processIdentifier else{fail("Application did not become foreground")}
 // Bring this test document forward through its actual title-bar mouse surface.
 let root=AXUIElementCreateApplication(app.processIdentifier)
 if let focused=attr(root,"AXFocusedWindow"),CFEqual(focused,win){return}
 let b=bounds(win);click(CGPoint(x:b.minX+b.width*0.5,y:b.minY+12))
}
let source=CGEventSource(stateID:.hidSystemState)
func post(_ event:CGEvent?){guard let e=event else{fail("Could not construct OS input")};e.post(tap:.cghidEventTap)}
func click(_ point:CGPoint){post(CGEvent(mouseEventSource:source,mouseType:.mouseMoved,mouseCursorPosition:point,mouseButton:.left));post(CGEvent(mouseEventSource:source,mouseType:.leftMouseDown,mouseCursorPosition:point,mouseButton:.left));Thread.sleep(forTimeInterval:0.06);post(CGEvent(mouseEventSource:source,mouseType:.leftMouseUp,mouseCursorPosition:point,mouseButton:.left));Thread.sleep(forTimeInterval:0.15)}
func clickElement(_ e:AXUIElement){let b=bounds(e);click(CGPoint(x:b.midX,y:b.midY))}
func combo(_ code:CGKeyCode,_ flags:CGEventFlags=[]){let down=CGEvent(keyboardEventSource:source,virtualKey:code,keyDown:true);down?.flags=flags;post(down);let up=CGEvent(keyboardEventSource:source,virtualKey:code,keyDown:false);up?.flags=[];post(up);Thread.sleep(forTimeInterval:0.08)}
func type(_ value:String){if value.isEmpty{combo(51);return};var units=Array(value.utf16);let down=CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:true);down?.keyboardSetUnicodeString(stringLength:units.count,unicodeString:&units);post(down);post(CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:false));Thread.sleep(forTimeInterval:0.4)}
func editor()->(NSRunningApplication,AXUIElement,AXUIElement) {
 let app=application("com.apple.TextEdit"),win=window(app,title)
 let fields=descendants(win).filter{str($0,"AXRole")=="AXTextArea"}
 if fields.count != 1 {fail("Expected one test editor")};return (app,win,fields[0])
}
func calculator()->(NSRunningApplication,AXUIElement){let app=application("com.apple.calculator");return(app,window(app,"Calculator"))}
func calcButton(_ id:Set<String>){let (_,win)=calculator();let found=descendants(win).filter{id.contains(str($0,"AXIdentifier")) && str($0,"AXRole")=="AXButton"};if found.count != 1{fail("Calculator button unavailable: "+id.joined(separator:","))};clickElement(found[0])}
func read()->[String:Any] {
 let (_,_,field)=editor();var result:[String:Any]=["editor":str(field,"AXValue")]
 if !NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.calculator").isEmpty {
  let (_,win)=calculator();let areas=descendants(win).filter{str($0,"AXIdentifier")=="StandardInputView"}
  let values=areas.flatMap{descendants($0)}.filter{str($0,"AXRole")=="AXStaticText"}.map{str($0,"AXValue")}
  result["calculator"]=values.joined().unicodeScalars.filter{!CharacterSet.controlCharacters.contains($0)}.map{String($0)}.joined()
 }else{result["calculator"]=NSNull()};return result
}
if command=="editor" {let (a,w,e)=editor();front(a,w);clickElement(e);combo(0,.maskCommand);type(input["value"] ?? "")}
else if command=="open-second" {
 if !NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.calculator").isEmpty{fail("Close Calculator before testing an application opened during recording")}
 // Spotlight is the actual user-facing application launcher.
 combo(49,.maskCommand);type("Calculator");combo(36)
 for _ in 0..<100 {
  if let app=NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.calculator").first {
   let wins=attr(AXUIElementCreateApplication(app.processIdentifier),"AXWindows") as? [AXUIElement] ?? []
   if wins.contains(where:{str($0,"AXTitle")=="Calculator"}){break}
  }
  RunLoop.current.run(until:Date(timeIntervalSinceNow:0.05))
 }
 _=calculator()
}
else if command=="calculator" || command=="reset-second" {
 let (a,w)=calculator();front(a,w);calcButton(["AllClear","Clear"]);calcButton(["AllClear","Clear"])
 if command=="calculator" {for id in ["Seven","Add","Two","Equals"]{calcButton([id])}}
}
else if command=="close-second" {if !NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.calculator").isEmpty{let (a,w)=calculator();front(a,w);combo(12,.maskCommand);for _ in 0..<100{if NSRunningApplication.runningApplications(withBundleIdentifier:"com.apple.calculator").isEmpty{break};RunLoop.current.run(until:Date(timeIntervalSinceNow:0.02))}}}
else if command != "read" {fail("Unknown UX command")}
let data=try! JSONSerialization.data(withJSONObject:read(),options:[.sortedKeys]);print(String(data:data,encoding:.utf8)!)
