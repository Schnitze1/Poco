# Poco — PII Anonymisation Tool

Reversible PII detection and tokenisation for safe use of documents with LLMs.

Detect PII in text (and PDF/DOCX uploads), replace it with readable tokens such as `[Email_1]` and `[Name_1]`, send the redacted text to an LLM, then restore the original values. Built with a Rust core, CLI, and AWS Lambda HTTP API.

---

## Repository layout

| Path | What it is |
|---|---|
| `pii-tool/` | Cargo workspace (core engine, CLI, Lambda handler) |
| `web/` | React/TypeScript frontend with API integration and persistence tests |
| `pii-tool/crates/core` | `pii-core` — extract, detect, encode/decode (gold-tested) |
| `pii-tool/crates/cli` | Interactive CLI (`cargo run -p pii-cli`) |
| `pii-tool/crates/lambda` | `poco-lambda` — AWS Lambda HTTP API |
| `pii-tool/test_data/` | PDF/DOCX/TXT fixtures for the gold suite |
| `docs/API.md` | HTTP API contract for the website client |
| `docs/ENVIRONMENTS.md` | Environment setup, automatic delivery and demo checklist |
| `.github/workflows/deploy.yml` | Automatic delivery from develop through all environments |
| `.github/workflows/ci.yml` | Shared backend tests and frontend tests/lint/build |
| `.github/workflows/deploy-environment.yml` | Shared Lambda deployment, package/configuration checks and health checks |
| `.github/workflows/test-aws.yml` | AWS readiness, Testing/Staging API tests and Production monitoring setup |

---

## Quick start (local)

```bash
cd pii-tool
cargo test --workspace          # full suite including gold metrics
cargo run -p pii-cli            # interactive encode/decode
```

**Algorithm metrics** (54-entity gold suite + 17 traps): recall 53/54 (98.1%), precision 100%, exact-category 100%, trap leakage 0. Details: `pii-tool/README.md`.

---

## Architecture

```text
file / paste text
    → extract (.pdf / .docx / .txt)
    → Vault::encode  (gaze-pii + rules)
    → redactedText + mappings[]
    → LLM (out of band)
    → Vault::decode  (session / mappings)
    → restored text
```

- Detection is **rules-based** (gaze-pii + `poc_extra.toml`), not a neural NER.
- Tokens are reversible; mappings must never be written to disk in the Lambda.
- The website extracts TXT/MD/PDF in the browser and uses the API for DOCX extraction. The backend also supports uploaded file bytes and S3 keys.

---

## Deployment

Merging a feature PR into `develop` starts the complete pipeline:

```text
feature/* → PR → develop
                    ↓
          CI tests, lint and build
                    ↓
        Verify environment isolation
                    ↓
          Build one Lambda package
                    ↓
       Development → Testing → Staging
                    ↓
            Production backend
                    ↓
          Verify production monitoring
                    ↓
          Publish production website
                    ↓
         Verify the website and release metadata
```

Every environment must pass package/configuration and API health checks before the next deployment starts. Testing and Staging also run live encode/decode and DynamoDB/S3 integration tests before promotion. The same Lambda ZIP is reused throughout. Failed checks stop promotion; failure after publication reports a failed release and does not automatically roll back.

`develop` is the deployment source. The new workflow does not deploy independently from `test/qa`, `release/**` or `main`, and automatic delivery does not merge code into those branches. Branches retaining older workflows still have their previous behaviour. Branch protections remain optional; the team reviews PRs before merging into `develop`.

Complete the cloud setup and verify any existing GitHub environment restrictions before merging this workflow into `develop`: that merge will start automatic delivery to production. Missing GitHub environments are created automatically when referenced; manual environment setup is optional. All deployment environments, including `github-pages`, must allow `develop` without required reviewers. The production website uses the existing Pages custom domain `littlepoco.me`.

AWS Academy Learner Lab uses `us-east-1`, the existing `LabRole`, and temporary credentials in GitHub secrets. Credentials must be valid for the entire run and renewed when they expire.

Live API/storage integration tests run in Testing and Staging. Automated browser end-to-end acceptance tests remain required for the project specification and are not currently included.

Production monitoring uses Lambda Insights and the `Poco-Production` CloudWatch dashboard. The existing AWS workflow can configure it before merging; delivery verifies it again before website publication.

Setup, monitoring requirements and recording steps: [`docs/ENVIRONMENTS.md`](docs/ENVIRONMENTS.md).

---

## API

Base (dev): `https://6xz841x652.execute-api.us-east-1.amazonaws.com/dev`

| Method | Path | Implemented behaviour |
|---|---|---|
| GET | `/health` | Liveness and environment identity |
| POST | `/encode` | `{ "text": "..." }` → session ID, redacted text and mappings |
| POST | `/decode` | `{ "sessionId": "...", "text": "..." }` → restored text and unknown tokens |

Full contract: [`docs/API.md`](docs/API.md).

---

## Session / persistence (current)

Encode creates a **new vault per request** and writes mappings under a session ID. With `DYNAMODB_TABLE` configured, encode/decode and vault edits use DynamoDB; without it, sessions use process memory. The frontend also stores its workspace and session ID in browser local storage.

`S3_BUCKET` enables optional upload/redacted-text storage. Redacted-text archiving is best effort, so encode success alone does not prove an S3 write succeeded. Verify the live resources and encode/decode flow for each environment before the demonstration.

---

## Known limitations

- Bare person names (no title/cue) are unreliable — Vault manual mapping is the workaround  
- PDF extract: CJK glyphs may be lost; line order may not match the logical document  
- Scanned/image-only PDFs are out of scope (`NoTextLayer`)  
- Card expiry/CVV and product codes/versions are intentionally not redacted  
- No BTC detector (ETH addresses are detected)

---

## Development

```bash
cd pii-tool
cargo test --workspace
cargo test -p pii-core --test gold_suite -- --nocapture   # print metrics
```

Lambda is built in CI inside `amazonlinux:2023` (glibc 2.34) with a small `__isoc23_str*` stub for ONNX Runtime. Do not build the deploy zip on a newer host glibc.

Tag: **`v0.2.0`** (algorithm complete + CI deploy green).
