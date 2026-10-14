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

`npm run test:ci` runs the colocated Vitest tests once using jsdom. `npm test` starts watch mode. The persistence tests cover empty storage, workspace restoration, clearing an old session, and malformed stored JSON.

The shared `.github/workflows/ci.yml` runs `backend-tests` and `frontend-checks` on implementation-branch pushes and every pull request targeting `develop`, `main`, `test/qa`, or `release/**`. PR checks have no path filters, so documentation-only changes still receive both results. Backend tests use in-memory sessions with AWS storage disabled; frontend checks run tests, lint, and a production build. These checks do not verify live AWS behaviour.

The `Deploy` workflow calls the same CI before packaging and deploying Lambda. On `main`, CI builds the frontend with `VITE_API_STAGE=prod` and uploads a Pages artifact. After the production Lambda update and health check succeed, the `publish-web` job in `deploy.yml` publishes that validated artifact through the `github-pages` environment. Dev, test, and staging deployments do not publish the website. The `littlepoco.me` domain remains configured in GitHub Pages settings; Actions-based publishing does not require a CNAME file.

Branch protections are optional; the team reviews PRs and waits for CI manually before merging. The repository owner must configure the `production` and `github-pages` environment reviewers before production promotion if an enforced release approval stage is required. See [`../docs/ENVIRONMENTS.md`](../docs/ENVIRONMENTS.md) for the deployment map and owner setup. Referencing an environment in a workflow does not configure its approval rules.

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
