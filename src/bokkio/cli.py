from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .model import BokkioError, BokkioLookupError
from .xa11y_backend import ACTION_METHODS, Xa11yBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bokkio",
        description="Native desktop accessibility inspector, actions and decisions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    apps = subparsers.add_parser("apps", help="List visible applications")
    apps.add_argument("--json", action="store_true")

    windows = subparsers.add_parser("windows", help="List application windows")
    windows.add_argument("--app", required=True)
    windows.add_argument("--json", action="store_true")

    snapshot = subparsers.add_parser("snapshot", help="Capture a native accessibility tree")
    snapshot.add_argument("--app", required=True)
    snapshot.add_argument("--window")
    output = snapshot.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument("--tree", action="store_true")

    find = subparsers.add_parser("find", help="Find elements by role and optional name")
    find.add_argument("--app", required=True)
    find.add_argument("--role", required=True)
    find.add_argument("--name")
    find.add_argument("--json", action="store_true")

    get = subparsers.add_parser("get", help="Read one element by ref")
    get.add_argument("ref")
    get.add_argument("--app")
    get.add_argument("--json", action="store_true")

    act = subparsers.add_parser("act", help="Perform a semantic action on an AX element")
    act.add_argument("--app", required=True)
    act.add_argument("--action", required=True, choices=sorted(ACTION_METHODS))
    act.add_argument("--ref")
    act.add_argument("--role")
    act.add_argument("--name")
    act.add_argument("--parent")
    act.add_argument("--value")
    act.add_argument("--direction", choices=["up", "down", "left", "right"])
    act.add_argument("--amount", type=float, help="Scroll fraction of the full range (0 < amount <= 1; default 0.25)")
    act.add_argument("--expect-value", help="Expected text after a type action")
    decide = subparsers.add_parser("decide", help="Ask Jev for one native desktop decision")
    decide.add_argument("--app", required=True)
    decide.add_argument("--goal", required=True)
    decide.add_argument("--window", help="Restrict decisions and snapshot validation to one native window")
    decide.add_argument("--allow-value", action="append", default=[], help="Literal text the decision may choose; repeat for multiple values")
    decide.add_argument("--confidence", type=float, default=0.7)
    decide.add_argument("--execute", action="store_true", help="Execute one accepted decision after validating a fresh snapshot")
    run = subparsers.add_parser("run", help="Plan and execute a bounded native desktop task")
    run.add_argument("--goal", required=True)
    run.add_argument("--allow-app", action="append", required=True, help="Authorized native app name or PID; repeat for cross-app tasks")
    run.add_argument("--trace", required=True, help="JSON trace and pause/resume checkpoint")
    run.add_argument("--max-actions", type=int, default=20)
    run.add_argument("--max-replans", type=int, default=1)
    run.add_argument("--max-phases", type=int, default=4)
    run.add_argument("--require-file", action="append", default=[], help="Deliverable that must exist before completion; repeat for multiple files")
    run.add_argument("--require-source", action="append", default=[], help="Source that must be opened by full path in a Windows native Open dialog before editor output")
    run.add_argument("--planner-model")
    run.add_argument("--plan-only", action="store_true")
    run.add_argument("--control-file", help='JSON file containing {"action":"pause"} or {"action":"cancel"}')
    run.add_argument("--resume", help="Resume a JSON checkpoint with the same goal and app allowlist")
    run.add_argument("--amend-reason", help="Explicit reason for a changed goal at a paused/completed checkpoint; keep the app allowlist")
    return parser


def render_tree(node: dict[str, Any], indent: int = 0) -> str:
    title = node.get("name") or node.get("value")
    line = "  " * indent + f"{node['role']}[{node['ref'][:8]}]"
    if title:
        line += f" {title!r}"
    lines = [line]
    for child in node.get("children") or []:
        if isinstance(child, dict):
            lines.append(render_tree(child, indent + 1))
    return "\n".join(lines)


