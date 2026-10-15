# Poco web app

React + TypeScript + Vite frontend. Run these commands from `web/`:

```sh
npm ci
npm run dev
```

`npm run build` checks TypeScript and creates `dist/`. `npm run preview` serves that build locally. `npm run lint` runs Oxlint.

## Validation

```sh
npm run test:ci
npm run lint
npm run build
```

`npm run test:ci` runs the colocated Vitest tests once using jsdom. It uses the plain-text TAP reporter: each test has an `ok` or `not ok` result without decorative status symbols. GitHub Actions captures this output under **frontend-checks → Run frontend tests**; there is currently no separate HTML report or coverage report. `npm test` starts watch mode. The persistence tests cover empty storage, workspace restoration, clearing an old session, and malformed stored JSON.

The shared `.github/workflows/ci.yml` runs locked Rust tests plus frontend tests, lint and build on implementation-branch pushes and pull requests. These checks use in-memory backend storage and do not prove live AWS behaviour.

Merging into `develop` starts automatic delivery through Development, Testing, Staging and Production. The workflow builds one Lambda ZIP and reuses it across all environments. Each deployment must pass package/configuration and API health checks before the next environment starts. Testing and Staging also require live API/storage integration and Chromium browser acceptance to pass before promotion. Pipeline commands stay inside YAML workflows.

CI prepares the production Pages artifact with `VITE_API_STAGE=prod` and commit metadata. After production backend health and monitoring checks pass, the workflow publishes that artifact and checks the public website is reachable and its release metadata matches the workflow commit.

The Testing and Staging deployment jobs run the API/storage and browser checks as steps before allowing promotion. They test encode/decode against the deployed APIs, read the synthetic mapping directly from DynamoDB and compare the actual S3 archive with the redacted output. Chromium then checks Encode → Vault → refresh → Decode and the unknown-token warning against the same API. Cleanup deletes the job's session mappings and archive after both API and browser checks, verifying the table has no remaining items for that session. Screenshots/traces are saved as artifacts. Tests stay inline in YAML; no separate E2E spec/config file is required. Coverage is the core text flow in desktop Chromium; uploads and other browsers remain outside this suite.

Branch protections are optional. Missing GitHub environments are created automatically without reviewers or environment secrets; the workflow uses repository AWS secrets. Existing restrictions on `dev`, `testing`, `staging`, `production` and `github-pages` must allow `develop` without approval pauses. Only changing those restrictions requires owner/admin settings access. The Pages custom domain is configured in GitHub settings. See [`../docs/ENVIRONMENTS.md`](../docs/ENVIRONMENTS.md) for prerequisites and monitoring requirements.

## API configuration

The app calls the Rust API through AWS API Gateway. By default it uses the `/dev` stage. Run against another stage from `web/` with:

```sh
VITE_API_STAGE=test npm run dev
```

`VITE_API_BASE` overrides the entire API base URL. These values are read when Vite starts or builds; restart or rebuild after changing them. The frontend's **API dev/test/staging/prod** status comes from `/health`.

The API must allow the frontend origin and its request methods through CORS. Running Vite locally does not start a local Rust backend. Use a fresh browser workspace when switching environments; local storage keys are not separated by API stage.

## Try the demo

1. In **Encode**, choose **Use example**, then **Encode**. Tokens are highlighted in the output.
2. Choose **Inspect PII** or **Vault** to filter, edit, add, or delete mappings. **Reset vault** clears the selected document's mappings.
3. In **Decode**, choose **Use example**, then **Decode**. Known tokens restore from the selected document's vault; `[Person_99]` intentionally stays unknown.
4. **New document** creates separate document fields and a local vault view. Documents currently share one backend session ID.
5. **Upload file** accepts TXT/MD/PDF/DOCX files up to 25 MB. TXT/MD and PDF extraction run in the browser; DOCX extraction uses the API and is also subject to API payload limits. The theme button switches between dark and light.

Encoding replaces the selected document's local mapping snapshot with the API response. Vault edits are sent to the API when a session exists. Decode uses mappings from the backend session.

Inputs, outputs, mappings, view selection, and the session ID are saved in browser local storage and restored after refresh. The backend uses DynamoDB when `DYNAMODB_TABLE` is configured, with an in-memory fallback otherwise. `src/mocks/demo.ts` supplies example text only; detection is performed by the API. LLM calls remain outside this app.

See `src/api.ts` for the implemented API calls and `../docs/API.md` for the API documentation.

## Git

Commit source, configuration, `package.json`, and `package-lock.json`. Ignore `node_modules/`, `dist/`, local environment files, logs, coverage, and TypeScript build metadata. `.env.example` can be committed with placeholder values only.
