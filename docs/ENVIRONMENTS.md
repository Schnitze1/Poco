# Environments and deployment

The repository targets AWS Academy Learner Lab resources in `us-east-1`. The workflows update existing Lambda functions; they do not provision API Gateway, DynamoDB, S3, IAM, or Lambda configuration. The table below describes workflow routing, not proof that every cloud environment is currently operational.

One API Gateway (`poco-pii-api`, ID `6xz841x652`) serves separate stages. Verify that each stage's `lambdaName` variable and invoke permissions target the intended Lambda.

| Branch | API stage | Lambda | GitHub deployment environment |
|---|---|---|---|
| `develop` | `/dev` | `poco-pii-api-handler-dev` | `dev` |
| `test/qa` | `/test` | `poco-pii-api-handler-test` | `test` |
| `release/**` | `/staging` | `poco-pii-api-handler-staging` | `staging` |
| `main` | `/prod` | `poco-pii-api-handler` | `production` |

API base: `https://6xz841x652.execute-api.us-east-1.amazonaws.com/{stage}`.

Implementation branches, including `test/frontend-tests`, run CI but do not automatically deploy. Use `feature/*` for new implementation work. A manual `Deploy` run on an unsupported branch or tag fails during target resolution before packaging or accessing AWS credentials.

## Delivery flow

Promote a reviewed candidate through `develop` → `test/qa` → `release/<version>` → `main`. These promotions are team decisions, not automatic transitions between environments. Create a new release candidate rather than assuming an old release branch contains the latest reviewed code.

The `Deploy` workflow (`.github/workflows/deploy.yml`) runs on pushes to delivery branches and supports manual dispatch:

1. Resolve and validate the branch's target directly in the YAML workflow.
2. Call the shared CI: locked Rust workspace tests, frontend tests, lint, and build.
3. Build Lambda in `amazonlinux:2023`, verify the `bootstrap.zip` binary, and upload the verified package as a workflow artifact.
4. Enter the target GitHub environment and wait for any configured protection rules. Download the verified package, configure AWS credentials, update Lambda, and wait for the update to finish.
5. Request `/health`, requiring HTTP 200, `status: ok`, and the expected API environment.
6. On `main` only, run the `publish-web` job to publish the validated production frontend artifact through `github-pages`.

CI embeds the matching API stage in its frontend build. Only the `main` build uploads a Pages artifact, using `VITE_API_STAGE=prod`. Website publication follows successful production backend deployment and health verification in the same `deploy.yml` run. Branch routing, Lambda build commands, and Pages publication are contained in the YAML workflows.

The production website uses the existing `littlepoco.me` domain configured in GitHub Pages settings and DNS. Actions-based publishing does not require a CNAME file.

CI and deployment jobs use Ubuntu 24.04 runners; the Lambda release binary is built inside Amazon Linux 2023 to match its runtime. Each environment builds from the candidate's locked dependencies rather than promoting one shared binary across environments.

Deployment workflow concurrency prevents overlapping runs for the same target. All `release/**` branches share the staging concurrency group. Active deployment runs are not canceled by a newer push. GitHub may replace a pending run with a newer pending run; concurrency is not a promise to deploy every queued commit.

## Owner setup before production promotion

Configure these GitHub environments in repository **Settings → Environments**:

| Environment | Allowed deployment branches | Review requirement |
|---|---|---|
| `dev` | `develop` | Team choice |
| `test` | `test/qa` | Team choice |
| `staging` | `release/**` | Team choice; recommended for release sign-off |
| `production` | `main` | Required reviewer; prevent self-review |
| `github-pages` | `main` | Required reviewer; prevent self-review |

The backend and Pages jobs enter different environments, so production may involve two approvals. The verified Lambda package is available before the backend approval job starts.

Referencing an environment in YAML does not configure required reviewers. GitHub can create an unconfigured environment when a workflow first references it. The owner must set reviewers and branch policies before the production workflow is merged and used.

Protect delivery branches with PR review and the shared CI results. Select the actual `backend-tests` and `frontend-checks` check names shown on a PR; do not require the removed `Frontend Tests` workflow. PR validation has no path filters, so documentation-only changes also receive these results.

See GitHub's [environment setup](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) and [concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

## AWS prerequisites

Expected Lambda configuration:

- Runtime `provided.al2023`, handler `bootstrap`, architecture `x86_64`.
- Learner Lab `LabRole`; verify its existing access to each environment's resources.
- Memory/timeout as required by the application; the prior setup used 512 MB / 30 seconds.
- `ENVIRONMENT` matching `dev`, `test`, `staging`, or `prod`.
- `DYNAMODB_TABLE` pointing to that environment's session table; the API guide uses `poco-pii-sessions-{stage}` names. Verify actual table names rather than assuming they exist.
- `S3_BUCKET` pointing to that environment's document bucket when storage/upload features are used.
- `RUST_LOG=info` and `LD_LIBRARY_PATH=/var/task` as appropriate for the packaged runtime.

Verify DynamoDB partition/sort keys (`sessionId`, `token`) and TTL configuration for `expiresAt`. API Gateway must route to the correct Lambda and support the frontend origin/methods through CORS. Direct browser uploads also need suitable S3 CORS configuration.

The AWS deployment job reads `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` from GitHub secrets and uses `us-east-1`. Existing repository secrets can be used; environment secrets override secrets of the same name. Refresh expired Learner Lab credentials before deployment. CI tests do not use these secrets or live AWS storage.

## Verification before recording

For each environment:

1. Verify the branch, workflow commit, Lambda target, and resource configuration.
2. Confirm `/health` returns the expected environment.
3. Encode synthetic text into a fresh session, retrieve its mappings, and decode it back to the original text.
4. Find that session in the intended DynamoDB table. Local/in-memory tests do not prove deployed persistence.
5. Verify actual S3 objects if demonstrating uploads or redacted-text storage; archive errors are non-fatal to encode.
6. Inspect the corresponding CloudWatch Lambda log group and available monitoring. The production group is `/aws/lambda/poco-pii-api-handler`; other environments have their Lambda name suffix.
7. For production, confirm the published browser calls `/prod` and the domain serves the intended frontend.

Example health check (replace `dev` with the stage under review):

```sh
curl --fail --silent --show-error \
  https://6xz841x652.execute-api.us-east-1.amazonaws.com/dev/health
```

The automated smoke check currently verifies liveness and environment identity. Full encode/decode and storage verification still needs the live acceptance checks above; a green health check alone is insufficient.
