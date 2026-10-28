# Environments and automatic delivery

A feature PR merged into `main` starts a complete automatic CI/CD run through Development, Testing, Staging and Production. Human code review happens before the merge; no branch promotion or deployment approval is needed after the run starts.

The workflows update existing AWS Academy Learner Lab resources in `us-east-1`. They do not provision the base Lambda functions, API Gateway, DynamoDB, S3 or IAM. Versioned delivery automatically configures Lambda versions/live aliases and each API stage’s routing using the existing LabRole. Production deployment includes the AWS Lambda Insights layer in its version snapshot; the monitoring job verifies it and creates a CloudWatch dashboard. Workflow configuration is not proof that the cloud setup is operational.

## Environment layout

| Runtime environment | API stage | Lambda | GitHub environment |
|---|---|---|---|
| Development | `/dev` | `poco-pii-api-handler-dev` | `dev` |
| Testing | `/test` | `poco-pii-api-handler-test` | `testing` |
| Staging | `/staging` | `poco-pii-api-handler-staging` | `staging` |
| Production | `/prod` | `poco-pii-api-handler` | `production` |

API base: `https://6xz841x652.execute-api.us-east-1.amazonaws.com/{stage}`.

The four runtimes need separate Lambda functions, DynamoDB tables and S3 buckets. API Gateway `6xz841x652` has a stage for each; each stage's `lambdaName` variable and invoke permissions must route to the intended Lambda. Sharing one API Gateway does not mean sharing runtime or storage.

`main` is the single trunk and triggers the entire delivery chain. Short-lived feature/fix branches run CI and target `main` in their PRs. A push to `main` runs CI through the delivery workflow, avoiding a second standalone push-CI run. Branch pushes and PR updates can both run CI; only `main` deploys through this version of the workflow.

`develop`, `test/qa` and `release/**` are retained as historical branches. The workflow does not automatically merge or synchronize them. Branches retaining older workflow files can still trigger their previous deployments; do not use them for promotion or continue merging work into `develop`. The environment is named Testing even though the API stage remains `test`.

## Why the environments are separate

| Environment | Current checks/use | Practical purpose |
|---|---|---|
| Development | Package/configuration verification and API health; available to the local frontend | Shared cloud integration and debugging with development data |
| Testing | Live API, DynamoDB, S3 and Chromium acceptance using temporary synthetic data | Repeatable functional checks without changing customer records |
| Staging | The same acceptance checks against a separate runtime/storage configuration | Rehearse a production deployment; currently adds configuration verification but limited extra functional coverage |
| Production | Public frontend/API, deployed package and health checks, production monitoring | Serve users and observe errors, latency and resource usage |

Each environment has its own Lambda, DynamoDB table and S3 bucket. API Gateway receives HTTP requests and routes each stage to its Lambda. Lambda runs the Rust API, DynamoDB holds session mappings, and S3 holds uploaded documents and redacted archives. GitHub Actions builds, tests and deploys; GitHub Pages hosts only the production frontend. CloudWatch and Lambda Insights provide production logs/metrics.

The current setup shares an AWS account, API Gateway and LabRole. Separate storage is useful isolation, but it is not an account/IAM security boundary. A customer-facing system would benefit from stronger production access isolation, reproducible infrastructure, representative staging data, different staging checks and broader recovery testing beyond the controlled Testing demonstration. Additional public frontend previews would help human acceptance but are not part of this pipeline.

## What runs automatically

The delivery workflow is `.github/workflows/deploy.yml`. It triggers on pushes to `main`, including PR merges, and supports manual dispatch from `main` only.

