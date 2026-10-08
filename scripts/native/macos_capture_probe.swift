import Cocoa
import ScreenCaptureKit
import Foundation
_ = NSApplication.shared
let args = CommandLine.arguments
let pid = pid_t(args[1])!
let target = URL(fileURLWithPath: args[2])
let title = args[3]
func emit(_ data: [String:Any], _ code: Int32) {
    print(String(data: try! JSONSerialization.data(withJSONObject: data, options: [.sortedKeys]), encoding: .utf8)!)
    exit(code)
}
if !CGPreflightScreenCaptureAccess() { emit(["error":"screen_capture_permission_missing"],1) }
Task { @MainActor in
    do {
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: false)
        let matches = content.windows.filter { $0.owningApplication?.processID == pid && $0.title == title }
        guard matches.count == 1 else { emit(["error":"owned_window_count", "count":matches.count],1); return }
        let window = matches[0]
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        config.width = Int(filter.contentRect.width * Double(filter.pointPixelScale))
        config.height = Int(filter.contentRect.height * Double(filter.pointPixelScale))
        config.showsCursor = false
        config.ignoreShadowsSingleWindow = true
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        let rep = NSBitmapImageRep(cgImage: image)
        try rep.representation(using: .png, properties: [:])!.write(to: target)
        emit(["pid":pid,"window_id":window.windowID,"width":image.width,"height":image.height,
              "point_pixel_scale":filter.pointPixelScale,"source_width":filter.contentRect.width,
              "source_height":filter.contentRect.height],0)
    } catch { emit(["error":"native_capture_failed","message":String(describing:error)],1) }
}
dispatchMain()
