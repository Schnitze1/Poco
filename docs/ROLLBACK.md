# Automatic backend recovery

The versioned deployment workflow automatically configures Lambda versions, a `live` alias, a narrowly scoped API Gateway invocation permission and the selected API stage's `lambdaName` variable. No manual alias/routing setup or CodeDeploy application is required. Existing functions, API stages, tables, buckets and LabRole must already exist.

Keep the Learner Lab active and the GitHub repository's `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` secrets current. Environment secrets, if present, must use the same intended account and remain valid too. The workflow cannot renew the university lab session or change its IAM restrictions.

## Release behaviour

Each environment uses its existing Lambda function. The first versioned deployment checks the API integration and working baseline, retains a numbered snapshot of the serving code/configuration, creates `live` if necessary and switches only that stage's variable from the unqualified function to `function:live`. Later deployments reuse this routing. An unrelated existing alias, weighted routing, unexpected integration or unhealthy baseline stops the deployment for investigation.

The runner updates `$LATEST` while `live` continues serving the previous immutable version. It verifies the ZIP hash and environment configuration, publishes a candidate snapshot and directly invokes that numbered version's health endpoint. Only then does it move `live` to the candidate and verify the public stage API. Testing and Staging subsequently run the existing API, DynamoDB, S3 and Chromium acceptance checks.

Production's Lambda Insights layer is configured before its candidate version is published. Consequently, the code and instrumentation configuration are included in the same version snapshot. The later monitoring job verifies the accepted version, collects metrics and updates the dashboard without changing Lambda configuration.

If deployment or verification fails within the environment job, a separate recovery step restores `live` to the retained previous version and verifies its configuration fingerprint, routing and API health. A successful recovery leaves the original deployment job failed and prevents promotion to subsequent environments. If the candidate was never activated, recovery verifies that the previous version still serves traffic.

Alias and function updates use AWS revision checks. Recovery refuses to overwrite an alias/routing change it cannot identify as belonging to this attempt. Release state is written before activation, so recovery can handle an applied alias update whose response was lost. Saved JSON contains version numbers, hashes, configuration digests, ownership/revision identifiers and event times; environment variable values are not exported.

The workflows call `scripts/lambda_release.py` using Python's standard library and the runner's AWS CLI. Offline regression tests run in shared CI:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

## AWS permissions

In addition to existing deployment permissions, the runner needs `lambda:GetAlias`, `CreateAlias`, `UpdateAlias`, `PublishVersion`, `ListVersionsByFunction`, `GetPolicy`, `AddPermission` and `InvokeFunction`; it also needs the existing Lambda configuration/code operations and API Gateway read/update-stage access. The invocation permission is attached to `live` and restricted to the account, REST API and selected stage. No IAM role or policy is created or modified.

The Testing demonstration exercises these operations against the real lab role. A successful Testing result verifies that role's access for Testing; resource-scoped restrictions in another environment can still differ. If AWS returns `AccessDeniedException`, use the reported operation to identify the lab restriction rather than creating a new IAM role or blindly widening policies. Production setup occurs on its first deployment using this workflow.

## Controlled Testing demonstration

The **Testing rollback demonstration** workflow shares the `poco-delivery` concurrency group and waits for an active deployment to finish. It is hard-coded to Testing and has no Production selector. Its initial feature-branch push trigger allows verification before merging the new workflow; after merging it can be dispatched from Actions.

The demonstration snapshots the healthy Testing application, changes only Lambda description metadata to publish a distinct candidate, activates it, verifies health and deliberately raises a verification failure. It then runs the same recovery method used by deployment jobs. It verifies the previous version and health, restores the original Testing routing and description, and saves `testing-rollback-demonstration` evidence for 30 days. Baseline/candidate versions and the unused alias may remain. No application code, tables, buckets or Production resources are changed by the demonstration.

A green demonstration means the injected failure and recovery/cleanup were verified. It is not evidence that corrupt application code was deployed or that every failure type was tested. A real failed deployment remains red even if its recovery step succeeds. Record the actual run result before claiming live rollback in the report.

Live Testing verification succeeded on 28 October 2026: [successful recovery demonstration](https://github.com/Schnitze1/Poco/actions/runs/40626518227). The artifact records candidate activation, the injected verification failure, restoration of the previous version, verified API health and restoration of the original Testing routing/metadata. This proves that the current lab credentials allowed the required Testing operations. Production integration still needs its first deployment after merging this change.

Initial live checks caught stale revision identifiers after alias permission setup and version publication. The helper now refreshes the alias revision after setup, verifies the candidate workspace after publication and checks the complete owned configuration fingerprint before metadata cleanup. These checks allowed recovery without overwriting unrelated configuration. The earlier attempts kept the previous application healthy; the successful run also verified cleanup.

## Limits and manual recovery

Recovery applies to the failing backend environment. A failure in Staging does not revert an already accepted Development or Testing deployment. Monitoring sample/dashboard failures after a healthy Production deployment do not revert that application. The website is published separately through GitHub Pages; automatic frontend rollback is not implemented. DynamoDB/S3 writes, schema changes and external side effects are not reversed by switching Lambda versions.

The runner and valid AWS credentials must remain available. A force cancellation, job timeout, runner loss or expired lab session can prevent the recovery step from executing. The workflow does not claim guaranteed recovery in those cases. Retained versions consume Lambda storage; this change deliberately does not delete history automatically.

For a failed environment, inspect **Restore the previous backend version** and the `backend-release-{stage}` artifact first. Download its JSON state and use matching current credentials in the same AWS account. From the checkout for that workflow run, retry the guarded recovery command, for example:

```sh
python3 scripts/lambda_release.py recover --stage test --state /path/to/test.json
```

This command changes traffic and verifies the retained baseline. It rejects a mismatched stage/function and unexpected concurrent changes. Do not rerun an old recovery command after an unrelated later release; inspect the current alias and saved revisions first. Rerunning an entire deployment job instead starts a fresh deployment attempt for that run's code.

## Report evidence

Place the following evidence beside the Level 4 recovery explanation, with longer logs in an appendix. Use the real run identifier and capture time in captions, without making the narrative dependent on one particular commit.

**[INSERT SCREENSHOT: The Testing rollback demonstration Actions steps showing candidate activation, the deliberate verification failure, recovery and successful cleanup.]**

*Figure R1. A controlled verification failure in Testing triggers restoration of the retained backend version. Production is excluded from the demonstration.*

**[INSERT FORMATTED OUTPUT: Relevant demonstration log lines showing the previous/candidate version numbers, restored alias and verified routing/health, followed by the artifact's event sequence.]**

*Listing R1. Execution evidence connecting candidate activation to verified recovery. Explain that the application code was unchanged and the failure was deliberately injected.*

**[INSERT SCREENSHOT: AWS Lambda → Testing function → Aliases → live, showing the retained version after recovery; show the Versions tab or artifact for the distinct candidate.]**

*Figure R2. The Testing live alias selects the retained previous version after recovery. If the original route was unqualified, the demonstration also restores that original stage routing.*

**[INSERT SCREENSHOT: The Testing API `/test/health` returning status `ok` and environment `test` after recovery, with a visible capture time.]**

*Figure R3. Post-recovery Testing API availability and environment identity. This health result does not replace the separate persistence and browser acceptance evidence.*

**[INSERT SCREENSHOT AFTER MERGING: A future deployment showing a numbered live version and the environment's backend-release artifact. Only claim automatic recovery of an actual failed deployment if that run demonstrates it.]**

*Figure R4. Versioned backend deployment configuration applied by the integrated delivery workflow.*
