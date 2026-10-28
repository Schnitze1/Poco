#!/usr/bin/env python3
"""Check only the six required metric responses, alongside other evidence files."""

import json
from pathlib import Path
import sys

METRICS = ("cpu_total_time", "memory_utilization", "tmp_used", "rx_bytes", "tx_bytes", "http-latency")


def missing_metrics(folder):
    missing = []
    for metric in METRICS:
        try:
            report = json.loads((Path(folder) / f"{metric}.json").read_text())
            points = report.get("Datapoints") if isinstance(report, dict) else None
            if not isinstance(points, list) or not points:
                missing.append(metric)
        except (OSError, ValueError):
            missing.append(metric)
    return missing


if __name__ == "__main__":
    missing = missing_metrics(sys.argv[1])
    if missing:
        print("Waiting for metric samples: " + ", ".join(missing))
    sys.exit(1 if missing else 0)
