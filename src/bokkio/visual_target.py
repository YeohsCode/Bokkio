"""Window-scoped image matching. Flat or ambiguous templates never choose a point."""
from __future__ import annotations
import base64,io,math

def match_image(png,reference):
    import numpy as np
    from PIL import Image
    image=Image.open(io.BytesIO(png)).convert('L');template=Image.open(io.BytesIO(base64.b64decode(reference['png'],validate=True))).convert('L')
    if image.width*image.height>16000000 or template.width*template.height>65536 or min(template.size)<8:raise ValueError('Image anchor exceeds the size budget')
    threshold=reference.get('threshold',.92)
    if type(threshold) not in {int,float} or not math.isfinite(threshold) or not .7<=threshold<=.99:raise ValueError('Invalid image-match threshold')
    # Coarse-to-fine NCC: downsample the whole capture to <=1000 pixels wide,
    # then correlate bounded templates at common display/DPI scales using FFT.
    ratio=min(1,1000/image.width);image=image.resize((max(1,round(image.width*ratio)),max(1,round(image.height*ratio))))
    a=np.asarray(image,dtype=np.float64);h,w=a.shape;integral=np.pad(a.cumsum(0).cumsum(1),((1,0),(1,0)));squares=np.pad((a*a).cumsum(0).cumsum(1),((1,0),(1,0)));candidates=[]
    for scale in (.5,.75,1,1.25,1.5,2):
        tw,th=max(8,round(template.width*ratio*scale)),max(8,round(template.height*ratio*scale))
        if tw>w or th>h:continue
        b=np.asarray(template.resize((tw,th)),dtype=np.float64);b-=b.mean();variance=(b*b).sum()
        if variance/(tw*th)<16:continue
        shape=(h+th-1,w+tw-1)
        correlation=np.fft.irfft2(np.fft.rfft2(a,s=shape)*np.fft.rfft2(b[::-1,::-1],s=shape),s=shape)[th-1:h,tw-1:w]
        sums=integral[th:,tw:]-integral[:-th,tw:]-integral[th:,:-tw]+integral[:-th,:-tw]
        total=squares[th:,tw:]-squares[:-th,tw:]-squares[th:,:-tw]+squares[:-th,:-tw]
        denominator=np.sqrt(np.maximum(0,total-sums*sums/(tw*th))*variance);scores=np.divide(correlation,denominator,out=np.zeros_like(correlation),where=denominator>1)
        for _ in range(2):
            y,x=np.unravel_index(np.argmax(scores),scores.shape);score=float(scores[y,x]);candidates.append({'score':score,'x':float((x+tw/2)/ratio),'y':float((y+th/2)/ratio),'width':float(tw/ratio),'height':float(th/ratio)})
            scores[max(0,y-th//2):min(scores.shape[0],y+th//2+1),max(0,x-tw//2):min(scores.shape[1],x+tw//2+1)]=-1
    if not candidates:raise ValueError('Image anchor has no distinctive structure')
    candidates.sort(key=lambda v:v['score'],reverse=True);best=candidates[0]
    if best['score']<threshold:raise ValueError('Image anchor was not found')
    others=[v for v in candidates[1:] if abs(v['x']-best['x'])>best['width']/2 or abs(v['y']-best['y'])>best['height']/2]
    if others and best['score']-others[0]['score']<.03:raise ValueError('Image anchor matches multiple targets')
    return best

def capture_match(client,pid,window,reference):
    import base64
    from .macos_capture import screen_point
    response=client.call('desktop.capture',{'app':str(pid),'window':window})
    if response['status']!='completed':raise ValueError(response)
    result=response['result']
    # Read the registered, window-scoped artifact through the existing Runtime.
    raw=client.call('artifact.read',{'artifact_id':result['artifact']['artifact_id'],'max_bytes':10000000})
    if raw['status']!='completed':raise ValueError(raw)
    data=raw['result']
    png=base64.b64decode(data['data_base64'],validate=True)
    match=match_image(png,reference);point=screen_point(result['metadata'],match['x'],match['y']);return point,match
