# Environments and automatic delivery

A feature PR merged into `develop` starts a complete automatic CI/CD run through Development, Testing, Staging and Production. Human code review happens before the merge; no branch promotion or deployment approval is needed after the run starts.

The workflows update existing AWS Academy Learner Lab resources in `us-east-1`. They do not provision Lambda functions, API Gateway, DynamoDB, S3 or IAM. The optional monitoring setup attaches the AWS Lambda Insights layer to Production and creates a CloudWatch dashboard using the existing LabRole. Workflow configuration is not proof that the cloud setup is operational.

## Environment layout

| Runtime environment | API stage | Lambda | GitHub environment |
|---|---|---|---|
| Development | `/dev` | `poco-pii-api-handler-dev` | `dev` |
| Testing | `/test` | `poco-pii-api-handler-test` | `testing` |
| Staging | `/staging` | `poco-pii-api-handler-staging` | `staging` |
| Production | `/prod` | `poco-pii-api-handler` | `production` |

API base: `https://6xz841x652.execute-api.us-east-1.amazonaws.com/{stage}`.

The four runtimes need separate Lambda functions, DynamoDB tables and S3 buckets. API Gateway `6xz841x652` has a stage for each; each stage's `lambdaName` variable and invoke permissions must route to the intended Lambda. Sharing one API Gateway does not mean sharing runtime or storage.

`develop` triggers the entire chain. Feature branches run CI and deploy after merging into `develop`. In the new workflow, `test/qa`, `release/**` and `main` run CI but do not select an environment. The workflow does not automatically merge or synchronize those branches. Branches retaining older workflow files can still use their previous deployment behaviour; avoid using them for promotion after switching to this flow. The environment is named Testing even though the API stage remains `test`.

## What runs automatically

The delivery workflow is `.github/workflows/deploy.yml`. It triggers on pushes to `develop`, including PR merges, and supports manual dispatch from `develop` only.

1. Validate the source branch and call shared CI: locked Rust workspace tests, frontend unit tests, lint, TypeScript and production build. Save the production Pages artifact with commit metadata.
2. Call the shared read-only `test-aws.yml` workflow. Check all four Lambda runtime/role/storage configurations, API stage variables, distinct table/bucket names, actual DynamoDB table schemas/TTL and S3 bucket access/region before changing code.
3. Build Lambda once in `amazonlinux:2023`, validate its executable/glibc compatibility and save `bootstrap.zip` as an artifact.
4. Deploy that ZIP to Development, then Testing, then Staging, then Production. Each stage calls the shared `deploy-environment.yml` and waits for the previous stage to pass.
5. At each stage, check the deployed Lambda package hash and configuration, then verify `/health` returns HTTP 200, `status: ok` and the expected environment identity. After Testing and Staging deployment, rerun readiness checks and test encode, API session mappings, actual DynamoDB persistence/expiry, S3 archive content and decode. Both environments must pass these integration tests before promotion.
6. After production backend health verification passes, enable/verify production Lambda Insights, wait for CPU/memory/disk/network/HTTP metric samples and create/update the production dashboard. Then publish the validated production frontend through GitHub Pages. Check `deployment.json` identifies the workflow commit and production stage, and check the public website is reachable.
7. Keep the Lambda artifact for seven days. Save workflow logs and screenshots as evidence for the report.

All deployment orchestration stays in YAML; there are no pipeline helper shell scripts or Playwright tests. Development, Testing and Staging have persistent API/storage runtimes in AWS, but this workflow does not publish frontend sites for them. Only Production has a public Pages site (`littlepoco.me`). The Lambda package is identical across environments.

Failed CI, readiness, health, API integration or monitoring checks prevent subsequent stages. A failure after production has already changed marks the run failed but does not roll back deployed code. Backend and frontend updates are separate operations; this pipeline does not promise an atomic release.

One concurrency group serializes the entire delivery chain, so runs cannot overwrite another run's Testing/Staging environments. Active runs are not canceled by newer pushes. GitHub may replace a pending run with a newer pending run, so not every queued commit is guaranteed a deployment.

## Setup before the first deployment

