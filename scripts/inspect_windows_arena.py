"""Read pinned WAA task metadata without importing or executing upstream code."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


ROOT = "src/win-arena-container/client/evaluation_examples_windows"


def inspect(checkout, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Use a full lowercase Git commit SHA")

    def git(*args):
        return subprocess.run(["git", "-C", str(checkout), *args], check=True, capture_output=True).stdout

    resolved = git("rev-parse", "--verify", revision + "^{commit}").decode().strip()
    if resolved != revision: raise ValueError("Revision must resolve to the pinned commit")
    paths = sorted(p.decode() for p in git("ls-tree", "-rz", "--name-only", revision, "--", ROOT).split(b"\0") if p)
    tasks, splits = [], {}

    def types(value):
        if value is None: return []
        return [entry.get("type") for entry in (value if isinstance(value, list) else [value]) if isinstance(entry, dict)]

    for path in paths:
        relative = PurePosixPath(path).relative_to(ROOT)
        if relative.suffix != ".json": continue
        is_task = len(relative.parts) == 3 and relative.parts[0] == "examples"
        is_split = len(relative.parts) == 1 and relative.name.startswith("test_")
        if not (is_task or is_split): continue
        raw = git("show", revision + ":" + path)
        data = json.loads(raw)
        if is_split:
            if not isinstance(data, dict): raise ValueError("Invalid task split: " + path)
            splits[relative.name] = {"domains": {k: len(v) for k, v in data.items()},
                                    "task_count": sum(len(v) for v in data.values())}
            continue
        if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not isinstance(data.get("evaluator"), dict):
            raise ValueError("Invalid task metadata: " + path)
        evaluator = data["evaluator"]
        tasks.append({"domain": relative.parts[1], "id": data["id"], "path": path,
                      "sha256": hashlib.sha256(raw).hexdigest(), "snapshot": data.get("snapshot"),
                      "setup_types": types(data.get("config")), "postconfig_types": types(evaluator.get("postconfig")),
                      "metric_functions": evaluator.get("func"), "result_types": types(evaluator.get("result")),
                      "expected_types": types(evaluator.get("expected")), "execution_status": "not_run"})
    if not tasks: raise ValueError("No Windows Arena task files at the pinned revision")
    identities = defaultdict(list)
    for task in tasks: identities[(task["domain"], task["id"])].append(task["path"])
    duplicates = [{"domain": domain, "id": task_id, "paths": paths}
                  for (domain, task_id), paths in identities.items() if len(paths) > 1]
    # The pinned upstream has duplicate declared IDs. Preserve every file and
    # its hash; runners must use path + revision as their catalog identity.
    return {"benchmark": "WindowsAgentArena", "repository": "https://github.com/microsoft/WindowsAgentArena",
            "revision": revision, "task_file_count": len(tasks),
            "unique_declared_identity_count": len(identities), "duplicate_declared_ids": duplicates,
            "domains": dict(sorted(Counter(t["domain"] for t in tasks).items())),
            "splits": splits, "tasks": tasks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = inspect(args.checkout, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: catalog[k] for k in ("revision", "task_file_count", "domains", "splits")}))
