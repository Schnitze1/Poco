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
| `docs/ENVIRONMENTS.md` | dev / test / staging / prod deploy map |
| `.github/workflows/deploy.yml` | CI: tests → AL2023 Lambda build → deploy → smoke |
| `.github/workflows/ci.yml` | Shared backend tests and frontend tests/lint/build |

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

| Trigger | Environment | Lambda | API stage |
|---|---|---|---|
| push `develop` | dev | `poco-pii-api-handler-dev` | `/dev` |
| push `test/qa` | test | `poco-pii-api-handler-test` | `/test` |
| push `release/**` | staging | `poco-pii-api-handler-staging` | `/staging` |
| push `main` | prod | `poco-pii-api-handler` | `/prod` |

**Do not push `main` until production is deliberately ready.**

The workflow builds and verifies the Lambda package before entering the deployment environment. On `main`, the production frontend is published only after the Lambda deployment and environment health check succeed. Other branches do not publish Pages. Deployment runs are serialized per target, including all release branches sharing staging.

The owner must configure required CI checks and reviewers for the `production` and `github-pages` environments before merging production routing. Workflow environment references alone do not enforce approval.

AWS Academy Learner Lab constraints: `us-east-1` only, `LabRole` only (no custom IAM/OIDC), static credentials in GitHub secrets (refresh ~every 4 hours).

More detail: [`docs/ENVIRONMENTS.md`](docs/ENVIRONMENTS.md).

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