1. Validate the source branch and call shared CI: locked Rust workspace tests, frontend unit tests, lint, TypeScript and production build. Save the production Pages artifact with commit metadata.
2. Call the shared read-only `test-aws.yml` workflow once. Check all four Lambda runtime/role/storage configurations, API stage variables, distinct table/bucket names, actual DynamoDB table schemas/TTL and S3 bucket access/region before changing code.
3. Build Lambda once in `amazonlinux:2023`, validate its executable/glibc compatibility and save `bootstrap.zip` as an artifact.
4. Retain the working version, configure `live` routing automatically and deploy that ZIP as a new numbered version to Development, then Testing, then Staging, then Production. Each stage calls the shared `deploy-environment.yml` and waits for the previous stage to pass.
5. At each stage, check the deployed Lambda package hash and configuration, then verify `/health` returns HTTP 200, `status: ok` and the expected environment identity. Within each Testing and Staging deployment job, test encode, API session mappings, actual DynamoDB persistence/expiry, S3 archive content and decode. Then build the frontend for that API stage and run Chromium acceptance for Encode → Vault → refresh → Decode plus an unknown-token warning. Both environments must pass integration and browser acceptance before promotion.
6. Include production Lambda Insights before publishing its candidate version. After production backend health verification passes, verify that instrumentation, wait for CPU/memory/disk/network/HTTP metric samples and create/update the production dashboard. Then publish the validated production frontend through GitHub Pages. Check `deployment.json` identifies the workflow commit and production stage, and check the public website is reachable.
7. On a failure inside an environment deployment/verification job, attempt to restore its previous backend version and verify routing/health. Keep the original job failed and stop promotion. Save release/recovery JSON for 30 days and the Lambda artifact for seven days. Save workflow logs and screenshots as evidence for the report.

The Actions graph has one readiness job, one deployment job for each environment, a dedicated monitoring job and one website publication/verification job. Testing/Staging acceptance appears as steps inside those environment jobs; conditional API/monitoring jobs no longer add skipped branches to the graph.

Deployment orchestration and live acceptance checks stay in YAML. Version publication, alias routing and recovery use `scripts/lambda_release.py`, with offline regression tests in shared CI; there are no separate E2E spec/config files. Browser acceptance uses the Playwright library in an inline Node script. Development, Testing and Staging have persistent API/storage runtimes in AWS, but this workflow does not publish frontend sites for them. Only Production has a public Pages site (`littlepoco.me`). The Lambda package is identical across environments.

Failed CI, readiness, health, API integration or monitoring checks prevent subsequent stages. A deployment or verification failure within an environment job triggers guarded backend recovery to its retained previous version. Later monitoring-data/dashboard or Pages failures stop the run without reverting a healthy backend. See [ROLLBACK.md](ROLLBACK.md) for setup, permissions, the Testing demonstration and recovery limits. Backend and frontend updates are separate operations; this pipeline does not promise an atomic release.

One concurrency group serializes the entire delivery chain, so runs cannot overwrite another run's Testing/Staging environments. Active runs are not canceled by newer pushes. GitHub may replace a pending run with a newer pending run, so not every queued commit is guaranteed a deployment.

## Setup before the first deployment

Complete these before merging the automatic workflow into `main`; that merge triggers production delivery.

- The workflow references GitHub environments `dev`, `testing`, `staging`, `production` and `github-pages`. GitHub automatically creates missing environments without reviewers or environment secrets, so you do not need settings access to create them manually. Existing restrictions must allow `main` without approval pauses. Only changing restrictions or adding environment-specific secrets requires the owner/admin.
- Keep Pages **Source: GitHub Actions**, the existing custom domain and DNS. Its environment's branch policy must allow `main`; a policy allowing only `develop` blocks this pipeline.
- Store valid `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` as repository secrets. Environment secrets can override them for environment jobs; preflight uses repository credentials. All must reach the same intended Learner Lab account.
- Verify four Lambda functions use runtime `provided.al2023`, handler `bootstrap`, architecture `x86_64` and the existing `LabRole`. Set `ENVIRONMENT` to `dev`, `test`, `staging` or `prod`, and provide nonempty `DYNAMODB_TABLE` and `S3_BUCKET`. Verify timeout/memory suit encode/decode; the prior setup used 512 MB / 30 seconds.
- Verify DynamoDB string keys `sessionId` (partition) and `token` (sort), plus enabled TTL on `expiresAt`. Enable each Lambda to access its own table/bucket. The deployment runner needs Lambda/API Gateway configuration reads, DynamoDB table/TTL descriptions, S3 bucket access checks and Lambda code updates. Readiness checks describe storage resources but do not read or write application items/objects or prove the Lambda role can use them.
- Verify API Gateway stage integrations, Lambda invocation permissions and CORS for local development and the public site. Direct S3 browser uploads also need appropriate bucket CORS.
- Verify Production monitoring has the required permissions described below and confirm real data appears.

