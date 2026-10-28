"""Offline release/recovery tests. No AWS credentials or application data required."""

import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lambda_release import API, AwsCli, AwsError, FUNCTIONS, INSIGHTS, Release, ReleaseError, fingerprint


class FakeAws:
    def __init__(self, stage="test"):
        self.stage, self.function = stage, FUNCTIONS[stage]
        self.latest = {
            "FunctionName": self.function,
            "FunctionArn": f"arn:aws:lambda:us-east-1:123456789012:function:{self.function}",
            "Version": "$LATEST", "CodeSha256": "original-hash", "RevisionId": "r0",
            "Runtime": "provided.al2023", "Handler": "bootstrap", "Architectures": ["x86_64"],
            "State": "Active", "LastUpdateStatus": "Successful",
            "Role": "arn:aws:iam::123456789012:role/LabRole", "Description": "Original description",
            "Environment": {"Variables": {"ENVIRONMENT": stage, "DYNAMODB_TABLE": "table", "S3_BUCKET": "bucket",
                                            "DO_NOT_EXPORT": "private-configuration-value"}},
            "Layers": [{"Arn": "arn:aws:lambda:us-east-1:123456789012:layer:other:1"}],
            "MemorySize": 512, "Timeout": 30,
        }
        self.versions, self.live, self.policy = {}, None, None
        self.target, self.revision = self.function, 0
        self.calls, self.denied, self.fail_after_activation = [], None, False

    def bump(self):
        self.revision += 1
        return f"r{self.revision}"

    def wait(self, function):
        assert function == self.function

    def guard(self, expected, actual):
        if expected != actual:
            raise AwsError("update", "PreconditionFailedException")

    def call(self, service, operation, **params):
        self.calls.append((service, operation, params))
        if operation == self.denied:
            raise AwsError(operation, "AccessDeniedException")
        if "function_name" in params:
            assert params["function_name"] == self.function
        if service == "apigateway":
            assert params["rest_api_id"] == API
            if operation == "get-stage":
                return {"variables": {"lambdaName": self.target}}
            if operation == "update-stage":
                assert params["stage_name"] == self.stage
                self.target = params["patch_operations"][0]["value"]
                return {}
            if operation == "get-resources":
                return {"items": [{"id": "proxy", "resourceMethods": {"ANY": {}}}]}
            if operation == "get-integration":
                return {"type": "AWS_PROXY", "uri": "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/"
                        "arn:aws:lambda:us-east-1:123456789012:function:${stageVariables.lambdaName}/invocations"}
        if operation == "get-function-configuration":
            version = params.get("qualifier")
            if version == "live":
                version = self.live["FunctionVersion"]
            return copy.deepcopy(self.versions[version] if version else self.latest)
        if operation == "list-versions-by-function":
            return {"Versions": [copy.deepcopy(self.latest), *copy.deepcopy(list(self.versions.values()))]}
        if operation == "publish-version":
            self.guard(params["revision_id"], self.latest["RevisionId"])
            assert params["code_sha256"] == self.latest["CodeSha256"]
            number = str(len(self.versions) + 1)
            self.versions[number] = {**copy.deepcopy(self.latest), "Version": number}
            self.latest["RevisionId"] = self.bump()
            return copy.deepcopy(self.versions[number])
        if operation == "get-alias":
            if self.live is None:
                raise AwsError(operation, "ResourceNotFoundException")
            return copy.deepcopy(self.live)
        if operation == "create-alias":
            assert self.live is None
            self.live = {"FunctionVersion": params["function_version"], "RevisionId": self.bump(),
                         "Description": params["description"]}
            return copy.deepcopy(self.live)
        if operation == "update-alias":
            self.guard(params["revision_id"], self.live["RevisionId"])
            self.live = {"FunctionVersion": params["function_version"], "RevisionId": self.bump(),
                         "Description": params["description"]}
            if self.fail_after_activation and params["description"].startswith("poco-"):
                self.fail_after_activation = False
                raise AwsError(operation, "RequestTimeout")
            return copy.deepcopy(self.live)
        if operation == "add-permission":
            if self.policy:
                raise AwsError(operation, "ResourceConflictException")
            self.policy = {"Statement": [{"Sid": params["statement_id"], "Effect": "Allow",
                "Action": params["action"], "Principal": {"Service": params["principal"]},
                "Resource": self.latest["FunctionArn"] + ":live",
                "Condition": {"ArnLike": {"AWS:SourceArn": params["source_arn"]},
                              "StringEquals": {"AWS:SourceAccount": params["source_account"]}}}]}
            self.live["RevisionId"] = self.bump()
            return {}
        if operation == "get-policy":
            return {"Policy": json.dumps(self.policy)}
        if operation == "update-function-configuration":
            self.guard(params["revision_id"], self.latest["RevisionId"])
            for key in ("description", "layers"):
                if key in params:
                    self.latest[key.title()] = ([{"Arn": a} for a in params[key]] if key == "layers" else params[key])
            self.latest["RevisionId"] = self.bump()
            return copy.deepcopy(self.latest)
        if operation == "update-function-code":
            self.guard(params["revision_id"], self.latest["RevisionId"])
            package = Path(params["zip_file"].removeprefix("fileb://"))
            self.latest["CodeSha256"] = base64.b64encode(hashlib.sha256(package.read_bytes()).digest()).decode()
            self.latest["RevisionId"] = self.bump()
            return copy.deepcopy(self.latest)
        if operation == "invoke":
            event = json.loads(Path(params["payload"].removeprefix("fileb://")).read_text())
            assert event["path"] == "/health" and event["httpMethod"] == "GET"
            Path(params["_output_file"]).write_text(json.dumps({"statusCode": 200,
                "body": json.dumps({"status": "ok", "env": self.stage})}))
            return {"ExecutedVersion": params["qualifier"]}
        raise AssertionError((service, operation, params))


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.aws = FakeAws()
        self.path = Path(self.directory.name, "state.json")
        self.health_calls = []
        self.release = Release("test", self.path, self.aws, self.health_calls.append)
        self.output = patch("sys.stdout", new_callable=io.StringIO)
        self.output.start()
        self.addCleanup(self.output.stop)

    def package(self):
        package = Path(self.directory.name, "bootstrap.zip")
        package.write_bytes(b"candidate binary package")
        return package

    def activate(self):
        self.release.prepare()
        self.release.deploy(self.package())

    def test_bootstrap_is_stage_scoped_and_keeps_baseline(self):
        original = fingerprint(self.aws.latest)
        self.release.prepare()
        self.assertEqual(self.aws.target, self.aws.function + ":live")
        self.assertEqual(fingerprint(self.aws.versions["1"]), original)
        statement = self.aws.policy["Statement"][0]
        self.assertIn(f"{API}/test/*/*", statement["Condition"]["ArnLike"]["AWS:SourceArn"])
        self.assertTrue(self.release.state["prepared"])

    def test_successful_deployment_and_recovery_keep_original_failure_visible(self):
        self.activate()
        self.assertEqual(self.aws.live["FunctionVersion"], "2")
        # A later API/browser acceptance failure invokes the separate recovery action.
        reloaded = Release("test", self.path, self.aws, self.health_calls.append)
        reloaded.recover()
        self.assertEqual(self.aws.live["FunctionVersion"], "1")
        self.assertNotEqual(self.aws.latest["CodeSha256"], self.aws.versions["1"]["CodeSha256"])
        self.assertTrue(reloaded.state["recovered"])

    def test_candidate_failure_before_activation_keeps_old_live(self):
        self.release.prepare()
        self.release.invoke = lambda version: (_ for _ in ()).throw(ReleaseError("runtime failed"))
        with self.assertRaisesRegex(ReleaseError, "runtime failed"):
            self.release.deploy(self.package())
        self.release.recover()
        self.assertEqual(self.aws.live["FunctionVersion"], "1")
        self.assertTrue(self.release.state["recovered"])

    def test_lost_activation_response_can_be_recovered_from_persisted_intent(self):
        self.release.prepare()
        self.aws.fail_after_activation = True
        with self.assertRaises(AwsError):
            self.release.deploy(self.package())
        self.assertNotIn("activation_revision", self.release.state)
        Release("test", self.path, self.aws, self.health_calls.append).recover()
        self.assertEqual(self.aws.live["FunctionVersion"], "1")

    def test_external_alias_change_is_not_overwritten(self):
        self.activate()
        self.aws.live["RevisionId"] = "external-revision"
        with self.assertRaisesRegex(ReleaseError, "changed externally"):
            self.release.recover()
        self.assertEqual(self.aws.live["FunctionVersion"], "2")

    def test_activation_revision_conflict_keeps_external_alias(self):
        self.release.prepare()
        self.aws.live["RevisionId"] = "someone-else"
        with self.assertRaises(AwsError):
            self.release.deploy(self.package())
        self.assertEqual(self.aws.live["RevisionId"], "someone-else")

    def test_external_route_change_prevents_recovery_write(self):
        self.activate()
        self.aws.target = "unexpected-function"
        with self.assertRaisesRegex(ReleaseError, "Routing changed externally"):
            self.release.recover()
        self.assertEqual(self.aws.live["FunctionVersion"], "2")

    def test_expired_or_denied_credentials_do_not_report_recovery(self):
        self.activate()
        self.aws.denied = "update-alias"
        with self.assertRaises(AwsError):
            self.release.recover()
        self.assertFalse(self.release.state.get("recovered", False))

    def test_failed_restored_health_does_not_report_success(self):
        self.activate()
        self.release.health = lambda stage: (_ for _ in ()).throw(ReleaseError("unhealthy"))
        with self.assertRaisesRegex(ReleaseError, "unhealthy"):
            self.release.recover()
        self.assertFalse(self.release.state.get("recovered", False))

    def test_preparation_permission_failure_never_migrates_routing(self):
        self.aws.denied = "add-permission"
        with self.assertRaises(AwsError):
            self.release.prepare()
        self.release.recover()
        self.assertEqual(self.aws.target, self.aws.function)
        self.assertFalse(self.release.state["prepared"])

    def test_failed_migration_health_restores_legacy_route(self):
        def check(stage):
            if self.aws.target.endswith(":live"):
                raise ReleaseError("new routing unhealthy")
        self.release.health = check
        with self.assertRaisesRegex(ReleaseError, "unhealthy"):
            self.release.prepare()
        self.release.recover()
        self.assertEqual(self.aws.target, self.aws.function)

    def test_already_versioned_route_is_supported(self):
        self.release.prepare()
        second = Release("test", Path(self.directory.name, "second.json"), self.aws, self.health_calls.append)
        second.prepare()
        self.assertEqual(second.state["previous_version"], "1")
        self.assertEqual(len(self.aws.versions), 1)

    def test_conflicting_existing_permission_is_rejected(self):
        self.release.prepare()
        self.aws.policy["Statement"][0]["Condition"]["ArnLike"]["AWS:SourceArn"] = "*"
        second = Release("test", Path(self.directory.name, "second.json"), self.aws, self.health_calls.append)
        with self.assertRaisesRegex(ReleaseError, "permission does not match"):
            second.prepare()

    def test_weighted_alias_is_rejected(self):
        self.release.prepare()
        self.aws.live["RoutingConfig"] = {"AdditionalVersionWeights": {"2": 0.1}}
        with self.assertRaisesRegex(ReleaseError, "weighted"):
            self.release.recover()

    def test_unrelated_unused_alias_is_rejected(self):
        self.release.prepare()
        self.aws.target = self.aws.function
        self.aws.latest["Description"] = "external change"
        second = Release("test", Path(self.directory.name, "second.json"), self.aws, self.health_calls.append)
        with self.assertRaisesRegex(ReleaseError, "differs from the serving baseline"):
            second.prepare()

    def test_snapshot_detects_configuration_change_but_ignores_revision(self):
        snapshot = fingerprint(self.aws.latest)
        self.aws.latest["RevisionId"] = "other"
        self.assertEqual(fingerprint(self.aws.latest), snapshot)
        self.aws.latest["Environment"]["Variables"]["S3_BUCKET"] = "other-bucket"
        self.assertNotEqual(fingerprint(self.aws.latest), snapshot)

    def test_state_does_not_export_environment_values(self):
        self.activate()
        text = self.path.read_text()
        self.assertNotIn("private-configuration-value", text)
        self.assertNotIn("Environment", text)

    def test_production_insights_is_snapshotted_before_traffic_change(self):
        aws = FakeAws("prod")
        release = Release("prod", Path(self.directory.name, "prod.json"), aws, lambda stage: None)
        release.prepare()
        release.deploy(self.package())
        candidate = aws.versions[release.state["candidate_version"]]
        self.assertEqual([layer["Arn"] for layer in candidate["Layers"]],
                         ["arn:aws:lambda:us-east-1:123456789012:layer:other:1", INSIGHTS])
        release.recover()
        self.assertNotIn(INSIGHTS, [layer["Arn"] for layer in aws.versions["1"]["Layers"]])

    def test_demo_injects_failure_restores_version_routing_and_metadata(self):
        original = fingerprint(self.aws.latest)
        self.release.demonstrate()
        self.assertTrue(self.release.state["demo_failure_injected"])
        self.assertTrue(self.release.state["recovered"])
        self.assertTrue(self.release.state["demo_cleanup"])
        self.assertTrue(self.release.state["demo_passed"])
        self.assertEqual(self.aws.target, self.aws.function)
        self.assertEqual(self.aws.live["FunctionVersion"], "1")
        self.assertEqual(fingerprint(self.aws.latest), original)

    def test_demo_cannot_target_production(self):
        aws = FakeAws("prod")
        release = Release("prod", Path(self.directory.name, "prod.json"), aws)
        with self.assertRaisesRegex(ReleaseError, "restricted to Testing"):
            release.demonstrate()
        self.assertEqual(aws.calls, [])

    def test_demo_failure_before_activation_also_restores_original_metadata(self):
        original = fingerprint(self.aws.latest)
        self.release.invoke = lambda version: (_ for _ in ()).throw(ReleaseError("invoke failed"))
        with self.assertRaisesRegex(ReleaseError, "invoke failed"):
            self.release.demonstrate()
        self.assertEqual(self.aws.target, self.aws.function)
        self.assertEqual(fingerprint(self.aws.latest), original)
        self.assertTrue(self.release.state["demo_cleanup"])
        self.assertNotIn("demo_passed", self.release.state)

    def test_alias_revision_is_refreshed_after_permission_setup(self):
        self.release.prepare()
        self.assertEqual(self.release.state["previous_alias_revision"], self.aws.live["RevisionId"])
        self.release.deploy(self.package())
        self.assertTrue(self.release.state["candidate_verified"])

    def test_state_from_another_environment_is_rejected(self):
        self.release.prepare()
        with self.assertRaisesRegex(ReleaseError, "different function"):
            Release("prod", self.path, self.aws)

    def test_aws_cli_diagnostics_do_not_echo_sensitive_stderr(self):
        class Result:
            returncode, stdout = 1, ""
            stderr = "An error occurred (AccessDeniedException) sensitive-value"
        with patch("subprocess.run", return_value=Result()):
            with self.assertRaises(AwsError) as context:
                AwsCli().call("lambda", "get-function-configuration", function_name="test")
        self.assertNotIn("sensitive-value", str(context.exception))
        self.assertIn("AccessDeniedException", str(context.exception))


if __name__ == "__main__":
    unittest.main()
