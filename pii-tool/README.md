# PII Anonymisation Tool POC

Workspace for the Rust engine, CLI, and Lambda handler.  
Project overview and deploy docs: **[../README.md](../README.md)** · **[../docs/ENVIRONMENTS.md](../docs/ENVIRONMENTS.md)** · **[../docs/API.md](../docs/API.md)**

## How to run

```bash
cargo test --workspace
cargo run -p pii-cli
```

## Code coverage

Install the pinned coverage tool and the LLVM tools for the active Rust toolchain:

```sh
cargo install cargo-llvm-cov --locked --version 0.9.1
rustup component add llvm-tools-preview
```

From `pii-tool/`, run the workspace tests once and generate reports from that execution:

```sh
cargo llvm-cov clean --workspace
DYNAMODB_TABLE= S3_BUCKET= cargo llvm-cov --locked --workspace --no-report -- --test-threads=1
cargo llvm-cov report --html --output-dir coverage
cargo llvm-cov report --json --summary-only --output-path coverage/coverage-summary.json
cargo llvm-cov report --lcov --output-path coverage/lcov.info
cargo llvm-cov report --fail-under-lines 80
```

Clear `DYNAMODB_TABLE` and `S3_BUCKET` in the test environment to use the same in-memory storage as CI. These coverage tests require no active Learner Lab. They do not measure the live API, deployed DynamoDB/S3 operations or browser acceptance.

CI installs the same coverage version, generates HTML/JSON/LCOV and text reports, publishes a job summary, and uploads `backend-coverage` for 30 days. Test failures still fail CI; report generation is attempted afterwards so diagnostic evidence is retained where possible. Global workspace line coverage below 80% fails the report step and blocks delivery. The threshold is checked after HTML/JSON/LCOV generation so those diagnostic reports remain available on a coverage failure.

CLI acceptance launches the real binary in temporary directories and exercises text/document input, encoding, decoding, mapping reuse, clearing, validation, EOF and output failures. Manual-redaction tests cover invalid/duplicate rules, Unicode boundaries, token collisions and corrected source values. The additional Rust test files use the coverage tool's standard test-file exclusions, so their own lines do not inflate the measured application totals.

The scope is the Rust workspace. cargo-llvm-cov excludes dependency/generated paths and standalone test/example files by default. Inline unit-test modules in application source files remain included with the stable Rust toolchain, so this baseline must not be described as production-code-only coverage. Third-party native C/C++ dependencies are not instrumented. See the [cargo-llvm-cov documentation](https://github.com/taiki-e/cargo-llvm-cov) for the default exclusions.

## Algorithm Summary (v0.1.0)

Deterministic, rules-based PII detection and reversible tokenisation.

**Verified metrics (gold suite, 54 entities + 17 traps):**
- Recall: 98.1% (53/54)
- Precision: 100% (52/52)
- Exact-category correctness: 100%
- Trap leakage: 0
- Token collisions: 0 (asserted on all four input paths)

**Known limitations (documented, not bugs):**
- No BTC detector — only ETH addresses detected
- PDF extraction loses CJK glyphs (张伟 → ❍❍) — CJK only works on TXT/DOCX
- PDF line reordering preserves token numbers but may reorder lines in output
- Scanned/image-only PDFs return NoTextLayer and are out of scope
- Card expiry/CVV intentionally not redacted
- Product codes, versions, ticket IDs intentionally not redacted

### Person-name detection (NER)

Free-text person names (e.g. `Priya Patel`, `Michael Chen`) are only partially
reliable. The `gaze-pii` NER / name recognizers miss many bare names and can
under- or over-capture spans around titles and role phrases. This is a known
limitation of the underlying detection model.

Until NER coverage improves, the Vault feature (manual token entry) is the
intended workaround: operators can register a token mapping for any name the
automatic pipeline missed so encode/decode still round-trips that value.

Do not treat “all person names in the document were redacted” as a guarantee of
this POC; verify with `View current session mapping` and add missing names via
the Vault when needed.

