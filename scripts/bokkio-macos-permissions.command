#!/bin/zsh
set -eu
bokkio_app_path=${1:-"$HOME/Applications/Bokkio.app"}
if [[ $# -eq 0 && ! -d "$bokkio_app_path" && -d /Applications/Bokkio.app ]]; then
  bokkio_app_path=/Applications/Bokkio.app
fi
if [[ ! -f "$bokkio_app_path/Contents/MacOS/Bokkio" ]]; then
  print -u2 -r -- "找不到 Bokkio 应用：$bokkio_app_path"
  print -u2 -r -- '用法：bokkio-macos-permissions.command "/完整路径/Bokkio.app"'
  exit 1
fi
print -r -- "需要在辅助功能列表中添加并启用的应用：$bokkio_app_path"
print -r -- "内置执行文件：$bokkio_app_path/Contents/Resources/runtime/python/bin/python3"
/usr/bin/open -R "$bokkio_app_path"
/usr/bin/open 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
print -r -- '已打开设置并定位应用。启用开关并完成系统确认后，返回 Bokkio 查看权限状态。'