Complete these before merging the automatic workflow into `develop`; that merge triggers production delivery.

- The workflow references GitHub environments `dev`, `testing`, `staging`, `production` and `github-pages`. GitHub automatically creates missing environments without reviewers or environment secrets, so you do not need settings access to create them manually. Existing restrictions must allow `develop` without approval pauses. Only changing restrictions or adding environment-specific secrets requires the owner/admin.
- Keep Pages **Source: GitHub Actions**, the existing custom domain and DNS. Its environment's branch policy must allow `develop`; a `main`-only policy blocks this pipeline.
- Store valid `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` as repository secrets. Environment secrets can override them for environment jobs; preflight uses repository credentials. All must reach the same intended Learner Lab account.
- Verify four Lambda functions use runtime `provided.al2023`, handler `bootstrap`, architecture `x86_64` and the existing `LabRole`. Set `ENVIRONMENT` to `dev`, `test`, `staging` or `prod`, and provide nonempty `DYNAMODB_TABLE` and `S3_BUCKET`. Verify timeout/memory suit encode/decode; the prior setup used 512 MB / 30 seconds.
- Verify DynamoDB string keys `sessionId` (partition) and `token` (sort), plus enabled TTL on `expiresAt`. Enable each Lambda to access its own table/bucket. The deployment runner needs Lambda/API Gateway configuration reads, DynamoDB table/TTL descriptions, S3 bucket access checks and Lambda code updates. Readiness checks describe storage resources but do not read or write application items/objects or prove the Lambda role can use them.
- Verify API Gateway stage integrations, Lambda invocation permissions and CORS for local development and the public site. Direct S3 browser uploads also need appropriate bucket CORS.
- Set up production monitoring as described below and confirm real data appears.

