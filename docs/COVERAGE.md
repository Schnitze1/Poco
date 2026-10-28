# Coverage reporting and local baseline

Coverage reporting and an 80% global line-coverage gate are configured in the shared CI workflow for each application. Tests run once with instrumentation, then the workflow creates coverage summaries and downloadable reports. Test failures, coverage below 80%, and reporting failures fail CI and block dependent delivery stages.

## Verified local baseline

The following results were measured locally on 28 October 2026. They are not evidence of a GitHub Actions execution or a deployed AWS test.

| Scope | Tests passed | Line coverage | Covered executable lines |
|---|---:|---:|---:|
| Frontend | 75 | 99.54% | 433 / 435 |
| Rust workspace | 120 | 81.77% | 2,583 / 3,159 |

Frontend coverage uses matching Vitest and V8-provider versions (5.0.5). All application TypeScript/TSX files under `web/src` are included, including unimported React components. Test files and type declarations are excluded. The expanded suite exercises real React components through user interactions, supported by focused API, PDF extraction, persistence and token-editing tests. API responses and PDF-parser boundaries are mocked in these local checks. The automated browser acceptance suite is separate and is not merged into this report.

Backend coverage uses cargo-llvm-cov 0.9.1 and the stable Rust toolchain. The local run used Rust 1.99.1 on Apple Silicon. Dependencies, generated files and standalone test/example files are excluded by the coverage tool. Existing inline unit-test modules remain included in the source-file totals, so 81.77% must not be described as production-code-only coverage. The new CLI and manual-redaction test files are excluded by the tool's existing rules. The CLI, Lambda handler and storage modules remain in scope even where coverage is low. Third-party native C/C++ libraries are not instrumented.

Both local line results exceed the enforced 80% threshold. Do not average the two percentages or describe the passing-test rate as code coverage. The scopes differ, and the whole-workspace result does not imply 80% coverage of every individual file or of live AWS operations. The CI runner uses Linux, so record its measured baseline separately if it differs from this local result.

The initial measurements were 12.32% frontend and 76.01% Rust workspace line coverage. The increase comes from additional behaviour checks rather than reduced source scope. CLI acceptance executes the real binary, while manual-redaction cases cover validation, token collisions and literal replacement. Frontend checks cover the principal screens, document operations, upload paths and error recovery. They also exposed a card-class inference issue, now fixed with Luhn validation, and the saved-workspace initialiser was changed to avoid accessing refs during render.

## Reproduce and view

From `web/`, run `npm run test:coverage` and open `coverage/index.html`. The same directory contains `coverage-summary.json` and `lcov.info`.

Backend commands are documented in [`pii-tool/README.md`](../pii-tool/README.md#code-coverage). The HTML report is `pii-tool/coverage/html/index.html`; JSON, LCOV and the CI text summary are saved beside the HTML directory. Keep `DYNAMODB_TABLE` and `S3_BUCKET` empty for code-level tests. No active Learner Lab is needed.

Local validation passed all 195 tests, frontend compilation, lint, coverage-report generation and workflow syntax/summary checks. Both gates pass at 80% and have negative checks using a temporary 100% threshold to verify that insufficient coverage returns a failure. The pushed branch's successful Actions run provides CI execution evidence; a code-level CI run does not deploy or verify AWS services.

## Evidence for the project report

After a successful CI run, capture the frontend and backend coverage tables in the Actions summary and retain the console test output. Download `frontend-coverage` and `backend-coverage`, open their HTML reports locally, and capture readable summary and file-detail views. Both coverage artifacts are retained for 30 days.

Suggested report wording:

> Coverage reporting and minimum line-coverage gates were added to the frontend and Rust test suites. Local execution recorded 99.54% frontend line coverage and 81.77% Rust workspace line coverage, with all 75 frontend and 120 backend tests passing. The frontend result includes unimported application files, while the Rust source totals include existing inline unit-test modules. Both results exceed the configured 80% minimum, and CI blocks a candidate if either application falls below this threshold. Coverage summaries and downloadable reports provide the supporting evidence, with live API and browser acceptance assessed separately.

The previous report statement that coverage is not configured can now be replaced with the measured results and enforced gates. Preserve the distinction between local evidence, CI execution and deployed acceptance. Coverage instrumentation can change release duration, so historical release timings should not be treated as measurements of the new CI configuration.
