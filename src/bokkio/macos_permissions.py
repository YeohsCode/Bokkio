"""Describe the calling runtime's Accessibility status and exact install paths."""
from __future__ import annotations
import ctypes
import os
from pathlib import Path
import shlex
import sys

SETTINGS_URL='x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'

def permission_paths():
    executable=str(Path(sys.executable).resolve())
    application=os.environ.get('BOKKIO_DESKTOP_APP_PATH','')
    target=application or executable
    return {'application_path':application,'runtime_executable':executable,'authorization_path':target,'settings_url':SETTINGS_URL,'commands':['open -R '+shlex.quote(target),'open '+shlex.quote(SETTINGS_URL)]}

def permission_status():
    value=permission_paths()
    if sys.platform!='darwin':return {**value,'accessibility':True}
    ax=ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    ax.AXIsProcessTrusted.argtypes=[];ax.AXIsProcessTrusted.restype=ctypes.c_bool
    return {**value,'accessibility':bool(ax.AXIsProcessTrusted())}

def permission_message():
    value=permission_paths();target=value['authorization_path']
    return ('macOS Accessibility permission is required. '
            f'请在系统设置 > 隐私与安全性 > 辅助功能中添加并启用：{target}。 '
            f'实际执行文件：{value["runtime_executable"]}。 '
            f'辅助命令：open -R {shlex.quote(target)}；open {shlex.quote(SETTINGS_URL)}。 '
            '授权后在 Bokkio 配置页刷新状态并重试；仅在状态仍未更新时重新打开 Bokkio。')