Branch protections remain optional: review PRs and check CI manually before merging. This setup does not require another person's review or prevent you from merging your own PR. GitHub does not allow authors to submit a formal approving review on their own PR; reviewing the changes and merging is the team's sign-off. Deployment jobs still depend on passing CI, even without branch protection. For environment configuration see [GitHub's environment documentation](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) and [GitHub's PR approval rules](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

Learner Lab credentials expire. Renew them before the run; this workflow cannot renew the university lab session. A deployment run is automatic while valid credentials and resource permissions remain available. Expired credentials are a setup failure, not evidence that the pipeline has completed successfully.

## Read-only readiness checkpoint

Run the existing `test-aws.yml` workflow from the feature branch before creating or merging the deployment PR:

```sh
gh workflow run test-aws.yml --repo Schnitze1/Poco --ref feature/cicd-readiness
```

This uses repository credentials and requires no GitHub environment settings access. It reads AWS identity, Lambda configuration, API stage targets, table schemas/TTL and bucket access/regions. It requires four different tables and buckets and writes a resource summary to the Actions run summary. It does not deploy, provision resources or change application data. The deployment workflow calls the same checks before packaging.

If it fails, fix the specific AWS configuration or permission reported and rerun this checkpoint. A passing readiness check verifies resource configuration and runner access; it does not replace live encode/decode, persistence or end-to-end acceptance tests.

## Live API integration checkpoint

Run the same existing workflow with its optional integration test enabled:

```sh
gh workflow run test-aws.yml --repo Schnitze1/Poco --ref feature/cicd-readiness \
  -f run-api-tests=true -f api-stage=test
```

The default invocation remains read-only. With `run-api-tests=true`, the workflow first verifies all four environments, then creates one fresh synthetic session in the selected Testing or Staging API. It checks email redaction, API mappings, a directly queried DynamoDB item and its expiry, actual S3 archive content and decode restoration. Cleanup runs on normal completion or test failure: it deletes that session through the API, checks its table items are gone and deletes only its archive object. A test or cleanup failure fails the job. The API test is restricted to `test` and `staging`.

Deployment reuses this test after updating Testing and Staging. Feature-branch diagnostic runs test the currently deployed code; only the delivery run after a merge verifies the newly deployed candidate. Neither invocation deploys code by itself. Browser interactions remain a separate requirement. Production monitoring is configured using the optional mode below.

## Assignment coverage and remaining evidence

| Specification | Pipeline support | Evidence needed |
|---|---|---|
| Level 1: four environments | Separate Lambda/API stages and storage, validated before delivery | AWS configuration and isolation screenshots |
| Level 2: production instrumentation/monitoring | Automated Lambda Insights setup, metric ingestion checks and the Poco-Production CloudWatch dashboard | A successful monitoring run plus populated dashboard screenshots under real traffic |
| Level 3: automated unit, integration and end-to-end tests before production | Shared Rust/Vitest CI plus live API/DynamoDB/S3 integration gates in Testing/Staging; browser acceptance tests are missing | Add automated browser acceptance coverage before claiming completion, then verify the public app/database |
| Level 4: automatic trigger-to-production workflow | A `develop` push starts the full chain with no further branch merges | A visible feature change progressing through one successful run to the published website |

## Production monitoring checkpoint

Configure instrumentation before the final merge using the existing workflow:

```sh
gh workflow run test-aws.yml --repo Schnitze1/Poco --ref feature/cicd-readiness \
  -f configure-monitoring=true
```

This mode updates only the Production Lambda's layer configuration and the `Poco-Production` CloudWatch dashboard; it does not publish new application code or change IAM. It preserves unrelated layers, uses a revision check to avoid overwriting concurrent configuration changes and verifies that the application code hash stays the same. If health validation fails after a layer update, it attempts to restore the previous layers. Missing metric samples or dashboard errors fail the monitoring job; these later failures do not roll back a healthy layer configuration.

The workflow pins the AWS x86-64 [Lambda Insights extension](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versionsx86-64.html) for `us-east-1` (extension 1.0.776.0, layer version 66). It relies on the existing `LabRole` log permissions for `/aws/lambda-insights`, generates a few Production health requests and waits for actual CPU, memory, disk, network and HTTP-latency samples. It does not create or attach IAM policies. If the lab denies layer updates, monitoring logs, metric reads or dashboard creation, resolve the reported permission with the lab owner/instructor before claiming completion.

Open **CloudWatch → Dashboards → Poco-Production** in `us-east-1`. The dashboard covers requests/errors/throttles, execution duration, CPU time, memory, temporary-disk usage, received/sent bytes, API Gateway HTTP latency and HTTP errors. See [Lambda Insights metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-metrics-lambda-functions.html) for units. CPU time is measured in milliseconds; temporary-disk usage is bytes used rather than disk I/O throughput. These are the serverless equivalents available here and should be explained accurately in the presentation.

The application log group is `/aws/lambda/poco-pii-api-handler`; enhanced performance events go to `/aws/lambda-insights`. Save populated dashboard screenshots and the `production-monitoring-evidence` artifact for the final report. Metrics are near real time and may take a few minutes to appear. The artifact retains sample responses and dashboard JSON for seven days. The normal delivery workflow reuses monitoring setup/verification after Production deployment and before website publication.

## Demonstration recording

1. Show the four runtime/storage environments and production dashboard; open the current public app.
2. Make a small visible UI change on a feature branch and show its PR CI results.
3. Merge the PR into `develop`. Follow the resulting **Deploy** run through CI, preflight, package, Development, Testing, Staging, Production and Pages publication without manual environment promotions.
4. Show Testing/Staging readiness, health and live API/storage integration checks passed before production started, and show the same Lambda artifact/hash being reused. Once browser acceptance tests are added, show their results too.
5. Open the public website, show the visible change and demonstrate Encode → Vault → Decode. Show the final public-site check verifies the same commit.
6. Show fresh production metrics/logs and save screenshots, logs and test reports for the final report. If a failure is demonstrated, show that later stages are skipped.

The live API integration tests verify encode/decode and actual DynamoDB/S3 persistence using synthetic data. Automated browser end-to-end acceptance tests against Testing remain necessary to fulfil Level 3; Level 4 also requires all prior levels. Manually demonstrate encode/decode, vault edits and actual DynamoDB/S3 data as supplementary evidence.

The prepared workflows and local validation are not a substitute for this successful live demonstration. Run and verify the complete cloud pipeline before recording.
