import json
from pathlib import Path
import tempfile
import unittest

from check_monitoring import METRICS, missing_metrics


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        for metric in METRICS:
            (self.folder / f"{metric}.json").write_text(json.dumps({
                "Datapoints": [{"Timestamp": "2026-10-28T03:00:00Z", "Maximum": 1}]}))

    def test_alias_configuration_and_dashboard_evidence_do_not_block_valid_metrics(self):
        for name in ("live-alias", "live-config", "dashboard", "dashboard-result"):
            (self.folder / f"{name}.json").write_text('{"evidence":true}')
        self.assertEqual(missing_metrics(self.folder), [])

    def test_each_required_metric_must_contain_samples(self):
        for metric in METRICS:
            path = self.folder / f"{metric}.json"
            original = path.read_text()
            path.write_text('{"Datapoints":[]}')
            self.assertEqual(missing_metrics(self.folder), [metric])
            path.write_text(original)

    def test_missing_invalid_and_unexpected_payloads_are_not_accepted(self):
        for payload in (None, '{', '[]', '{}', '{"Datapoints":{}}'):
            path = self.folder / 'cpu_total_time.json'
            if payload is None:
                path.unlink()
            else:
                path.write_text(payload)
            self.assertEqual(missing_metrics(self.folder), ['cpu_total_time'])


if __name__ == '__main__':
    unittest.main()
