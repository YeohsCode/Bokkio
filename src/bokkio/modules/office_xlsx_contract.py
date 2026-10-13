"""Metadata-only contract for the optional Office XLSX module."""
VERSION = "1.0.0"
MODULE = "office.xlsx"
IMPLEMENTATION = "openpyxl.file"
BASE = {
    "path": {"type": "string"}, "sheet": {"type": "string"},
    "expected_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
}
CONTRACTS = {}
for name, description, extra, write in [
    ("read_range", "Read bounded literal cell values from a saved XLSX file.", {"range": {"type": "string"}}, False),
    ("update_cells", "Write literal cells into a NEW XLSX file; preserve and hash-check the source.",
     {"output_path": {"type": "string"}, "cells": {"type": "object"}}, True),
    ("verify_cells", "Reopen a saved XLSX and compare exact expected literal cell values.", {"cells": {"type": "object"}}, False),
]:
    properties = {**BASE, **extra}
    cid = "xlsx." + name
    CONTRACTS[cid] = {
        "id": cid, "version": VERSION, "module_id": MODULE, "module_version": VERSION,
        "description": description, "side_effect": "new_file" if write else "read",
        "input_schema": {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False},
        "output_schema": {"type": "object", "required": ["status", "capability", "implementation", "evidence"],
                          "properties": {"status": {"enum": ["completed", "verified", "completion_unknown"]},
                                         "capability": {"type": "object"}, "implementation": {"type": "object"}, "evidence": {"type": "object"}}},
        "preconditions": ["module explicitly granted", "live session and granted paths", "source SHA256 matches", "saved ordinary .xlsx"],
        "expected_effects": ["new file with requested literal values"] if write else ["no file mutation"],
        "verification": "reopen and compare cells; hash source and output" if write else "source hash before and after reading; exact cell comparison for verify",
        "recovery": {"automatic_retry": False, "unknown_completion": "inspect job and artifact evidence; do not switch implementation or redispatch"},
        "implementations": [{"id": IMPLEMENTATION, "version": VERSION, "platforms": ["Darwin", "Windows", "Linux"],
                             "dependency": "openpyxl>=3.1.5,<4", "transport": "code job",
                             "grants": ["modules", "paths", "write", "trusted_host", "exact approval when required"],
                             "limits": ["1000 cells", "10 MiB source / 50 MiB expanded ZIP", "literal values only", "no formula recalculation",
                                        "does not edit an open application", "updates reject formulas, macros, drawings, tables, links and protected sheets", "output must not exist"]}],
    }

