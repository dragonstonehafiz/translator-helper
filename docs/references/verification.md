# Verification and Implementation Patterns

## Purpose

Commands to run when checking work, and recurring patterns for extending the codebase (new endpoint, new task, new page). Layer-specific behavior lives in [`architecture.md`](architecture.md), [`tasks.md`](tasks.md), [`api.md`](api.md), and [`frontend.md`](frontend.md) — this file is about *how to check* changes, not what the layers contain.

## Contents

- [Git restrictions](#git-restrictions)
- [Verification principles](#verification-principles)
- [Backend verification](#backend-verification)
- [Frontend verification](#frontend-verification)
- [Documentation verification](#documentation-verification)
- [Adding a backend endpoint](#adding-a-backend-endpoint)
- [Adding a task](#adding-a-task)
- [Adding a frontend page](#adding-a-frontend-page)
- [Layer-specific checks](#layer-specific-checks)

## Git restrictions

The agent never runs `git add`, `git commit`, `git push`, or anything else that stages, commits, or uploads changes. Verification means running local checks only.

## Verification principles

- There is no automated test suite and no linter configuration. The user verifies behavior manually in the browser with both servers running; say which flows to try rather than claiming behavior is verified.
- Prefer file-scoped checks. A full frontend build (`npm run build`) requires explicit approval.
- Don't start the backend or frontend server — the user normally has both running already (`reload=True` and `ng serve` pick up changes).
- Match the check to the layer touched; a docs-only change needs neither backend nor frontend checks.
- Current code is authoritative. If a check contradicts a reference, trust the check and correct the reference.

## Backend verification

Use the `backend/.venv` interpreter, not a global `python`. No type checker or test runner is installed in the venv.

```bash
cd backend
.venv/Scripts/python.exe -m py_compile routes/translate.py     # Windows; syntax-check every changed .py file
.venv/bin/python -m py_compile routes/translate.py              # macOS/Linux
.venv/Scripts/python.exe -c "import server"                     # import check; triggers no model load (lifespan doesn't run)
```

`backend/tests/` holds standalone CLI harnesses for running one task in isolation, not tests. They make real LLM calls, so run one only when the task calls for it. Each script's header shows how to run it, e.g.:

```bash
python tests\run_plan_translation_batches.py --file-path ..\data\sample\sample_sub_gakumas_tokimeki.ass --input-lang ja --output-lang en --batch-size 50 --pretty
```

Sample audio and subtitle inputs live in `data/sample/`.

## Frontend verification

```bash
cd frontend
npx tsc -p tsconfig.app.json --noEmit    # type check TypeScript (fast; does not check templates)
npm run build                            # full build incl. strictTemplates — requires explicit approval
```

`tsc` does not type-check component templates; template errors only surface in `ng build` or the running `ng serve` output. When a change touches templates, ask the user to check the `ng serve` console or approve a build. The generated `*.spec.ts` files are not maintained — don't use `npm test` as verification.

## Documentation verification

For documentation-only changes:

```bash
git status --short    # confirm only docs/, AGENTS.md, or README.md changed
```

Check by hand that every relative link in changed Markdown files resolves and every heading fragment exists. Use `git status --short` rather than `git diff --name-only` so new untracked files show up.

## Adding a backend endpoint

1. Add the handler to the matching module in `backend/routes/` (`library.py`, `translate.py`, `transcribe.py`, `file_management.py`, `utils.py`, `task_results.py`). A new module must be included in `routes/__init__.py`.
2. Import singletons and helpers from `routes/shared.py`; return through the `utils/api_response.py` helpers with the payload under `data` (see [`api.md`](api.md#response-envelope)).
3. Add the matching method to `ApiService` and the response interface if needed.
4. Call it from the component through the service, with an error-dialog `error:` callback.
5. Run `py_compile` on the changed Python files and `tsc` on the frontend.
6. Update [`api.md`](api.md).

## Adding a task

Follow [`tasks.md`](tasks.md#adding-a-task), then `py_compile` every changed file. Exercise the chain through the UI (ask the user) or a harness under `backend/tests/`.

## Adding a frontend page

1. Create the standalone component in `frontend/src/app/pages/<name>/`.
2. Add the route in `app.routes.ts`.
3. Add a link in `components/navbar/navbar.component.html`.
4. Use the page template from [`frontend.md`](frontend.md#styling): `.page-container`, `.header-container`, and `.form-section`, with `app-tabs` > `app-tab` > `app-subsection`.
5. Run `tsc`; ask the user to check the page in the running app.
6. Update [`frontend.md`](frontend.md#routes-and-pages).

## Layer-specific checks

| Change | References to load | Checks |
|---|---|---|
| Route or response shape | `api.md`, `frontend.md` | `py_compile` changed files; `tsc`; confirm the frontend interface matches |
| Task or chain | `tasks.md` | `py_compile`; task type registered in `shared.py`; pass-through rule; run-log numbering |
| Prompt | `tasks.md` | `py_compile`; a harness run or a manual run in the UI if the user wants one |
| Model backend or settings | `architecture.md` | `py_compile`; Settings page loads the schema and loads the model (manual) |
| Library storage | `architecture.md`, `api.md` | `py_compile`; never touch `outputs/library/` data without approval |
| Page or component | `frontend.md` | `tsc`; template check through `ng serve` output or an approved build; manual UI check |
