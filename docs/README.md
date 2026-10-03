# Documentation

Canonical home for this repository's rules, task procedures, and application references. `AGENTS.md` is a short entry point that links here.

## Load project references

| Task area | Reference |
|---|---|
| Architecture, repository layout, runtime boundaries, storage | [`architecture.md`](references/architecture.md) |
| Task orchestration, task chains, prompts, run logs | [`tasks.md`](references/tasks.md) |
| HTTP endpoints and contracts | [`api.md`](references/api.md) |
| Frontend services, pages, components, styling | [`frontend.md`](references/frontend.md) |
| Verification commands and implementation patterns | [`verification.md`](references/verification.md) |

Load only the references relevant to the current task; expand to another reference only when tracing the code reveals a dependency on it. Inspect current source code before asserting how something behaves — treat the code as authoritative whenever a reference conflicts with it, and correct the stale reference following [`documentation-maintenance.md`](documentation-workflow/documentation-maintenance.md).

## Documentation ownership

| Subject | Canonical file |
|---|---|
| System architecture, repository layout, singletons, model backends, file storage (library JSON, settings, outputs) | [`architecture.md`](references/architecture.md) |
| Task pattern, orchestrator, result/progress handlers, chain composition, task-type sets, run-log numbering, prompts | [`tasks.md`](references/tasks.md) |
| HTTP contracts and the response envelope | [`api.md`](references/api.md) |
| Frontend services, state, routes, pages, components, styling | [`frontend.md`](references/frontend.md) |
| Verification commands and implementation patterns | [`verification.md`](references/verification.md) |
| Coding rules, safety/permission boundaries, scope control | [`repository-rules.md`](repository-rules.md) |
| Implementation-planning procedure | [`implementation-planning.md`](programming-workflow/implementation-planning.md) |
| Issue-drafting procedure | [`issue-authoring.md`](github-workflow/issue-authoring.md) |
| PR-drafting procedure | [`pull-request-authoring.md`](github-workflow/pull-request-authoring.md) |
| Commit-message drafting procedure | [`commit-message-authoring.md`](github-workflow/commit-message-authoring.md) |
| Documentation maintenance procedure | [`documentation-maintenance.md`](documentation-workflow/documentation-maintenance.md) |
| Project discovery and documentation ownership map | This file |
| User setup and usage | `../README.md` |

Every fact has exactly one canonical home from this table. A file not listed here doesn't own application knowledge — it either summarizes or links to the file that does.

## Working rules

- Load only what the task requires — never all references by default.
- Inspect current code before asserting behavior; do not draft from a reference alone.
- Treat code as authoritative over any reference.
- For writing or correcting documentation, follow [`documentation-maintenance.md`](documentation-workflow/documentation-maintenance.md).
