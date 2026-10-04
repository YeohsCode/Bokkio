"""Build the disposable Cocoa fixture; launch the resulting app separately."""
from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import subprocess
import tempfile


def build(output: Path, source: Path | None = None, name: str = "BokkioTest") -> Path:
    source = source or Path(__file__).resolve().parents[1] / "vendor/xa11y/test-apps/cocoa/main.swift"
    if not source.is_file():
        raise SystemExit(f"Missing vendored Cocoa fixture source: {source}")
    contents = output / "Contents"
    binary = contents / "MacOS" / name
    binary.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["swiftc", "-o", str(binary), "-framework", "Cocoa", str(source)], check=True)
    with (contents / "Info.plist").open("wb") as file:
        plistlib.dump({
            "CFBundleIdentifier": f"local.bokkio.{name.lower()}",
            "CFBundleName": name,
            "CFBundleExecutable": name,
            "CFBundlePackageType": "APPL",
            "NSHighResolutionCapable": True,
        }, file)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(tempfile.gettempdir()) / "BokkioTest.app")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--name", default="BokkioTest")
    args = parser.parse_args()
    print(build(args.output.resolve(), args.source, args.name))
