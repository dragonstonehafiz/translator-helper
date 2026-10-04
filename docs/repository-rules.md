# Repository Rules

Coding rules, verification expectations, and safety/permission boundaries that apply to virtually every task in this repository. Component behavior, endpoint details, task-chain wiring, and page-specific conventions belong in the references linked from [`README.md`](README.md), not here.

## Coding rules

### Backend

- use type hints and a concise, single-line docstring on every Python function, class, and method — describe purpose or contract, not implementation history
- return every JSON response through the helpers in `utils/api_response.py`; put payload fields under `data`, never at the root
- never swallow errors silently — tasks raise on failure and `TaskOrchestrator` records the error; routes return failures as error envelopes
- import runtime paths from `utils/config.py` (`CONFIG_DIR`, `LIBRARY_DIR`, `OUTPUTS_DIR`, `LOGS_DIR`) rather than rebuilding them
- keep `.method()` on the same line as its object — no chained calls starting on a new line

### Frontend

- use explicit TypeScript types; avoid `any` (the project compiles with `strict` and `strictTemplates`)
- standalone components only, no NgModules
- keep styles in the component's colocated `.scss` file; no inline styles; never redefine the global classes from `src/styles.scss`
- make every backend call through `ApiService`; never inject `HttpClient` in a component
- use `ErrorDialogService` instead of `alert(...)` and `ConfirmationService` instead of `confirm(...)`; every Observable `error:` callback shows the error dialog
- use `WORKFLOW_TYPES` and `LANGUAGE_OPTIONS` rather than hardcoding workflow IDs or language lists
- reuse the shared components in `src/app/components/` instead of duplicating their markup
- no `console.log` in frontend code; keep emoji to a minimum — prefer text labels or SVG icons

### Both

- no backward-compat shims during refactors — update call sites directly
- no new heavy dependencies without approval
- no unrelated refactoring — keep changes scoped to the task
- use existing colors, global classes, and named constants; no new magic numbers or one-off colors

## Verification

There is no automated test suite; the user tests manually in the browser. Run the file-scoped checks in [`verification.md`](references/verification.md) against every changed file. A full frontend build (`npm run build`) requires explicit approval — it is not part of the default verification loop.

## Safety and permissions

Allowed without asking:
- read files, list files, search
- syntax/type check single files
- run the isolated task harnesses under `backend/tests/` when the task calls for it

Ask first:
- `uv pip install` / `npm install` new packages
- deleting files, including anything under `backend/files/` (settings and API keys, library data, generated subtitles, logs)
- full project builds
- starting the backend or frontend server

Never:
- stage files (`git add`) or create commits
- run `git push`
- publish issues or documentation remotely
- treat drafting or planning as authorization to implement
- print or copy API keys from `backend/files/config/*.json`

## Scope control

When a request is ambiguous or would require a large speculative change, ask a clarifying question or propose a short plan before proceeding. Do not push wide refactors without confirmation.
