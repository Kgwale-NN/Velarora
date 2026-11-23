"""Corroborate screenshot detections with fresh evidence from the captured PC."""
import threading
import time
from backend.core.foreground_app import local_windows_target
from workstation.app_presence import snapshot, window_boxes

_lock=threading.Lock()
_samples={}
_regions={}
_window_reporting=set()
MAX_AGE=5


def record(computer_id,apps,process='',windows=None):
    with _lock:
        now=time.monotonic()
        for cid in list(_samples):
            if now-_samples[cid][1]>MAX_AGE:
                del _samples[cid]
                _regions.pop(cid,None)
        if apps is None:
            _window_reporting.discard(computer_id)
            if process.casefold()=='notepad.exe':
                _samples[computer_id]=({'notepad.exe':True},now)
            else:
                _samples.pop(computer_id,None)
        else:
            _window_reporting.add(computer_id)
            _samples[computer_id]=({key:value for key,value in apps.items() if key=='notepad.exe'},now)
        if windows is None:
            _regions.pop(computer_id,None)
        else:
            _regions[computer_id]=([b for b in windows if b[0]<b[2] and b[1]<b[3]],now)


def current(computer_id,host):
    # Use this server's processes only when it is also the captured Windows PC.
    if local_windows_target(host or ''):
        return snapshot()
    with _lock:
        sample=_samples.get(computer_id)
        return sample[0] if sample and time.monotonic()-sample[1]<=MAX_AGE else None


def corroborate(result,computer_id,host):
    from ultralytics.engine.results import Results
    if not isinstance(result,Results) or result.boxes is None:
        return result
    apps=current(computer_id,host)
    if apps and apps.get('notepad.exe') is True:
        return result
    keep=[i for i,box in enumerate(result.boxes)
          if str(result.names[int(box.cls[0])]).strip().casefold()!='notepad']
    # For this supported native app, missing/stale evidence is unverified,
    # not permission to raise an alarm from an ambiguous screenshot.
    return result[keep]


def refine(result,computer_id,host,model,image,**predict):
    """Let the AI inspect confirmed native windows, rather than similar browser panels.

    Window extents come from Windows. Confidence still comes from model
    inference on the actual window pixels; no AI score is fabricated.
    """
    from ultralytics.engine.results import Results
    if not isinstance(result,Results) or result.boxes is None:return result
    if not any(str(name).strip().casefold()=='notepad' for name in result.names.values()):return result
    apps=current(computer_id,host)
    if not apps or apps.get('notepad.exe') is not True:return corroborate(result,computer_id,host)
    if local_windows_target(host or ''):
        regions=window_boxes(frame_shape=image.shape)
    else:
        with _lock:
            sample=_regions.get(computer_id)
            regions=sample[0] if sample and time.monotonic()-sample[1]<=MAX_AGE else None
    keep=[i for i,b in enumerate(result.boxes) if str(result.names[int(b.cls[0])]).strip().casefold()!='notepad']
    filtered=result[keep]
    if regions is None:
        # A current client explicitly reports that Notepad is running but could
        # not provide a visible window. Do not trust a dashboard-shaped box.
        # Older clients have no window API, so keep their prior visual path.
        with _lock:
            reports_windows=computer_id in _window_reporting
        return filtered if reports_windows or local_windows_target(host or '') else result
    H,W=image.shape[:2];verified=[]
    for x1,y1,x2,y2 in regions:
        left=max(0,int(x1*W));top=max(0,int(y1*H));right=min(W,int(x2*W));bottom=min(H,int(y2*H))
        if right-left<16 or bottom-top<16:continue
        prediction=model([image[top:bottom,left:right]],**predict)[0]
        boxes=[b for b in prediction.boxes if str(prediction.names[int(b.cls[0])]).strip().casefold()=='notepad']
        if boxes:
            best=max(boxes,key=lambda b:float(b.conf[0]))
            verified.append([left,top,right,bottom,float(best.conf[0]),int(best.cls[0])])
    if verified:
        import torch
        data=filtered.boxes.data
        filtered.update(boxes=torch.cat((data,data.new_tensor(verified)),dim=0))
    return filtered
