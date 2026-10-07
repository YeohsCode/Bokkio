"""Read-only checks for Office files saved by the macOS Computer Use pilot.

This verifier never edits documents or substitutes file generation for native
application interaction. Expected values come from a fixed synthetic order input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


S = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
W = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
A = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
FORMULAS = {"G3": 'COUNTIFS(B3:B7,"East",C3:C7,"Complete")',
            "G4": 'SUMIFS(D3:D7,B3:B7,"East",C3:C7,"Complete")'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sheet(path):
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(item.itertext()) for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", S)]
        values, formulas = {}, {}
        for cell in ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall(".//s:c", S):
            ref = cell.attrib["r"]
            value = cell.findtext("s:v", namespaces=S)
            if cell.get("t") == "s":
                value = strings[int(value)]
            elif cell.get("t") == "inlineStr":
                value = "".join(cell.find("s:is", S).itertext())
            values[ref] = value
            formula = cell.findtext("s:f", namespaces=S)
            if formula is not None:
                formulas[ref] = formula
        return values, formulas


def verify(directory, source, baseline=None):
    with source.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream, delimiter="\t"))
    if len(records) != 5 or [r["Order"] for r in records] != ["1001", "1002", "1003", "1004", "1005"]:
        raise ValueError("Use the fixed five-order synthetic input")
    artifacts = []
    for version in ("v1", "v2"):
        expected = [dict(r) for r in records]
        if version == "v2":
            expected[3]["Amount"] = "250"
        eligible = [r for r in expected if r["Region"] == "East" and r["Status"] == "Complete"]
        count, total = len(eligible), sum(int(r["Amount"]) for r in eligible)
        folder = directory / version
        book = folder / "orders.xlsx"
        values, formulas = sheet(book)
        checks = {"input_rows": all(values.get(f"{column}{row}") == record[field]
                                    for row, record in enumerate(expected, 3)
                                    for column, field in zip("ABCD", ("Order", "Region", "Status", "Amount"))),
                  "headers": [values.get(c + "2") for c in "ABCD"] == ["Order", "Region", "Status", "Amount"],
                  "formula_contract": all(formulas.get(ref) == formula for ref, formula in FORMULAS.items()),
                  "cached_count": values.get("G3") == str(count), "cached_total": values.get("G4") == str(total)}
        artifacts.append({"version": version, "file": book.name, "bytes": book.stat().st_size, "sha256": sha256(book),
                          "expected_count": count, "expected_total": total, "checks": checks, "passed": all(checks.values())})
        doc = folder / "weekly-report.docx"
        with zipfile.ZipFile(doc) as archive:
            paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", W))
                          for p in ET.fromstring(archive.read("word/document.xml")).findall(".//w:body/w:p", W)]
        expected_paragraphs = [f"Bokkio weekly report {version}", "Region: East", "Status: Complete",
                               f"Order count: {count}", f"Total amount: {total}"]
        if version == "v2":
            expected_paragraphs.append("Revision: order 1004 amount changed from 200 to 250.")
        expected_paragraphs += ["Source: orders.xlsx", "Synthetic computer-use acceptance data."]
        artifacts.append({"version": version, "file": doc.name, "bytes": doc.stat().st_size, "sha256": sha256(doc),
                          "paragraphs": paragraphs, "checks": {"exact_report": paragraphs == expected_paragraphs},
                          "passed": paragraphs == expected_paragraphs})
        deck = folder / "weekly-summary.pptx"
        with zipfile.ZipFile(deck) as archive:
            names = [n for n in archive.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml") and "/_rels/" not in n]
            text = [t.text or "" for t in ET.fromstring(archive.read("ppt/slides/slide1.xml")).findall(".//a:t", A)]
        expected_text = [f"Bokkio weekly summary {version}", "East / Complete", f"Order count: {count}", f"Total amount: {total}"]
        if version == "v2":
            expected_text.append("Revision: order 1004 +50")
        expected_text.append("Source: orders.xlsx")
        checks = {"one_slide": len(names) == 1, "exact_summary": text == expected_text}
        artifacts.append({"version": version, "file": deck.name, "bytes": deck.stat().st_size, "sha256": sha256(deck),
                          "text": text, "checks": checks, "passed": all(checks.values())})
    preservation = {name: sha256(directory / "v1" / name) == value for name, value in (baseline or {}).items()}
    return {"scope": "macos_office_interactive_cua_pilot", "source_sha256": sha256(source), "artifacts": artifacts,
            "v1_preservation": preservation, "passed": all(a["passed"] for a in artifacts) and all(preservation.values()),
            "bokkio_agent_end_to_end": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "fixtures/mac-office/orders.tsv")
    parser.add_argument("--baseline-hashes", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline_hashes.read_text()) if args.baseline_hashes else None
    report = verify(args.artifacts, args.source, baseline)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "artifacts": len(report["artifacts"]), "v1_preservation": report["v1_preservation"]}))
    raise SystemExit(0 if report["passed"] else 1)
