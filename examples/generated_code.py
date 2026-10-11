"""Executed by code.run: delegated SDK calls + data processing + artifact check."""
from pathlib import Path
import csv

from bokkio.sdk import Client

client = Client.from_environment()
target = Path.cwd() / "generated-report.csv"
with target.open("w", encoding="utf-8", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(["name", "value"])
    for index in range(3):
        writer.writerow([f"item-{index}", index * 10])
result = client.call("evidence.check", {"path": str(target), "csv_rows": 3, "csv_columns": ["name", "value"]})
assert result["result"]["passed"], result
print(result["result"]["artifact"]["artifact_id"])