Branch protections remain optional: review PRs and check CI manually before merging. This setup does not require another person's review or prevent you from merging your own PR. GitHub does not allow authors to submit a formal approving review on their own PR; reviewing the changes and merging is the team's sign-off. Deployment jobs still depend on passing CI, even without branch protection. For environment configuration see [GitHub's environment documentation](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) and [GitHub's PR approval rules](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

Learner Lab credentials expire. Renew them before the run; this workflow cannot renew the university lab session. A deployment run is automatic while valid credentials and resource permissions remain available. Expired credentials are a setup failure, not evidence that the pipeline has completed successfully.

## Read-only readiness checkpoint

Run the read-only `test-aws.yml` workflow independently when checking AWS setup:

```sh
gh workflow run test-aws.yml --repo Schnitze1/Poco --ref main
```

This uses repository credentials and requires no GitHub environment settings access. It reads AWS identity, Lambda configuration, API stage targets, table schemas/TTL and bucket access/regions. It requires four different tables and buckets and writes a resource summary to the Actions run summary. It does not deploy, provision resources or change application data. The deployment workflow calls the same checks before packaging.

If it fails, fix the specific AWS configuration or permission reported and rerun this checkpoint. A passing readiness check verifies resource configuration and runner access; it does not replace live encode/decode, persistence or end-to-end acceptance tests.

## Testing and Staging acceptance

API/storage and browser acceptance are steps inside `deploy-environment.yml`, enabled only for Testing and Staging. Each job deploys the shared Lambda ZIP, verifies the deployed package/configuration and health, and then runs acceptance before the next environment can start. AWS readiness runs once before packaging; it is not repeated for each environment. Development and Production retain their deployment/configuration and health checks.

The acceptance step creates one fresh synthetic session in the selected API. It checks email redaction, API mappings, a directly queried DynamoDB item and its expiry, actual S3 archive content and decode restoration. The same job builds and serves the candidate frontend on the runner and runs Chromium against that API. It checks redaction, vault contents, session persistence after refresh, decode restoration and the visible unknown-token warning.

Cleanup runs on normal completion or test failure: it deletes that job's session through the API, checks its table items are gone and deletes only its archive object. Both API and browser checks reuse that session, so cleanup runs after both. A test or cleanup failure fails the environment job and prevents promotion.

To repeat a failed environment, rerun the relevant job from the **Deploy** run in GitHub Actions. This repeats its deployment and acceptance checks for that run's commit; it is not a read-only diagnostic. The old `run-api-tests` input on `test-aws.yml` has been removed; that workflow now has one responsibility: read-only readiness.

Browser evidence is uploaded as `browser-acceptance-test` or `browser-acceptance-staging` for seven days. It includes success/failure screenshots, preview logs and a Playwright trace. Download before expiry; inspect a trace locally from `web/` with:

```sh
npx playwright show-trace /path/to/trace.zip
```

The preview runs a production frontend build connected directly to the real stage API, so the browser checks also exercise CORS and network integration. Screenshots/traces contain synthetic test data. A failed browser assertion, page error or API error fails the job and stops promotion.

## Assignment coverage and remaining evidence

### Code coverage reports

Shared CI runs frontend tests with Vitest V8 coverage and backend tests with cargo-llvm-cov. Both jobs write coverage tables to the Actions summary and upload HTML and machine-readable reports as `frontend-coverage` and `backend-coverage`. These artifacts are retained for 30 days; download them for the report before they expire. This retention setting applies to coverage artifacts, not the existing seven-day browser, monitoring or Lambda artifacts.

Frontend scope includes all application TypeScript/TSX files under `web/src`, even if unimported by tests; test files and declarations are excluded. Backend scope is the Rust workspace with the tool's default dependency/generated/standalone-test exclusions. Inline Rust unit-test modules remain included, which must be stated when interpreting that percentage. The coverage jobs use code-level tests with in-memory backend storage and need no active Learner Lab.

Both jobs enforce a global minimum of 80% line coverage. Frontend coverage is checked by Vitest, while Rust coverage uses `cargo llvm-cov report --fail-under-lines 80`. Test, coverage and reporting failures block delivery, with generated artifacts retained for diagnosis. A local report is evidence of a local execution; use a successful Actions run as evidence that the CI configuration executed. Report frontend and backend percentages separately, with their scopes, rather than combining them or confusing passing-test counts with coverage.

The measured local baseline, scope limitations and suggested report wording are recorded in [COVERAGE.md](COVERAGE.md).

| Specification | Pipeline support | Evidence needed |
|---|---|---|
| Level 1: four environments | Separate Lambda/API stages and storage, validated before delivery | AWS configuration and isolation screenshots |
| Level 2: production instrumentation/monitoring | Automated Lambda Insights setup, metric ingestion checks and the Poco-Production CloudWatch dashboard | A successful monitoring run plus populated dashboard screenshots under real traffic |
| Level 3: automated unit, integration and end-to-end tests before production | Rust/Vitest CI plus live API/DynamoDB/S3 integration and Chromium acceptance gates in Testing/Staging | Successful cloud runs, browser screenshots/traces and public app/database verification |
| Level 4: automatic trigger-to-production workflow | A `main` push starts the full chain with no further branch merges | A visible feature change progressing through one successful run to the published website |

## Production monitoring

A dedicated job in `deploy.yml` verifies monitoring after Production backend deployment and before website publication. It no longer calls the multi-purpose AWS test workflow or repeats all four readiness checks. The old `configure-monitoring` input on `test-aws.yml` has been removed.

Production deployment configures the Insights layer before publishing the candidate, preserving unrelated layers and using revision checks. The monitoring job reads the numbered version selected by `live`, verifies its pinned layer and health, and updates only the `Poco-Production` CloudWatch dashboard. It does not change Lambda configuration or IAM. Missing metric samples or dashboard errors fail the monitoring job without rolling back a healthy application. Rerunning monitoring repeats these observations without redeploying code.

The workflow pins the AWS x86-64 [Lambda Insights extension](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versionsx86-64.html) for `us-east-1` (extension 1.0.776.0, layer version 66). It relies on the existing `LabRole` log permissions for `/aws/lambda-insights`, generates a few Production health requests and waits for actual CPU, memory, disk, network and HTTP-latency samples. It does not create or attach IAM policies. If the lab denies layer updates, monitoring logs, metric reads or dashboard creation, resolve the reported permission with the lab owner/instructor before claiming completion.

Open **CloudWatch → Dashboards → Poco-Production** in `us-east-1`. The dashboard covers requests/errors/throttles, execution duration, CPU time, memory, temporary-disk usage, received/sent bytes, API Gateway HTTP latency and HTTP errors. See [Lambda Insights metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-metrics-lambda-functions.html) for units. CPU time is measured in milliseconds; temporary-disk usage is bytes used rather than disk I/O throughput. These are the serverless equivalents available here and should be explained accurately in the presentation.

The application log group is `/aws/lambda/poco-pii-api-handler`; enhanced performance events go to `/aws/lambda-insights`. Save populated dashboard screenshots and the `production-monitoring-evidence` artifact for the final report. Metrics may be delayed: AWS documents up to 20 minutes for quiet functions. The check continues health traffic and allows a bounded ingestion window (30-minute job timeout). See [Insights troubleshooting](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-Troubleshooting.html). The artifact retains sample responses and dashboard JSON for seven days. The normal delivery workflow reuses monitoring verification after Production deployment and before website publication.

## Demonstration recording

1. Show the four runtime/storage environments and production dashboard; open the current public app.
2. Make a small visible UI change on a feature branch and show its PR CI results.
3. Merge the PR into `main`. Follow the resulting **Deploy** run through CI, preflight, package, Development, Testing, Staging, Production and Pages publication without manual environment promotions.
4. Show the single readiness gate and the Testing/Staging health, live API/storage integration and browser acceptance steps passed before production started. Open their screenshot/trace artifacts and show the same Lambda artifact/hash being reused.
5. Open the public website, show the visible change and demonstrate Encode → Vault → Decode. Show the final public-site check verifies the same commit.
6. Show fresh production metrics/logs and save screenshots, logs and test reports for the final report. If a failure is demonstrated, show that later stages are skipped.

The live API integration and Chromium acceptance tests verify the core encode/vault/decode flow and actual DynamoDB/S3 persistence using synthetic data. Browser coverage is currently desktop Chromium and the core text flow; it does not cover uploads, every UI action or other browsers. Manually demonstrate additional features and actual DynamoDB/S3 data as supplementary evidence.

The prepared workflows and local validation are not a substitute for this successful live demonstration. Run and verify the complete cloud pipeline before recording.
