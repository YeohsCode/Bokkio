"""Bounded Mac visual input, with no automatic retries after event posting."""
import json
import math
import subprocess
import sys

from .macos_capture import _helper, capture_window
from .model import BokkioError
from .visual import find_text,validate_capture
from .windows_capture import CaptureError


def perform(metadata,png,text,action,*,value=None,region=None,expect_text=None,verification_region=None,control=None,
            _native_target=None,_post_verify=None):
    if action not in {'click','type','replace'}:
        raise CaptureError('invalid_input','Only click/type/replace are available',dispatched=0)
    if not isinstance(expect_text,str) or not expect_text:
        raise CaptureError('verification_required','Visual input requires explicit post-action text',dispatched=0)
    if action in {'type','replace'} and (not isinstance(value,str) or not value or len(value.encode('utf-16-le'))//2>1000
                           or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise CaptureError('invalid_input','Type requires bounded literal text',dispatched=0)
    if action=='click' and value is not None:
        raise CaptureError('invalid_input','Click does not accept text',dispatched=0)
    if control is not None:
        if control() not in {'continue',None}:
            raise CaptureError('input_cancelled','Input was paused/cancelled before dispatch',dispatched=0)
    if _native_target is None:
        candidate=find_text(metadata,png,text,max_age=15,region=region)
    else:
        # Internal runtime transport: Jev supplies an observed ref, never a
        # point. A fresh native object provides the field bounds; the helper
        # still binds those points to the captured pixels and window identity.
        validate_capture(metadata,png,max_age=15)
        node=_native_target;data=node.get('platform_data',{});box=node.get('bounds')
        if (action!='replace' or node.get('platform')!='macos' or node.get('role')!='combo_box'
                or node.get('state',{}).get('enabled') is False or not data.get('mac_unique_identity')
                or data.get('mac_owner_pid')!=metadata['pid'] or not data.get('ax_value_settable')
                or 'AXConfirm' not in data.get('ax_original_actions',[]) or not isinstance(box,dict)
                or set(box)!={'x','y','width','height'} or any(type(v) not in {int,float} or not math.isfinite(v) for v in box.values())
                or box['width']<=0 or box['height']<=0):
            raise CaptureError('invalid_native_target','Replacement requires a uniquely bound writable native field',dispatched=0)
        rect=metadata['content_rect']
        left=max(box['x'],rect['x']);top=max(box['y'],rect['y'])
        right=min(box['x']+box['width'],rect['x']+rect['width']);bottom=min(box['y']+box['height'],rect['y']+rect['height'])
        if right<=left or bottom<=top:raise CaptureError('invalid_native_target','Native field is outside the captured window',dispatched=0)
        candidate={'source':'native_bounds_bound_to_capture','ref':node['ref'],'pid':metadata['pid'],'window_id':metadata['window_id'],
                   'image_sha256':metadata['image_sha256'],'center_screen':{'x':(left+right)/2,'y':(top+bottom)/2}}
    if not isinstance(metadata.get('process_started_seconds_microseconds'),str) or not isinstance(metadata.get('window_bounds'),dict):
        raise CaptureError('invalid_capture','Input requires a complete native identity contract',dispatched=0)
    if sys.platform!='darwin':raise CaptureError('unsupported_platform','Visual input is currently Mac-only',dispatched=0)
    request={'operation':'input','pid':metadata['pid'],'window_id':metadata['window_id'],
             'output':'unused','expected_birth':metadata['process_started_seconds_microseconds'],
             'expected_content_rect':metadata['content_rect'],'expected_window_bounds':metadata['window_bounds'],
             'image_sha256':metadata['image_sha256'],'captured_at_unix_ns':metadata['captured_at_unix_ns'],
             'point':candidate['center_screen'],'action':action,'text':value or ''}
    helper=_helper()
    if control is not None and control() not in {'continue',None}:
        raise CaptureError('input_cancelled','Input was cancelled before native dispatch',dispatched=0)
    try:
        result=subprocess.run([str(helper)],input=json.dumps(request).encode(),capture_output=True,timeout=10)
    except (subprocess.TimeoutExpired,OSError) as error:
        # A missing receipt cannot establish whether the helper posted events.
        raise CaptureError('input_completion_unknown','Native input receipt is unavailable',dispatched='unknown') from error
    try:
        receipt=json.loads(result.stdout)
        if 'error' in receipt:raise CaptureError(receipt['error'],receipt['message'],**receipt.get('details',{}))
        if (result.returncode or receipt.get('status')!='posted_unverified' or receipt.get('pid')!=metadata['pid']
                or receipt.get('window_id')!=metadata['window_id'] or receipt.get('dispatched') is not True):
            raise ValueError('invalid input receipt')
    except CaptureError:raise
    except (ValueError,TypeError) as error:
        raise CaptureError('input_completion_unknown','Native input receipt is invalid',dispatched='unknown') from error
    # One new observation confirms business output. Any failure after posting
    # remains unknown/unverified; callers must inspect rather than repeat.
    try:
        after,image=capture_window(metadata['pid'],window_id=metadata['window_id'],ocr=True,timeout=15)
        if after['process_started_seconds_microseconds']!=metadata['process_started_seconds_microseconds']:
            raise CaptureError('process_changed','Process changed after input')
        if _post_verify is None:
            verified=find_text(after,image,expect_text,max_age=15,region=verification_region)
        else:
            verified=_post_verify(after,image)
            if not isinstance(verified,dict) or verified.get('passed') is not True:
                raise CaptureError('native_readback_unconfirmed','Native field did not show the committed value')
    except BokkioError as error:
        raise CaptureError('input_completion_unknown','Posted input did not pass explicit text verification',
                           dispatched=True,cause=getattr(error,'code','native_readback_failed')) from error
    return {'status':'confirmed','receipt':receipt,'target':candidate,'verification':verified,'observation':after}
