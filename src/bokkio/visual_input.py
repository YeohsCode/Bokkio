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
            _native_target=None,_post_verify=None,_return_image=False,_confirm=True,_finish_typing=False,_expand=False,_native_option=False,_end_field_edit=False,_use_paste=False,_native_selection=None):
    if _native_selection is not None and (_native_target is None or action!='click' or _post_verify is None):
        raise CaptureError('invalid_input','Selection-bound button input requires a native target and readback',dispatched=0)
    if type(_use_paste) is not bool or (_use_paste and (_native_target is None or action!='replace')):
        raise CaptureError('invalid_input','Paste requires a bound native replacement',dispatched=0)
    if type(_end_field_edit) is not bool or (_end_field_edit and (_native_target is None or action!='replace' or _confirm)):
        raise CaptureError('invalid_input','Draft completion requires a bound unsubmitted field',dispatched=0)
    if type(_native_option) is not bool or (_native_option and (_native_target is None or action!='click')):
        raise CaptureError('invalid_input','Option input requires a bound native choice',dispatched=0)
    if type(_expand) is not bool or (_expand and (_native_target is None or action!='click')):
        raise CaptureError('invalid_input','Expansion requires a bound native field',dispatched=0)
    if type(_finish_typing) is not bool or (_finish_typing and action!='type'):
        raise CaptureError('invalid_input','Finishing text editing requires a type action',dispatched=0)
    if type(_confirm) is not bool or (not _confirm and (_native_target is None or action!='replace')):
        raise CaptureError('invalid_input','Draft replacement requires a bound native field',dispatched=0)
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
        field=(node.get('role') in {'combo_box','text_field'} and data.get('ax_value_settable')
               and 'AXConfirm' in data.get('ax_original_actions',[]) and (action=='replace' or _expand))
        option=(_native_option and node.get('role')=='text_field' and data.get('native_option_command')
                and not data.get('ax_value_settable') and node.get('name')==node.get('value')
                and type(data.get('ax_native_identity')) is int and node.get('state',{}).get('visible') is True
                and isinstance(data.get('native_option_combo_identifier'),str)
                and isinstance(data.get('native_option_viewport'),dict))
        button=(_native_selection is not None and node.get('role')=='button'
                and node.get('state',{}).get('visible') is True and 'AXPress' in data.get('ax_original_actions',[])
                and isinstance(node.get('name'),str) and 0<len(node['name'])<=1024
                and type(data.get('ax_native_identity')) is int)
        if button:
            selection=_native_selection;selection_data=selection.get('platform_data',{})
            if (selection.get('role')!='text_area' or selection.get('platform')!='macos'
                    or not selection_data.get('mac_unique_identity') or selection_data.get('mac_owner_pid')!=metadata['pid']
                    or type(selection_data.get('ax_native_identity')) is not int
                    or not isinstance(selection.get('state',{}).get('selected_text'),str)
                    or not 0<len(selection['state']['selected_text'])<=4000):
                raise CaptureError('invalid_native_target','Button input requires a uniquely bound nonempty text selection',dispatched=0)
        if (not (field or option or button) or node.get('platform')!='macos' or node.get('state',{}).get('enabled') is False
                or not data.get('mac_unique_identity') or data.get('mac_owner_pid')!=metadata['pid']
                or not isinstance(box,dict) or set(box)!={'x','y','width','height'}
                or any(type(v) not in {int,float} or not math.isfinite(v) for v in box.values())
                or box['width']<=0 or box['height']<=0):
            raise CaptureError('invalid_native_target','Input requires a uniquely bound writable field or readonly option',dispatched=0)
        rect=metadata['content_rect']
        left=max(box['x'],rect['x']);top=max(box['y'],rect['y'])
        right=min(box['x']+box['width'],rect['x']+rect['width']);bottom=min(box['y']+box['height'],rect['y']+rect['height'])
        if right<=left or bottom<=top:raise CaptureError('invalid_native_target','Native field is outside the captured window',dispatched=0)
        candidate={'source':'native_bounds_bound_to_capture','ref':node['ref'],'pid':metadata['pid'],'window_id':metadata['window_id'],
                   'image_sha256':metadata['image_sha256'],'center_screen':{'x':right-min(9,(right-left)/4) if _expand else (left+right)/2,'y':(top+bottom)/2}}
    if not isinstance(metadata.get('process_started_seconds_microseconds'),str) or not isinstance(metadata.get('window_bounds'),dict):
        raise CaptureError('invalid_capture','Input requires a complete native identity contract',dispatched=0)
    if sys.platform!='darwin':raise CaptureError('unsupported_platform','Visual input is currently Mac-only',dispatched=0)
    request={'operation':'input','pid':metadata['pid'],'window_id':metadata['window_id'],
             'output':'unused','expected_birth':metadata['process_started_seconds_microseconds'],
             'expected_content_rect':metadata['content_rect'],'expected_window_bounds':metadata['window_bounds'],
             'image_sha256':metadata['image_sha256'],'captured_at_unix_ns':metadata['captured_at_unix_ns'],
             'point':candidate['center_screen'],'action':action,'text':value or '', 'confirm':_confirm,
             'finish_typing':_finish_typing,'end_field_edit':_end_field_edit,'use_paste':_use_paste}
    if _native_target is not None:
        data=_native_target['platform_data']
        identifier=data.get('ax_identifier')
        if _native_selection is not None:
            request['native_button']={'name':_native_target['name'],'identity':data['ax_native_identity'],
                                     'bounds':_native_target['bounds'],'value':_native_target.get('value'),
                                     'selection_identity':_native_selection['platform_data']['ax_native_identity'],
                                     'selected_text':_native_selection['state']['selected_text']}
        elif _native_option:
            request['native_option']={'value':_native_target['value'],'identity':data['ax_native_identity'],
                                      'bounds':_native_target['bounds'],
                                      'combo_identifier':data['native_option_combo_identifier'],
                                      'viewport':data['native_option_viewport']}
        elif isinstance(identifier,str) and identifier and len(identifier)<=1024:
            request['native_field']={'role':'AXTextField' if _native_target['role']=='text_field' else 'AXComboBox','identifier':identifier,
                                     'bounds':_native_target['bounds'],'value':_native_target.get('value'),'expand':_expand}
        elif (isinstance(_native_target.get('name'),str) and 0<len(_native_target['name'])<=1024
              and type(data.get('ax_native_identity')) is int):
            request['native_field']={'role':'AXTextField' if _native_target['role']=='text_field' else 'AXComboBox','name':_native_target['name'],
                                     'identity':data['ax_native_identity'],'bounds':_native_target['bounds'],
                                     'value':_native_target.get('value'),'expand':_expand}
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
                raise CaptureError('native_readback_unconfirmed','Native field did not show the committed value',
                                   verification=verified if isinstance(verified,dict) else None)
    except BokkioError as error:
        raise CaptureError('input_completion_unknown','Posted input did not pass explicit text verification',
                           dispatched=True,cause=getattr(error,'code','native_readback_failed'),
                           verification=getattr(error,'details',{}).get('verification'),receipt=receipt) from error
    result={'status':'confirmed','receipt':receipt,'target':candidate,'verification':verified,'observation':after}
    if _return_image:result['_observation_image']=image
    return result
