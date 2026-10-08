"""Prepare, run and independently grade a pinned WindowsWorld Office subset.

Only the setup verb writes Office input files. Run uses DesktopAgent, Planner,
Jev and native app actions. It never substitutes file edits for app execution.
"""
import argparse
import json
from pathlib import Path

from bokkio.office_benchmark import prepare,evaluate
from bokkio.office_runner import run

parser=argparse.ArgumentParser(description=__doc__)
sub=parser.add_subparsers(dest='command',required=True)
setup=sub.add_parser('prepare');setup.add_argument('--bundle',type=Path,default=Path('fixtures/windowsworld-office'));setup.add_argument('--workspace',type=Path,required=True)
execute=sub.add_parser('run');execute.add_argument('--workspace',type=Path,required=True)
grade=sub.add_parser('evaluate');grade.add_argument('--task',required=True);grade.add_argument('--artifact',type=Path,required=True)
vlm=sub.add_parser('judge');vlm.add_argument('--bundle',type=Path,default=Path('fixtures/windowsworld-office'));vlm.add_argument('--task',required=True);vlm.add_argument('--actions',type=Path,required=True);vlm.add_argument('--screenshot',action='append',required=True)
args=parser.parse_args()
if args.command=='prepare':result=prepare(args.bundle,args.workspace)
elif args.command=='run':result=run(args.workspace)
elif args.command=='evaluate':result=evaluate(args.task,args.artifact)
else:
    from bokkio.office_judge import judge
    result=judge(args.bundle,args.task,json.loads(args.actions.read_text()),args.screenshot)
print(json.dumps(result,ensure_ascii=False,indent=2))
if args.command=='run':raise SystemExit(0 if result['status']=='completed' else 1)
if args.command=='evaluate':raise SystemExit(0 if result['passed'] else 1)
