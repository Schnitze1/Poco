#!/usr/bin/env python3
"""Versioned Poco releases. Uses the runner's AWS CLI; never saves environment values.

The live alias is the serving release. $LATEST is only a build/deployment workspace.
State is written before traffic changes so a later workflow step can recover even
when an update response is lost. AWS RevisionId guards reject concurrent changes.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import uuid


API = "6xz841x652"
REGION = "us-east-1"
ALIAS = "live"
FUNCTIONS = {s: "poco-pii-api-handler" + ("" if s == "prod" else f"-{s}")
             for s in ("dev", "test", "staging", "prod")}
INSIGHTS = f"arn:aws:lambda:{REGION}:580247275435:layer:LambdaInsightsExtension:66"


class ReleaseError(RuntimeError):
    pass


class AwsError(ReleaseError):
    def __init__(self, operation, code):
        super().__init__(f"AWS {operation}: {code}. Check the lab session and role permissions.")
        self.code = code


class InjectedFailure(ReleaseError):
    """Expected only in the Testing demonstration."""


class AwsCli:
    def call(self, service, operation, _output_file=None, **params):
        command = ["aws", service, operation, "--region", REGION,
                   "--no-cli-pager", "--output", "json"]
        for key, value in params.items():
            command += ["--" + key.replace("_", "-"),
                        json.dumps(value) if isinstance(value, (list, dict)) else str(value)]
        if _output_file is not None:
            command.append(str(_output_file))
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode:
            # Do not echo configuration, payloads, or credentials from CLI output.
            match = re.search(r"An error occurred \(([^)]+)\)", result.stderr)
            raise AwsError(operation, match[1] if match else f"CLI exit {result.returncode}")
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def wait(self, function):
        result = subprocess.run(["aws", "lambda", "wait", "function-updated", "--function-name",
                                 function, "--region", REGION, "--no-cli-pager"],
                                text=True, capture_output=True, check=False)
        if result.returncode:
            raise ReleaseError("Lambda update waiter failed; inspect update state")


def fingerprint(config):
    # A digest lets us verify rollback configuration without exposing its values.
    keys = ("CodeSha256", "Runtime", "Handler", "Role", "MemorySize", "Timeout",
            "Description", "Architectures", "Environment", "EphemeralStorage",
            "TracingConfig", "KMSKeyArn", "DeadLetterConfig", "FileSystemConfigs",
            "LoggingConfig", "SnapStart")
    snapshot = {k: config[k] for k in keys if k in config}
    snapshot["Layers"] = [layer["Arn"] for layer in config.get("Layers", [])]
    # VpcConfig includes AWS-generated IDs that are not versioned settings.
    snapshot["VpcConfig"] = {k: config.get("VpcConfig", {}).get(k)
                             for k in ("SubnetIds", "SecurityGroupIds", "Ipv6AllowedForDualStack")}
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def health(stage):
    for attempt in range(5):
        try:
            with urlopen(f"https://{API}.execute-api.{REGION}.amazonaws.com/{stage}/health",
                         timeout=20) as response:
                body = json.load(response)
                if response.status == 200 and body.get("status") == "ok" and body.get("env") == stage:
                    return
        except (OSError, ValueError):
            pass
        if attempt < 4:
            time.sleep(3)
    raise ReleaseError(f"{stage} API health/environment verification failed")


class Release:
    def __init__(self, stage, state_path, aws=None, check_health=health):
        if stage not in FUNCTIONS:
            raise ReleaseError("Unknown Poco stage")
        self.stage, self.function = stage, FUNCTIONS[stage]
        self.path = Path(state_path)
        self.aws, self.health = aws or AwsCli(), check_health
        self.state = {}
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            if (self.state.get("function"), self.state.get("stage")) != (self.function, stage):
                raise ReleaseError("State belongs to a different function/stage")

    def event(self, message, **fields):
        self.state.update(fields)
        self.state.setdefault("events", []).append({"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                    "message": message})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2) + "\n")
        temporary.replace(self.path)
        print(f"{self.stage}: {message}", flush=True)

    def config(self, version=None):
        params = {"function_name": self.function}
        if version is not None:
            params["qualifier"] = version
        return self.aws.call("lambda", "get-function-configuration", **params)

    def validate_config(self, config):
        env = config.get("Environment", {}).get("Variables", {})
        if not (config.get("Runtime") == "provided.al2023" and
                config.get("Handler") == "bootstrap" and config.get("Architectures") == ["x86_64"] and
                config.get("State") == "Active" and
                config.get("Role", "").endswith("/LabRole") and
                config.get("LastUpdateStatus", "Successful") == "Successful" and
                env.get("ENVIRONMENT") == self.stage and env.get("DYNAMODB_TABLE") and env.get("S3_BUCKET")):
            raise ReleaseError("Unexpected runtime, role, stage, storage or update state")

    def route(self):
        result = self.aws.call("apigateway", "get-stage", rest_api_id=API, stage_name=self.stage)
        if result.get("canarySettings", {}).get("percentTraffic", 0):
            raise ReleaseError("API Gateway canary traffic is not supported by this release workflow")
        return result.get("variables", {}).get("lambdaName")

    def set_route(self, expected, target):
        if self.route() != expected:
            raise ReleaseError("API routing changed externally; refusing to overwrite it")
        self.aws.call("apigateway", "update-stage", rest_api_id=API, stage_name=self.stage,
                      patch_operations=[{"op": "replace", "path": "/variables/lambdaName", "value": target}])
        if self.route() != target:
            raise ReleaseError("API stage variable did not match the requested target")

    def alias(self, optional=False):
        try:
            value = self.aws.call("lambda", "get-alias", function_name=self.function, name=ALIAS)
        except AwsError as error:
            if optional and error.code == "ResourceNotFoundException":
                return None
            raise
        if not value["FunctionVersion"].isdigit() or value.get("RoutingConfig", {}).get("AdditionalVersionWeights"):
            raise ReleaseError("live must select one numbered version without weighted routing")
        return value

    def audit(self):
        """Read-only check of the actual API integration before touching routing."""
        route = self.route()
        if route not in (self.function, f"{self.function}:{ALIAS}"):
            raise ReleaseError("API stage points to an unexpected Lambda")
        resources = self.aws.call("apigateway", "get-resources", rest_api_id=API)["items"]
        found = False
        for resource in resources:
            for method in resource.get("resourceMethods", {}):
                integration = self.aws.call("apigateway", "get-integration", rest_api_id=API,
                                            resource_id=resource["id"], http_method=method)
                if integration.get("type") == "MOCK":
                    continue
                uri = integration.get("uri", "")
                if integration.get("type") != "AWS_PROXY" or ":function:${stageVariables.lambdaName}/invocations" not in uri:
                    raise ReleaseError("API integration must invoke the lambdaName stage variable")
                found = True
        if not found:
            raise ReleaseError("No Lambda proxy integration found")
        config = self.config(ALIAS if route.endswith(":" + ALIAS) else None)
        self.validate_config(config)
        self.health(self.stage)
        print(f"{self.stage}: integration, routing and baseline health verified", flush=True)
        return route, config

    def publish(self, config):
        # AWS refuses to publish unchanged code/configuration. Reuse an exact snapshot.
        versions = self.aws.call("lambda", "list-versions-by-function", function_name=self.function)["Versions"]
        for version in reversed(versions):
            if version["Version"].isdigit() and fingerprint(version) == fingerprint(config):
                return version["Version"]
        result = self.aws.call("lambda", "publish-version", function_name=self.function,
                               revision_id=config["RevisionId"], code_sha256=config["CodeSha256"])
        version = result["Version"]
        if fingerprint(self.config(version)) != fingerprint(config):
            raise ReleaseError("Published version differs from the intended snapshot")
        return version

    def permission(self, config):
        account = config["FunctionArn"].split(":")[4]
        source = f"arn:aws:execute-api:{REGION}:{account}:{API}/{self.stage}/*/*"
        statement_id = f"poco-live-{self.stage}"
        try:
            self.aws.call("lambda", "add-permission", function_name=self.function, qualifier=ALIAS,
                          statement_id=statement_id, action="lambda:InvokeFunction",
                          principal="apigateway.amazonaws.com", source_arn=source, source_account=account)
        except AwsError as error:
            if error.code != "ResourceConflictException":
                raise
            policy = self.aws.call("lambda", "get-policy", function_name=self.function, qualifier=ALIAS)
            statements = json.loads(policy["Policy"])["Statement"]
            expected = next((s for s in statements if s.get("Sid") == statement_id), {})
            condition = expected.get("Condition", {})
            if not (expected.get("Effect") == "Allow" and expected.get("Action") == "lambda:InvokeFunction" and
                    expected.get("Principal") == {"Service": "apigateway.amazonaws.com"} and
                    expected.get("Resource") == f'{config["FunctionArn"].split(":function:")[0]}:function:{self.function}:{ALIAS}' and
                    condition.get("ArnLike", {}).get("AWS:SourceArn") == source and
                    condition.get("StringEquals", {}).get("AWS:SourceAccount") == account):
                raise ReleaseError("Existing alias permission does not match the required API/stage scope")

    def prepare(self):
        if self.state:
            raise ReleaseError("Use a new state file for each release attempt")
        original_route, config = self.audit()
        self.event("Preparing versioned routing", function=self.function, stage=self.stage,
                   original_route=original_route, prepared=False, owner="poco-" + uuid.uuid4().hex)
        existing = self.alias(optional=True)
        if original_route.endswith(":" + ALIAS):
            if not existing:
                raise ReleaseError("Routed alias is missing")
            previous = existing["FunctionVersion"]
        else:
            if existing and fingerprint(self.config(existing["FunctionVersion"])) != fingerprint(config):
                raise ReleaseError("Unused live alias differs from the serving baseline; inspect before migration")
            previous = existing["FunctionVersion"] if existing else self.publish(config)
        baseline = self.config(previous)
        self.validate_config(baseline)
        self.event("Baseline snapshot retained", previous_version=previous,
                   previous_hash=baseline["CodeSha256"], previous_fingerprint=fingerprint(baseline))
        if not existing:
            existing = self.aws.call("lambda", "create-alias", function_name=self.function,
                                     name=ALIAS, function_version=previous, description="Poco live baseline")
        self.permission(baseline)
        self.event("Alias invocation permission verified", previous_alias_revision=existing["RevisionId"])
        if original_route == self.function:
            # Record intent first; recovery also handles an applied update whose response was lost.
            self.event("Migrating only this stage to live", route_migration_intent=True)
            self.set_route(self.function, f"{self.function}:{ALIAS}")
        self.verify_previous()
        self.event("Baseline routing and health verified", prepared=True)

    def wait(self):
        # Use the CLI waiter; configuration is inspected again after it returns.
        self.aws.wait(self.function)

    def invoke(self, version):
        # A real REST API v1 proxy event exercises the runtime before changing traffic.
        event = {"resource": "/{proxy+}", "path": "/health", "httpMethod": "GET",
                 "headers": {"host": f"{API}.execute-api.{REGION}.amazonaws.com"},
                 "multiValueHeaders": {}, "queryStringParameters": None,
                 "multiValueQueryStringParameters": None, "pathParameters": {"proxy": "health"},
                 "stageVariables": None, "body": None, "isBase64Encoded": False,
                 "requestContext": {"resourcePath": "/{proxy+}", "httpMethod": "GET",
                                    "path": f"/{self.stage}/health", "stage": self.stage,
                                    "identity": {"sourceIp": "127.0.0.1"},
                                    "requestId": "poco-release-health", "accountId": "", "apiId": API}}
        with tempfile.TemporaryDirectory() as directory:
            payload, output = Path(directory, "event.json"), Path(directory, "response.json")
            payload.write_text(json.dumps(event))
            metadata = self.aws.call("lambda", "invoke", function_name=self.function, qualifier=version,
                                     payload=f"fileb://{payload}", _output_file=output)
            if metadata.get("FunctionError") or metadata.get("ExecutedVersion") != version:
                raise ReleaseError("Candidate runtime invocation failed or executed the wrong version")
            response = json.loads(output.read_text())
            body = response.get("body", "")
            if response.get("isBase64Encoded"):
                body = base64.b64decode(body).decode()
            body = json.loads(body)
            if response.get("statusCode") != 200 or body.get("status") != "ok" or body.get("env") != self.stage:
                raise ReleaseError("Version health invocation failed")

    def deploy(self, zip_path=None, demo=False):
        if not self.state.get("prepared") or self.state.get("candidate_version"):
            raise ReleaseError("Prepare a fresh release before deploying")
        if demo and self.stage != "test":
            raise ReleaseError("Rollback demonstration is restricted to Testing")
        if not demo and zip_path is None:
            raise ReleaseError("Deployment requires a ZIP")
        config = self.config()
        self.validate_config(config)
        if demo:
            self.event("Saving Testing metadata for demonstration cleanup",
                       demo_description=config.get("Description", ""), demo_hash=config["CodeSha256"])
        marker = f'Poco release {os.environ.get("GITHUB_SHA", "local")[:12]} {self.state["owner"]}'
        # Configure instrumentation before creating the immutable Production version.
        params = {"description": marker}
        if self.stage == "prod":
            layers = [layer["Arn"] for layer in config.get("Layers", [])
                      if ":layer:LambdaInsightsExtension:" not in layer["Arn"]] + [INSIGHTS]
            if len(layers) > 5:
                raise ReleaseError("Production has no layer slot available for Lambda Insights")
            params["layers"] = layers
        self.event("Preparing candidate configuration", candidate_description=marker)
        self.aws.call("lambda", "update-function-configuration", function_name=self.function,
                      revision_id=config["RevisionId"], **params)
        self.wait()
        config = self.config()
        self.event("Candidate configuration prepared", candidate_latest_revision=config["RevisionId"])
        expected_hash = config["CodeSha256"]
        if zip_path is not None:
            package = Path(zip_path).resolve()
            expected_hash = base64.b64encode(hashlib.sha256(package.read_bytes()).digest()).decode()
            self.aws.call("lambda", "update-function-code", function_name=self.function,
                          zip_file=f"fileb://{package}", revision_id=config["RevisionId"])
            self.wait()
            config = self.config()
        self.validate_config(config)
        if config["CodeSha256"] != expected_hash or config.get("Description") != marker:
            raise ReleaseError("Candidate package/configuration verification failed")
        candidate = self.publish(config)
        self.event("Candidate snapshot published", candidate_version=candidate,
                   candidate_hash=expected_hash, candidate_fingerprint=fingerprint(config))
        self.invoke(candidate)
        self.event("Candidate runtime health verified; activating live", activation_intent=True)
        alias = self.aws.call("lambda", "update-alias", function_name=self.function, name=ALIAS,
                              function_version=candidate, revision_id=self.state["previous_alias_revision"],
                              description=self.state["owner"])
        self.event("Candidate now selected by live", activation_revision=alias["RevisionId"])
        self.complete()

    def verify_previous(self):
        current = self.alias()
        previous = self.state["previous_version"]
        if current["FunctionVersion"] != previous or fingerprint(self.config(previous)) != self.state["previous_fingerprint"]:
            raise ReleaseError("Previous version/configuration verification failed")
        if self.route() != f"{self.function}:{ALIAS}":
            raise ReleaseError("API stage no longer routes through live")
        self.health(self.stage)

    def complete(self):
        current = self.alias()
        if (current["FunctionVersion"] != self.state["candidate_version"] or
                current.get("Description") != self.state["owner"] or
                current["RevisionId"] != self.state.get("activation_revision") or
                fingerprint(self.config(current["FunctionVersion"])) != self.state["candidate_fingerprint"] or
                self.route() != f"{self.function}:{ALIAS}"):
            raise ReleaseError("Live candidate ownership, routing or configuration changed")
        self.health(self.stage)
        self.event("Live candidate configuration and API health verified", candidate_verified=True)

    def recover(self):
        if not self.state:
            print(f"{self.stage}: no release state; no traffic was changed")
            return
        if not self.state.get("prepared"):
            if self.state.get("route_migration_intent"):
                route = self.route()
                if route == f"{self.function}:{ALIAS}":
                    # No candidate code is ever changed before preparation succeeds.
                    self.set_route(route, self.state["original_route"])
                elif route != self.state["original_route"]:
                    raise ReleaseError("Preparation failed and routing changed externally")
                self.health(self.stage)
            self.event("Preparation stopped before candidate deployment")
            return
        current = self.alias()
        previous = self.state["previous_version"]
        if current["FunctionVersion"] != previous:
            if not (self.state.get("activation_intent") and
                    current["FunctionVersion"] == self.state.get("candidate_version") and
                    current.get("Description") == self.state["owner"] and
                    current["RevisionId"] == self.state.get("activation_revision", current["RevisionId"])):
                raise ReleaseError("Alias changed externally; refusing to overwrite another release")
            if self.route() != f"{self.function}:{ALIAS}":
                raise ReleaseError("Routing changed externally; inspect before recovery")
            if fingerprint(self.config(previous)) != self.state["previous_fingerprint"]:
                raise ReleaseError("Retained baseline configuration differs from saved state")
            self.aws.call("lambda", "update-alias", function_name=self.function, name=ALIAS,
                          function_version=previous, revision_id=current["RevisionId"],
                          description="Poco restored previous release")
            self.event("live restored to the previous numbered version")
        self.verify_previous()
        self.event("Previous version, configuration, routing and health verified", recovered=True)

    def demo_cleanup(self):
        if not self.state.get("recovered"):
            raise ReleaseError("Cannot clean up the demonstration before recovery is verified")
        if self.state["original_route"] == self.function:
            self.set_route(f"{self.function}:{ALIAS}", self.function)
        config = self.config()
        if (config["CodeSha256"] != self.state["demo_hash"] or
                config.get("Description") != self.state["candidate_description"] or
                config["RevisionId"] != self.state["candidate_latest_revision"]):
            raise ReleaseError("Testing $LATEST changed externally; refusing metadata cleanup")
        self.aws.call("lambda", "update-function-configuration", function_name=self.function,
                      revision_id=config["RevisionId"], description=self.state["demo_description"])
        self.wait()
        self.health(self.stage)
        self.event("Testing original routing and metadata restored", demo_cleanup=True)

    def demonstrate(self):
        if self.stage != "test":
            raise ReleaseError("Rollback demonstration is restricted to Testing")
        try:
            self.prepare()
            self.deploy(demo=True)
            self.event("Injecting verification failure (healthy unchanged application)", demo_failure_injected=True)
            raise InjectedFailure("Deliberate post-deployment verification failure")
        except InjectedFailure:
            print("Expected verification failure detected; starting automatic recovery", flush=True)
        finally:
            self.recover()
        self.demo_cleanup()
        self.event("Controlled Testing rollback demonstration passed", demo_passed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["audit", "prepare", "deploy", "complete", "recover", "demo"])
    parser.add_argument("--stage", choices=list(FUNCTIONS), required=True)
    parser.add_argument("--state", required=True, help="Safe release-state JSON path")
    parser.add_argument("--zip")
    args = parser.parse_args()
    release = Release(args.stage, args.state)
    try:
        if args.action == "audit":
            release.audit()
        elif args.action == "prepare":
            release.prepare()
        elif args.action == "deploy":
            release.deploy(args.zip)
        elif args.action == "demo":
            release.demonstrate()
        else:
            getattr(release, args.action)()
    except (ReleaseError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
