"""Build a source + tested wheel delivery bundle without private state or credentials."""
from pathlib import Path
import hashlib
import json
import zipfile


def build():
    project = Path(__file__).resolve().parents[1]
    dist = project / "dist"
    dist.mkdir(exist_ok=True)
    files = [project / name for name in ("pyproject.toml", "uv.lock", "MANIFEST.in")]
    files += sorted((project / "src/bokkio").glob("*.py"))
    files += sorted((project / "src/bokkio/native").glob("*.swift"))
    files += sorted((project / "examples").glob("*.py")) + sorted((project / "examples").glob("*.json"))
    files += [project / "scripts" / name for name in ("install_runtime.sh", "install_runtime.ps1", "verify_runtime.py", "verify_runtime_visual.py")]
    files += [project / "tests" / name for name in ("test_runtime.py", "test_runtime_transports.py")]
    files += [project / "docs" / name for name in ("RUNTIME-GUIDE.md", "RUNTIME-DELIVERY.md", "PLAN-REPOSITIONING.md")]
    files += sorted((project / "docs/progress").glob("*.md")) + sorted((project / "docs/progress").glob("*.json"))
    files += sorted((project / "docs/evidence/2026-10-11-runtime").glob("*.json"))
    files += [project / "docs/evidence/2026-10-11-runtime" / name for name in ("README.md", "SHA256SUMS")]
    files += [project / "fixtures/cocoa-visual/main.swift", project / "fixtures/windows-visual/Program.cs", project / "fixtures/windows-visual/windows-visual.csproj"]
    releases = [dist / name for name in ("bokkio-0.2.0-py3-none-any.whl", "bokkio-0.2.0.tar.gz", "runtime-requirements.txt", "runtime-dependency-inventory.json")]
    for file in files + releases:
        if not file.is_file():
            raise FileNotFoundError(file)
    prefix = "bokkio-runtime-0.2.0"
    archive = dist / (prefix + "-candidate.zip")
    sums = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for file in files + releases:
            target = "packages/" + file.name if file in releases else file.relative_to(project).as_posix()
            output.write(file, prefix + "/" + target)
            sums.append(hashlib.sha256(file.read_bytes()).hexdigest() + "  " + target)
        output.writestr(prefix + "/SHA256SUMS", "\n".join(sums) + "\n")
        output.writestr(prefix + "/README.md", """# Bokkio Runtime 0.2.0 工作候选版

Windows/macOS 的通用执行工具：MCP、CLI、Python SDK、原生/截图输入、生成代码、Browser、审批、操作审计与统计。

macOS 运行 `sh scripts/install_runtime.sh`；Windows 运行 `powershell -File scripts/install_runtime.ps1`。
这两条命令从锁定依赖安装，需要可用包源。先阅读 docs/RUNTIME-GUIDE.md，人工配置 examples/runtime-policy.json；默认拒绝资源访问。

packages/ 内含 wheel、源码归档、锁定 requirements 和本机依赖元数据清单；不是离线依赖镜像。仓库回归 541 项，本包携带 22 项 Runtime 核心/transport 测试。

实际完成范围和待验收项见 docs/RUNTIME-DELIVERY.md。Windows 实机和客户业务样本尚待验收，本包不标为双平台已验收正式发行。
""")
    result = {"archive": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "files": len(files) + len(releases) + 2}
    (dist / "runtime-bundle.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(build()))
