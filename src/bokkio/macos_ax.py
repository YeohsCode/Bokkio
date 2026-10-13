"""Read actual Mac AX capabilities and dispatch to freshly matched AX objects.

xa11y normalizes AXConfirm to press but dispatches press as AXPress. This
supplement retains the original action and probes writable combo values.
Matching is bounded and must resolve one native object in the current tree;
geometry alone never establishes identity. No pointer or key events are used.
"""
from __future__ import annotations

import ctypes as c
import math
import time
from collections import defaultdict

from .model import BokkioActionError,BokkioCompletionUnknown,BokkioError,stable_hash
from .selector import flatten


class Point(c.Structure):
    _fields_=[('x',c.c_double),('y',c.c_double)]


class Size(c.Structure):
    _fields_=[('width',c.c_double),('height',c.c_double)]


class MacAX:
    def __init__(self):
        self.ax=c.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        self.cf=c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self._owned=[];self._targets={}
        def bind(lib,name,args,result):
            fn=getattr(lib,name);fn.argtypes=args;fn.restype=result
        ptr=c.c_void_p
        bind(self.ax,'AXUIElementCreateApplication',[c.c_int],ptr)
        bind(self.ax,'AXUIElementCreateSystemWide',[],ptr)
        bind(self.ax,'AXUIElementCopyAttributeValue',[ptr,ptr,c.POINTER(ptr)],c.c_int)
        bind(self.ax,'AXUIElementCopyActionNames',[ptr,c.POINTER(ptr)],c.c_int)
        bind(self.ax,'AXUIElementIsAttributeSettable',[ptr,ptr,c.POINTER(c.c_bool)],c.c_int)
        bind(self.ax,'AXUIElementSetAttributeValue',[ptr,ptr,ptr],c.c_int)
        bind(self.ax,'AXUIElementPerformAction',[ptr,ptr],c.c_int)
        bind(self.ax,'AXValueGetValue',[ptr,c.c_int,ptr],c.c_bool)
        bind(self.ax,'AXValueGetType',[ptr],c.c_int)
        bind(self.ax,'AXUIElementSetMessagingTimeout',[ptr,c.c_float],c.c_int)
        bind(self.ax,'AXUIElementGetPid',[ptr,c.POINTER(c.c_int)],c.c_int)
        bind(self.cf,'CFRelease',[ptr],None)
        bind(self.cf,'CFRetain',[ptr],ptr)
        bind(self.cf,'CFHash',[ptr],c.c_ulong)
        bind(self.cf,'CFEqual',[ptr,ptr],c.c_bool)
        bind(self.cf,'CFGetTypeID',[ptr],c.c_ulong)
        bind(self.cf,'CFStringCreateWithCString',[ptr,c.c_char_p,c.c_uint],ptr)
        bind(self.cf,'CFStringGetCString',[ptr,c.c_char_p,c.c_long,c.c_uint],c.c_bool)
        bind(self.cf,'CFStringGetLength',[ptr],c.c_long)
        bind(self.cf,'CFArrayGetCount',[ptr],c.c_long)
        bind(self.cf,'CFArrayGetValueAtIndex',[ptr,c.c_long],ptr)
        bind(self.cf,'CFBooleanGetValue',[ptr],c.c_bool)
        for name in ['CFStringGetTypeID','CFArrayGetTypeID','CFBooleanGetTypeID','CFNumberGetTypeID']:
            bind(self.cf,name,[],c.c_ulong)
        bind(self.cf,'CFURLGetTypeID',[],c.c_ulong)
        bind(self.cf,'CFURLCopyFileSystemPath',[ptr,c.c_int],ptr)
        # A timeout on the application AX object applies only to that object.
        # Bound the default for this caller process too, including xa11y's
        # independently created child objects. This is not an OS preference.
        system=self.ax.AXUIElementCreateSystemWide()
        try:
            if self.ax.AXUIElementSetMessagingTimeout(system,3):
                raise BokkioError('Mac AX read timeout could not be configured')
        finally:self.cf.CFRelease(system)

    def close(self):
        for ptr in self._owned:self.cf.CFRelease(ptr)
        self._owned=[];self._targets={}
        self._deadline=None

    def __del__(self):
        if hasattr(self,'_owned'):self.close()

    def _string(self,text):
        return self.cf.CFStringCreateWithCString(None,text.encode('utf-8'),0x08000100)

    def _attr(self,element,name):
        self._prepare_read(element)
        if not element:return None
        key=self._string(name);out=c.c_void_p()
        try:
            error=self.ax.AXUIElementCopyAttributeValue(element,key,c.byref(out))
            if error:return None
            self._owned.append(out.value);return out.value
        finally:self.cf.CFRelease(key)

    def _prepare_read(self,element):
        deadline=getattr(self,'_deadline',None)
        if deadline is not None and time.monotonic()>deadline:
            raise BokkioError('Mac AX capability observation exceeds time budget')
        if element:
            self.ax.AXUIElementSetMessagingTimeout(element,.3)

    def _text(self,ptr):
        if not ptr or self.cf.CFGetTypeID(ptr)!=self.cf.CFStringGetTypeID():return None
        length=self.cf.CFStringGetLength(ptr)
        if length>100000:return None
        buf=c.create_string_buffer(length*4+1)
        return buf.value.decode('utf-8') if self.cf.CFStringGetCString(ptr,buf,len(buf),0x08000100) else None

    def _boolean(self,element,name):
        value=self._attr(element,name)
        if not value or self.cf.CFGetTypeID(value)!=self.cf.CFBooleanGetTypeID():return None
        return bool(self.cf.CFBooleanGetValue(value))

    def _array(self,ptr):
        if not ptr or self.cf.CFGetTypeID(ptr)!=self.cf.CFArrayGetTypeID():return []
        count=self.cf.CFArrayGetCount(ptr)
        if count>4096:raise BokkioError('Mac AX array exceeds observation budget')
        return [self.cf.CFArrayGetValueAtIndex(ptr,i) for i in range(count)]

    def _url_path(self,ptr):
        if not ptr or self.cf.CFGetTypeID(ptr)!=self.cf.CFURLGetTypeID():return None
        path=self.cf.CFURLCopyFileSystemPath(ptr,0)
        if not path:return None
        self._owned.append(path);return self._text(path)

    def _settable(self,element,name):
        self._prepare_read(element)
        key=self._string(name);value=c.c_bool()
        try:return self.ax.AXUIElementIsAttributeSettable(element,key,c.byref(value))==0 and value.value
        finally:self.cf.CFRelease(key)

    def _actions(self,element):
        self._prepare_read(element)
        out=c.c_void_p()
        if self.ax.AXUIElementCopyActionNames(element,c.byref(out)):return []
        self._owned.append(out.value)
        return [self._text(p) for p in self._array(out.value)]

    def _bounds(self,element):
        point=self._attr(element,'AXPosition');size=self._attr(element,'AXSize')
        if not point or not size or self.ax.AXValueGetType(point)!=1 or self.ax.AXValueGetType(size)!=2:return None
        p=Point();s=Size()
        if not self.ax.AXValueGetValue(point,1,c.byref(p)) or not self.ax.AXValueGetValue(size,2,c.byref(s)):return None
        # xa11y reports integer point geometry.
        if not all(math.isfinite(v) for v in (p.x,p.y,s.width,s.height)):
            return None
        return (int(p.x),int(p.y),int(s.width),int(s.height))

    @staticmethod
    def _key(role,name,identifier,bounds,window=None):
        return (role,name,identifier,bounds,window)

    def _menu_tree(self,element,pid,parent=None,path=(),seen=None):
        """AXMenuBar is a separate app attribute, absent from xa11y children.

        Hidden leaf commands retain their actual bound AXPress capability.
        All actions are still bound by annotate() to one actual AX object.
        """
        seen=[] if seen is None else seen
        if any(self.cf.CFEqual(element,old) for old in seen):return None
        if len(seen)>=2048 or len(path)>32:raise BokkioError('Mac menu traversal exceeds budget')
        seen.append(element)
        raw_role=self._text(self._attr(element,'AXRole'))
        role={'AXMenuBar':'menu_bar','AXMenuBarItem':'menu_item','AXMenu':'menu','AXMenuItem':'menu_item'}.get(raw_role)
        if role is None:return None
        name=self._text(self._attr(element,'AXTitle')) or self._text(self._attr(element,'AXDescription')) or ''
        box=self._bounds(element)
        enabled=self._attr(element,'AXEnabled')
        enabled=self.cf.CFBooleanGetValue(enabled) if enabled and self.cf.CFGetTypeID(enabled)==self.cf.CFBooleanGetTypeID() else None
        ref=stable_hash(['mac-menu',pid,*path,raw_role,name])
        children=[]
        for index,child in enumerate(self._array(self._attr(element,'AXChildren'))):
            node=self._menu_tree(child,pid,ref,(*path,index),seen)
            if node is not None:children.append(node)
        visible=bool(box and box[2]>0 and box[3]>0)
        submenus=[n for n in children if n['role']=='menu']
        expanded=any(n['state']['visible'] for n in submenus) if submenus else None
        return {'ref':ref,'role':role,'name':name,'value':None,
                'bounds':dict(zip(('x','y','width','height'),box)) if box else None,
                'state':{'enabled':enabled,'visible':visible,'focused':None,'selected':None,'checked':None,'expanded':expanded},
                'actions':[],'parent':parent,'children':children,'platform':'macos',
                'platform_data':{'ax_role':raw_role,'ax_identifier':self._text(self._attr(element,'AXIdentifier')),
                                 'native_menu_attribute':True}}

    def annotate(self,tree,pid):
        self.close()
        self._deadline=time.monotonic()+15
        app=self.ax.AXUIElementCreateApplication(pid);self._owned.append(app)
        self.ax.AXUIElementSetMessagingTimeout(app,.3)
        frontmost=self._boolean(app,'AXFrontmost')
        if frontmost is not None:
            tree['state'].update(focused=frontmost,active=frontmost)
            tree['platform_data']['ax_frontmost']=frontmost
        menu=self._attr(app,'AXMenuBar')
        if menu and not any(n['role']=='menu_bar' for n in flatten([tree])):
            menu_tree=self._menu_tree(menu,pid,tree['ref'])
            if menu_tree:tree['children'].append(menu_tree)
        candidates=defaultdict(list);stack=[(app,0,None)];visited=defaultdict(list);count=0;visits=0
        if menu:stack.append((menu,0,None))
        while stack:
            self._prepare_read(stack[-1][0])
            element,depth,window_context=stack.pop();identity=int(self.cf.CFHash(element));visits+=1
            if visits>16384:raise BokkioError('Mac AX capability alias traversal exceeds budget')
            # Same hash may be a collision: compare the actual CF object.
            if any(self.cf.CFEqual(element,old) for old in visited[identity]):continue
            count+=1
            if count>4096 or depth>64:
                raise BokkioError(f'Mac AX capability traversal exceeds budget (unique={count}, depth={depth}, visits={visits})')
            visited[identity].append(element)
            owner=c.c_int()
            if self.ax.AXUIElementGetPid(element,c.byref(owner)) or owner.value!=pid:continue
            role=self._text(self._attr(element,'AXRole'))
            title=self._text(self._attr(element,'AXTitle'))
            scope_titles=tree['platform_data'].get('window_scope_titles')
            if role=='AXWindow' and scope_titles and title not in scope_titles:
                continue
            description=self._text(self._attr(element,'AXDescription'))
            identifier=self._text(self._attr(element,'AXIdentifier'))
            bounds=self._bounds(element)
            if role=='AXWindow':window_context=(title,bounds)
            record=(element,identity)
            for name in {title,description}:
                candidates[self._key(role,name,identifier,bounds,window_context)].append(record)
            stack.extend((child,depth+1,window_context) for child in self._array(self._attr(element,'AXChildren')))
        identity_refs=defaultdict(list)
        popup_names={n['name'] for n in flatten([tree]) if n['role'] in {'window','dialog'}}
        nodes={n['ref']:n for n in flatten([tree])}
        for node in nodes.values():
            window_node=node
            while window_node['platform_data'].get('ax_role')!='AXWindow' and window_node['parent'] in nodes:
                window_node=nodes[window_node['parent']]
            window_context=None
            if window_node['platform_data'].get('ax_role')=='AXWindow':
                box=window_node['bounds']
                window_context=(window_node['platform_data'].get('AXTitle',window_node['name']),tuple(box.values()) if box else None)
            data=node['platform_data'];bounds=node['bounds']
            key=self._key(data.get('ax_role'),node['name'],data.get('ax_identifier'),tuple(bounds.values()) if bounds else None,window_context)
            matches=candidates.get(key,[])
            if len(matches)!=1:continue
            element,identity=matches[0]
            if data.get('ax_role')=='AXWindow':
                data['ax_document']=self._text(self._attr(element,'AXDocument'))
                for state,attribute in [('focused','AXFocused'),('active','AXMain')]:
                    actual=self._boolean(element,attribute)
                    if actual is not None:
                        node['state'][state]=actual
                        data[state+'_source']=attribute
            actions=self._actions(element)
            native=[]
            if 'AXPress' in actions or 'AXConfirm' in actions:native.append('click')
            if 'AXShowMenu' in actions:native.append('expand')
            if data.get('ax_role')=='AXPopUpButton' and 'AXPress' in actions:native.append('expand')
            writable=node['role'] in {'text_field','text_area','combo_box'} and self._settable(element,'AXValue')
            if writable:native.append('set_value')
            focus_settable=node['role'] in {'text_field','text_area','combo_box'} and self._settable(element,'AXFocused')
            if focus_settable:native.append('focus')
            data['ax_focus_settable']=focus_settable
            if node['role']=='combo_box' and 'AXConfirm' in actions:
                native.append('submit')
                if 'AXPress' not in actions:
                    node['actions']=[a for a in node['actions'] if a!='click']
                    native=[a for a in native if a!='click']
            data.update(ax_native_identity=identity,mac_owner_pid=pid,ax_original_actions=actions,ax_value_settable=writable)
            if data.get('native_menu_attribute') and data.get('ax_role')=='AXMenuItem' and node['name'] and 'AXPress' in actions:
                data['native_menu_command']=True
            selected=self._text(self._attr(element,'AXSelectedText')) if node['role'] in {'text_field','text_area'} else None
            if selected is not None:node['state']['selected_text']=selected
            if 'AXShowMenu' in actions and node['name'] and node['role']=='combo_box' and node['state'].get('expanded') is None:
                node['state']['expanded']=node['name'] in popup_names
                data['expanded_source']='same_process_named_AX_popup'
            if node['role'] in {'text_field','text_area'} and self._settable(element,'AXSelectedTextRange') and isinstance(node['value'],str):
                native.append('select_text')
                data['ax_selection_focus_settable']=self._settable(element,'AXFocused')
            data['mac_verified_actions']=native
            node['actions']=sorted(set(node['actions'])|set(native))
            if writable:node['state']['editable']=True
            self._targets[node['ref']]=(element,identity,actions,pid)
            identity_refs[identity].append(node)
            parent=nodes.get(node['parent'])
            if (node['role']=='text_field' and not node['name'] and isinstance(node['value'],str) and node['value']
                    and not writable and 'AXConfirm' in actions and parent
                    and parent['platform_data'].get('ax_role')=='AXList'):
                node['name']=node['value'];node['actions']=['click'];node['state']['editable']=False
                data.update(native_option_command=True,name_source='native_readonly_list_value',mac_verified_actions=['click'])
                owner=parent
                while owner['parent'] in nodes and owner['role']!='combo_box':owner=nodes[owner['parent']]
                if owner['role']=='combo_box' and self._settable(element,'AXSelected'):
                    node['actions']=['select'];data['mac_verified_actions']=['select']
                    data['mac_selection_source']='AXSelected_then_combo_confirm'
                viewport=parent
                while viewport['parent'] in nodes and viewport['platform_data'].get('ax_role')!='AXScrollArea':viewport=nodes[viewport['parent']]
                clip=viewport['bounds'];box=node['bounds']
                if clip and box:
                    node['state']['visible']=(box['y']+box['height']>clip['y'] and box['y']<clip['y']+clip['height']
                                             and box['x']+box['width']>clip['x'] and box['x']<clip['x']+clip['width'])
            if 'AXOpen' in actions:
                path=self._url_path(self._attr(element,'AXURL'))
                filename=self._text(self._attr(element,'AXFilename'))
                if path and filename:
                    node['name']=filename;node['actions']=['open']
                    node['state']['editable']=False
                    data.update(native_file_entry=True,ax_url_path=path,name_source='AXFilename',mac_verified_actions=['open'])
        # A propagated structural ambiguity can be resolved by a uniquely
        # matched native CF object. Hash collisions/duplicate aliases stay gated.
        for group in identity_refs.values():
            if len(group)==1:group[0]['platform_data']['mac_unique_identity']=True
        self._label_fields(tree)
        for node in flatten([tree]):
            if node['role']=='combo_box' and 'AXShowMenu' in node['platform_data'].get('ax_original_actions',[]):
                choices=[n for n in flatten(node['children']) if n['platform_data'].get('native_option_command')]
                if choices:
                    node['state']['expanded']=True;node['platform_data']['expanded_source']='native_readonly_list_choices'
        self._deadline=None
        return tree

    @staticmethod
    def _label_fields(tree):
        """Name an already bound field from one aligned native sibling label.

        This is a label association only: geometry never adds action capability
        or replaces the unique AX object used for dispatch.
        """
        for parent in flatten([tree]):
            fields=[n for n in parent['children'] if n['role'] in {'combo_box','text_field'}
                    and not n['name'] and n['bounds'] and n['platform_data'].get('mac_unique_identity')]
            labels=[n for n in parent['children'] if n['role']=='static_text' and n['bounds']
                    and n['name'] and n['name'].endswith(':')]
            pairs={}
            for field in fields:
                box=field['bounds']
                candidates=[label for label in labels
                            if (abs(label['bounds']['x']-box['x'])<=2
                            and abs(label['bounds']['width']-box['width'])<=2
                            and 0<=box['y']-label['bounds']['y']-label['bounds']['height']<=10)
                            or (0<=box['x']-label['bounds']['x']-label['bounds']['width']<=10
                                and abs((box['y']+box['height']/2)-(label['bounds']['y']+label['bounds']['height']/2))<=3)]
                if len(candidates)==1:pairs[field['ref']]=candidates[0]
            for field in fields:
                label=pairs.get(field['ref'])
                if label and sum(l['ref']==label['ref'] for l in pairs.values())==1:
                    field['name']=label['name']
                    field['platform_data'].update(name_source='unique_aligned_native_sibling_label',label_ref=label['ref'])

    def perform(self,node,action,value=None):
        target=self._targets.get(node['ref'])
        if not target or target[1]!=node['platform_data'].get('ax_native_identity'):
            raise BokkioActionError('Mac native target is no longer bound')
        element,identity,actions,pid=target
        if action not in node['platform_data'].get('mac_verified_actions',[]):
            raise BokkioActionError('Mac native action is not advertised')
        if action=='set_value':
            current=self._attr(element,'AXValue')
            if current and self.cf.CFGetTypeID(current)==self.cf.CFNumberGetTypeID():
                raise BokkioActionError('Numeric AX values require a verified field edit; a string setter would change their native type')
            key=self._string('AXValue');text=self._string(value)
            try:error=self.ax.AXUIElementSetAttributeValue(element,key,text)
            finally:self.cf.CFRelease(key);self.cf.CFRelease(text)
            source='AXUIElementSetAttributeValue.AXValue'
        elif action=='focus':
            key=self._string('AXFocused');truth=c.c_void_p.in_dll(self.cf,'kCFBooleanTrue').value
            try:error=self.ax.AXUIElementSetAttributeValue(element,key,truth)
            finally:self.cf.CFRelease(key)
            source='AXUIElementSetAttributeValue.AXFocused'
        elif action=='select' and node['platform_data'].get('mac_selection_source')=='AXSelected_then_combo_confirm':
            key=self._string('AXSelected')
            truth=c.c_void_p.in_dll(self.cf,'kCFBooleanTrue').value
            try:error=self.ax.AXUIElementSetAttributeValue(element,key,truth)
            finally:self.cf.CFRelease(key)
            if error:raise BokkioCompletionUnknown(f'Mac AXSelected returned {error}; completion requires fresh observation')
            owner=element
            for _ in range(16):
                owner=self._attr(owner,'AXParent')
                if not owner:raise BokkioCompletionUnknown('Native option selection lost its owning combo')
                if self._text(self._attr(owner,'AXRole'))=='AXComboBox':break
            else:raise BokkioCompletionUnknown('Native option selection has no owning combo')
            if 'AXConfirm' not in self._actions(owner):raise BokkioCompletionUnknown('Native option owner cannot confirm selection')
            key=self._string('AXConfirm')
            try:error=self.ax.AXUIElementPerformAction(owner,key)
            finally:self.cf.CFRelease(key)
            source='AXSelected_then_owning_combo_AXConfirm'
        elif action=='select_text':
            # Actual selection stays in xa11y, which already supports ranges.
            raise BokkioActionError('Text selection dispatch uses the live xa11y object')
        else:
            source=('AXOpen' if action=='open' else
                    'AXPress' if action=='expand' and node['platform_data'].get('ax_role')=='AXPopUpButton' and 'AXPress' in actions else
                    'AXShowMenu' if action=='expand' else 'AXConfirm' if action=='submit' or 'AXPress' not in actions else 'AXPress')
            key=self._string(source)
            try:error=self.ax.AXUIElementPerformAction(element,key)
            finally:self.cf.CFRelease(key)
        if error:
            # No second action is attempted after a native call.
            raise BokkioCompletionUnknown(f'Mac {source} returned {error}; completion requires fresh observation')
        return {'action_source':source,'native_identity':identity}