def execute(args: argparse.Namespace, backend: Xa11yBackend) -> Any:
    if args.command == "apps":
        return backend.apps()
    if args.command == "windows":
        return backend.windows(args.app)
    if args.command == "snapshot":
        return backend.snapshot(args.app, args.window)
    if args.command == "find":
        return backend.find(args.app, args.role, args.name)
    if args.command == "get":
        return backend.get(args.ref, args.app)
    if args.command == "act":
        return backend.perform(
            args.app, args.action, ref=args.ref, role=args.role, name=args.name,
            parent=args.parent, value=args.value,
            direction=args.direction, amount=args.amount, expected_value=args.expect_value,
        )
    if args.command == "decide":
        from .decision import decide, execute_decision
        from .jev import JevProvider
        provider = JevProvider()
        snapshot = backend.snapshot(args.app, args.window)
        decision, response = decide(provider, args.goal, snapshot, args.allow_value, args.confidence)
        result = {"decision": decision.as_dict(), "model": response.get("model"),
                  "usage": response.get("usage"), "elapsed_seconds": response.get("elapsed_seconds"),
                  "executed": args.execute}
        if args.execute:
            result["result"] = execute_decision(backend, args.app, decision, args.confidence)
        return result
    if args.command == "run":
        from .agent import DesktopAgent, file_control
        from .planner import OpenRouterPlanner
        from .jev import JevProvider
        from pathlib import Path
        required = sorted({str(Path(p).expanduser().resolve()) for p in args.require_file})
        sources = sorted({str(Path(p).expanduser().resolve()) for p in args.require_source})
        goal = args.goal
        if sources:
            goal += '\nRequired native source paths: ' + json.dumps(sources, ensure_ascii=False)
        verifier = None
        if required:
            goal += '\nRequired deliverable files: ' + json.dumps(required, ensure_ascii=False)
            def verifier(trace):
                import hashlib
                files = []
                for p in required:
                    file = Path(p)
                    info = {'path':p, 'exists':file.is_file()}
                    if info['exists']:
                        digest = hashlib.sha256()
                        with file.open('rb') as stream:
                            for chunk in iter(lambda:stream.read(1024*1024), b''):
                                digest.update(chunk)
                        info.update(bytes=file.stat().st_size, sha256=digest.hexdigest())
                    files.append(info)
                return all(f['exists'] for f in files), {'required_files':files}
        agent = DesktopAgent(backend, OpenRouterPlanner(model=args.planner_model), None if args.plan_only else JevProvider(),
                             max_actions=args.max_actions, max_replans=args.max_replans, max_phases=args.max_phases, control=file_control(args.control_file), final_verifier=verifier, required_sources=sources)
        return agent.run(goal, args.allow_app, args.trace, resume=args.resume, plan_only=args.plan_only,
                         amend_reason=args.amend_reason)
    raise BokkioError(f"Unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = execute(args, Xa11yBackend())
        if args.command == "run":
            from pathlib import Path
            summary = {k: result[k] for k in ("status", "actions", "replans", "completed_steps")}
            summary["trace"] = str(Path(args.trace).resolve())
            summary["reason"] = result["events"][-1].get("reason")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        elif args.command == "snapshot" and not args.json:
            print("\n\n".join(render_tree(tree) for tree in result["windows"]))
        elif getattr(args, "json", False) or args.command in {"snapshot", "find", "get", "act", "decide", "run"}:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for item in result:
                if args.command == "apps":
                    foreground = " foreground" if item["is_foreground"] else ""
                    print(f"{item['pid'] or '-'}\t{item['name']}{foreground}")
                else:
                    bounds = item.get("bounds") or {}
                    rectangle = (
                        f" {bounds['x']},{bounds['y']} {bounds['width']}x{bounds['height']}"
                        if bounds
                        else ""
                    )
                    print(f"{item['ref']}\t{item['role']}\t{item['name'] or '-'}{rectangle}")
        return 1 if args.command == "run" and result["status"] in {"blocked", "failed", "cancelled"} else 0
    except BokkioLookupError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    except BokkioError as error:
        print(f"bokkio: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
