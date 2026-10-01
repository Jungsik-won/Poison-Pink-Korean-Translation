import Foundation
import Vision
import AppKit
let dir=URL(fileURLWithPath:CommandLine.arguments[1])
let files=try FileManager.default.contentsOfDirectory(at:dir,includingPropertiesForKeys:nil).filter{$0.pathExtension=="png"}.sorted{$0.lastPathComponent<$1.lastPathComponent}
for file in files {
 let request=VNRecognizeTextRequest()
 request.recognitionLevel = .accurate
 request.recognitionLanguages=["ja-JP","en-US"]
 request.usesLanguageCorrection=false
 try VNImageRequestHandler(url:file,options:[:]).perform([request])
 let rows=(request.results ?? []).compactMap { ob -> [String:Any]? in
  guard let t=ob.topCandidates(1).first else{return nil}
  return ["text":t.string,"confidence":t.confidence,"x":ob.boundingBox.minX,"y":ob.boundingBox.minY,"w":ob.boundingBox.width,"h":ob.boundingBox.height]
 }
 let obj:[String:Any]=["file":file.lastPathComponent,"text":rows]
 let data=try JSONSerialization.data(withJSONObject:obj,options:[.sortedKeys])
 print(String(data:data,encoding:.utf8)!)
}
