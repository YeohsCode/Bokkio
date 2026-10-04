"""Check both scroll axes in the disposable BokkioInteractions Cocoa app."""
import argparse
import json
from pathlib import Path
from bokkio.scroll import axis
from bokkio.xa11y_backend import Xa11yBackend


def verify(output):
    b = Xa11yBackend()
    trace = []
    for coordinate, forward, backward in [("x", "right", "left"), ("y", "down", "up")]:
        bars = [n for n in b.find("BokkioInteractions", "scroll_bar") if axis(n) == coordinate]
        assert len(bars) == 1
        ref = bars[0]["ref"]
        b.perform("BokkioInteractions", "scroll", ref=ref, direction=backward, amount=1)
        for _ in range(3):
            for direction in (forward, backward):
                result = b.perform("BokkioInteractions", "scroll", ref=ref, direction=direction, amount=0.25)
                trace.append(result)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(trace, indent=2), encoding="utf-8")
                assert result["verification"] == "confirmed", result["scroll"]
    print(json.dumps({"passed": True, "scroll_actions": len(trace)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
