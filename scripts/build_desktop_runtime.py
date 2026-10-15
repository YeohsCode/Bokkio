"""Stage a relocatable managed Python plus installed platform dependencies."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,sysconfig
from pathlib import Path

def stage(destination, sdk_python=None):
    destination=Path(destination).resolve()
    if destination.exists():shutil.rmtree(destination)
    destination.mkdir(parents=True)
    base=Path(sys.base_prefix).resolve();python=destination/'python'
    shutil.copytree(base,python,symlinks=False,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    relative=Path(sysconfig.get_path('purelib')).relative_to(sys.prefix)
    packages=python/relative;packages.mkdir(parents=True,exist_ok=True)
    shutil.copytree(sysconfig.get_path('purelib'),packages,dirs_exist_ok=True,symlinks=False,ignore=shutil.ignore_patterns('__pycache__','*.pyc','pytest*','_pytest*','bokkio*','__editable*'))
    shutil.copytree(Path(__file__).resolve().parents[1]/'src'/'bokkio',packages/'bokkio',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    if sdk_python:
        donor=Path(subprocess.check_output([str(sdk_python),'-c','import sysconfig;print(sysconfig.get_path("purelib"))'],text=True).strip())
        for p in donor.glob('deepseek*'):
            if p.is_dir():shutil.copytree(p,packages/p.name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Remove editable install roots that refer to the developer's checkout.
    for p in packages.glob('*bokkio*.pth'):p.unlink()
    if sys.platform=='darwin':
        from bokkio.app_launch import native_helper
        for name in ('macos_record','macos_input'):
            target=packages/'bokkio'/'native'/name;shutil.copy2(native_helper(name),target);target.chmod(0o755)
        from bokkio.macos_capture import _helper
        target=packages/'bokkio'/'native'/'macos_capture';shutil.copy2(_helper(),target);target.chmod(0o755)
    executable=python/('python.exe' if os.name=='nt' else 'bin/python3')
    subprocess.run([str(executable),'-c','import bokkio.runtime,xa11y;print("Bundled Runtime imports passed")'],check=True)
    (destination/'manifest.json').write_text(json.dumps({'python':str(executable.relative_to(destination)),'platform':sys.platform,'version':sys.version.split()[0]}))
    return destination
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='desktop/runtime');p.add_argument('--sdk-python');a=p.parse_args();print(stage(a.output,a.sdk_python))
